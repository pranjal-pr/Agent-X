require("dotenv").config();

const express = require("express");
const nodemailer = require("nodemailer");
const path = require("path");
const fs = require("fs/promises");
const crypto = require("crypto");
const { createDatabaseClient } = require("./db");

const app = express();
const PORT = process.env.PORT || 3000;
const ROOT_DIR = __dirname;
const CONTENT_PATH = path.join(ROOT_DIR, "content.json");
const DATABASE_URL = String(process.env.DATABASE_URL || "").trim();
const ADMIN_PASSWORD = String(process.env.ADMIN_PASSWORD || "1234").trim();
const ADMIN_SESSION_SECRET = String(
  process.env.ADMIN_SESSION_SECRET || "set_admin_session_secret_in_env"
);
const ADMIN_TOKEN_TTL_MS = 1000 * 60 * 60 * 12;
const isProduction = String(process.env.NODE_ENV || "").trim() === "production";
const SMTP_TIMEOUT_MS = Math.max(3000, Math.min(30000, Number(process.env.SMTP_TIMEOUT_MS) || 12000));

const DEFAULT_CONTENT = {
  visibility: {
    about: true,
    experience: true,
    skills: true,
    projects: true,
    certifications: true,
    contact: true,
  },
  subtitles: {
    about: "My Introduction",
    experience: "My journey in the academic & professional front",
    skills: "My toolkit for building machine learning models and shipping them into real products.",
    projects: "My independent projects & contributions",
    certifications: "Verified learning milestones in machine learning, AI, and software engineering.",
    contact: "Send a message and I will get back to you soon.",
  },
  hero: {
    brand: "Pranjal",
    name: "Hi, I am Pranjal",
    subtitle:
      "B.Tech CSE Student at Poornima University building intelligent systems from data to deployment.",
  },
  about: {
    intro:
      "As a B.Tech CSE student specializing in AI, Machine Learning, and DevOps, I focus on designing practical intelligent systems and deploying them with reliability. I enjoy translating ideas into real products through clean architecture, robust engineering, and performance-driven implementation.",
    stats: [
      { value: "04+", label: "Years XP" },
      { value: "23+", label: "Projects" },
      { value: "03+", label: "Domains" },
    ],
  },
  skills: {
    subtitle:
      "My toolkit for building machine learning models and shipping them into real products.",
    cards: [
      {
        title: "Foundations",
        description: "Core analysis, stats, and experimentation basics.",
        tags: ["Python", "SQL", "Data Cleaning", "EDA", "Data Storytelling"],
      },
      {
        title: "Machine Learning",
        description: "Modeling, features, and evaluation for real datasets.",
        tags: [
          "scikit-learn",
          "XGBoost",
          "Feature Engineering",
          "Model Evaluation",
          "Hyperparameter Tuning",
          "Pipelines",
        ],
      },
      {
        title: "Deep Learning",
        description: "Neural models for language, vision, and sequence tasks.",
        tags: [
          "PyTorch",
          "TensorFlow",
          "Neural Networks",
          "CNNs",
          "RNNs",
          "NLP",
        ],
      },
      {
        title: "AI Engineering",
        description: "LLM applications, retrieval, and responsible AI systems.",
        tags: [
          "Transformers",
          "LLMs",
          "Prompt Engineering",
          "RAG",
          "Vector Databases",
          "Embeddings",
          "Evaluation",
        ],
      },
      {
        title: "MLOps and Deployment",
        description: "Packaging, serving, and tracking models in production.",
        tags: [
          "Docker",
          "FastAPI",
          "MLflow",
          "Git",
          "CI/CD",
          "Model Serving",
          "Monitoring",
        ],
      },
      {
        title: "Visualization",
        description: "Clear charts and stakeholder-ready dashboards.",
        tags: ["Matplotlib", "Seaborn", "Plotly", "Dashboards"],
      },
    ],
  },
  projects: {
    subtitle: "My independent projects & contributions",
    items: [
      {
        title: "Movie Recommender System",
        description:
          "Content-based recommendation engine hosted on Hugging Face for personalized movie suggestions.",
        stars: 2,
        emoji: "🎬",
        cta: "Live Demo",
        href: "#",
      },
      {
        title: "Multi-Model AI Chatbot",
        description:
          "An interactive chatbot interface built with Streamlit and support for multiple model backends.",
        stars: 3,
        emoji: "🤖",
        cta: "In Dev",
        href: "#",
      },
      {
        title: "AstraRAG Chatbot",
        description:
          "Agentic Retrieval-Augmented Generation chatbot focused on contextual understanding and accurate responses.",
        stars: 4,
        emoji: "🛰️",
        cta: "In Dev",
        href: "#",
      },
      {
        title: "Hospital Management System",
        description:
          "Robust backend platform for managing patient records, scheduling, billing, and hospital workflows.",
        stars: 3,
        emoji: "🏥",
        cta: "Case Study",
        href: "#",
      },
      {
        title: "Credit Card Fraud Detection",
        description:
          "Machine learning model to detect fraudulent transactions with data preprocessing and anomaly scoring.",
        stars: 5,
        emoji: "💳",
        cta: "In Dev",
        href: "#",
      },
    ],
  },
  certifications: {
    subtitle:
      "Verified learning milestones in machine learning, AI, and software engineering.",
    items: [
      {
        year: "2024",
        title: "Machine Learning Specialization",
        org: "Coursera",
        href: "#",
      },
    ],
  },
  contact: {
    email: "pranjal@example.com",
    github: "https://github.com/your-username",
    linkedin: "https://linkedin.com/in/your-username",
  },
};

const database = createDatabaseClient(DATABASE_URL);
let contentStore = DEFAULT_CONTENT;
let persistenceMode = database ? "postgres" : "file";

app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: false }));

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SAFE_URL_REGEX = /^(https?:\/\/|mailto:|#|\/)/i;

function assertRuntimeConfig() {
  if (!isProduction) return;

  if (!DATABASE_URL) {
    throw new Error("DATABASE_URL is required in production. Configure your Neon Postgres connection string.");
  }

  if (!ADMIN_PASSWORD || ADMIN_PASSWORD === "1234") {
    throw new Error("Set a strong ADMIN_PASSWORD in production.");
  }

  if (
    !ADMIN_SESSION_SECRET ||
    ADMIN_SESSION_SECRET === "set_admin_session_secret_in_env"
  ) {
    throw new Error("Set ADMIN_SESSION_SECRET in production.");
  }
}

function isValidEmail(value) {
  return EMAIL_REGEX.test(String(value || "").trim());
}

function clampText(value, fallback = "", max = 400) {
  const normalized = String(value ?? fallback).trim();
  if (!normalized) return String(fallback || "").trim();
  return normalized.slice(0, max);
}

function normalizeUrl(value, fallback = "#") {
  const candidate = String(value ?? fallback).trim();
  if (!candidate) return fallback;
  if (!SAFE_URL_REGEX.test(candidate)) return fallback;
  return candidate.slice(0, 2048);
}

function normalizeVisibility(visibility) {
  const input = visibility && typeof visibility === "object" ? visibility : {};
  return {
    about: input.about !== false,
    experience: input.experience !== false,
    skills: input.skills !== false,
    projects: input.projects !== false,
    certifications: input.certifications !== false,
    contact: input.contact !== false,
  };
}

function normalizeSubtitles(subtitles, data = {}) {
  const input = subtitles && typeof subtitles === "object" ? subtitles : {};
  return {
    about: clampText(input.about, DEFAULT_CONTENT.subtitles.about, 180),
    experience: clampText(input.experience, DEFAULT_CONTENT.subtitles.experience, 220),
    skills: clampText(input.skills ?? data.skills?.subtitle, DEFAULT_CONTENT.subtitles.skills, 220),
    projects: clampText(input.projects ?? data.projects?.subtitle, DEFAULT_CONTENT.subtitles.projects, 220),
    certifications: clampText(
      input.certifications ?? data.certifications?.subtitle,
      DEFAULT_CONTENT.subtitles.certifications,
      220
    ),
    contact: clampText(input.contact, DEFAULT_CONTENT.subtitles.contact, 220),
  };
}

function normalizeStats(stats) {
  if (!Array.isArray(stats)) return DEFAULT_CONTENT.about.stats;
  return stats
    .slice(0, 6)
    .map((item) => ({
      value: clampText(item?.value, "", 40),
      label: clampText(item?.label, "", 80),
    }))
    .filter((item) => item.value || item.label);
}

function normalizeSkillCards(cards) {
  if (!Array.isArray(cards)) return DEFAULT_CONTENT.skills.cards;
  return cards
    .slice(0, 12)
    .map((card) => ({
      title: clampText(card?.title, "", 100),
      description: clampText(card?.description, "", 260),
      tags: Array.isArray(card?.tags)
        ? card.tags.slice(0, 15).map((tag) => clampText(tag, "", 60)).filter(Boolean)
        : [],
    }))
    .filter((card) => card.title || card.description || card.tags.length > 0);
}

function normalizeProjectItems(items) {
  if (!Array.isArray(items)) return DEFAULT_CONTENT.projects.items;
  return items
    .slice(0, 20)
    .map((item) => ({
      title: clampText(item?.title, "", 120),
      description: clampText(item?.description, "", 420),
      stars: Math.max(0, Math.min(5, Number(item?.stars) || 0)),
      emoji: clampText(item?.emoji, "", 16),
      demoUrl: normalizeUrl(item?.demoUrl ?? item?.href, "#"),
      repoUrl: normalizeUrl(item?.repoUrl, "#"),
    }))
    .filter((item) => item.title || item.description || item.emoji || item.demoUrl !== "#" || item.repoUrl !== "#");
}

function normalizeCertItems(items) {
  if (!Array.isArray(items)) return DEFAULT_CONTENT.certifications.items;
  return items
    .slice(0, 12)
    .map((item) => ({
      year: clampText(item?.year, "", 10),
      title: clampText(item?.title, "", 140),
      org: clampText(item?.org, "", 120),
      href: normalizeUrl(item?.href, "#"),
    }))
    .filter((item) => item.year || item.title || item.org || item.href !== "#");
}

function normalizeContent(input) {
  const data = input && typeof input === "object" ? input : {};
  const subtitles = normalizeSubtitles(data.subtitles, data);
  return {
    visibility: normalizeVisibility(data.visibility),
    subtitles,
    hero: {
      brand: clampText(data.hero?.brand, DEFAULT_CONTENT.hero.brand, 80),
      name: clampText(data.hero?.name, DEFAULT_CONTENT.hero.name, 120),
      subtitle: clampText(data.hero?.subtitle, DEFAULT_CONTENT.hero.subtitle, 220),
    },
    about: {
      intro: clampText(data.about?.intro, DEFAULT_CONTENT.about.intro, 1200),
      stats: normalizeStats(data.about?.stats),
    },
    skills: {
      subtitle: subtitles.skills,
      cards: normalizeSkillCards(data.skills?.cards),
    },
    projects: {
      subtitle: subtitles.projects,
      items: normalizeProjectItems(data.projects?.items),
    },
    certifications: {
      subtitle: subtitles.certifications,
      items: normalizeCertItems(data.certifications?.items),
    },
    contact: {
      email: isValidEmail(data.contact?.email)
        ? String(data.contact.email).trim()
        : DEFAULT_CONTENT.contact.email,
      github: normalizeUrl(data.contact?.github, DEFAULT_CONTENT.contact.github),
      linkedin: normalizeUrl(data.contact?.linkedin, DEFAULT_CONTENT.contact.linkedin),
    },
  };
}

async function loadContentFromFile() {
  try {
    const raw = await fs.readFile(CONTENT_PATH, "utf8");
    const parsed = JSON.parse(raw);
    return normalizeContent(parsed);
  } catch (error) {
    const fallback = normalizeContent(DEFAULT_CONTENT);
    await fs.writeFile(CONTENT_PATH, JSON.stringify(fallback, null, 2), "utf8");
    return fallback;
  }
}

async function saveContentToFile(nextContent) {
  const normalized = normalizeContent(nextContent);
  await fs.writeFile(CONTENT_PATH, JSON.stringify(normalized, null, 2), "utf8");
  return normalized;
}

async function loadContent() {
  if (database) {
    const seedContent = await loadContentFromFile();
    const stored = await database.init(seedContent);
    contentStore = normalizeContent(stored);
    persistenceMode = "postgres";
    return contentStore;
  }

  contentStore = await loadContentFromFile();
  persistenceMode = "file";
  return contentStore;
}

async function saveContent(nextContent) {
  const normalized = normalizeContent(nextContent);
  if (database) {
    const stored = await database.saveContent(normalized);
    contentStore = normalizeContent(stored);
    return contentStore;
  }

  contentStore = await saveContentToFile(normalized);
  return contentStore;
}

function safeStringEqual(left, right) {
  const l = Buffer.from(String(left || ""));
  const r = Buffer.from(String(right || ""));
  if (l.length !== r.length) return false;
  return crypto.timingSafeEqual(l, r);
}

function createAdminToken() {
  const payload = {
    iat: Date.now(),
    exp: Date.now() + ADMIN_TOKEN_TTL_MS,
  };
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = crypto
    .createHmac("sha256", ADMIN_SESSION_SECRET)
    .update(encoded)
    .digest("base64url");
  return `${encoded}.${signature}`;
}

function verifyAdminToken(token) {
  if (!token || typeof token !== "string") return false;
  const [encoded, providedSignature] = token.split(".");
  if (!encoded || !providedSignature) return false;

  const expectedSignature = crypto
    .createHmac("sha256", ADMIN_SESSION_SECRET)
    .update(encoded)
    .digest("base64url");

  if (!safeStringEqual(providedSignature, expectedSignature)) return false;

  try {
    const parsed = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8"));
    return Number(parsed.exp) > Date.now();
  } catch (error) {
    return false;
  }
}

function requireAdmin(req, res, next) {
  const header = String(req.headers.authorization || "");
  const token = header.startsWith("Bearer ") ? header.slice(7).trim() : "";

  if (!verifyAdminToken(token)) {
    return res.status(401).json({ ok: false, message: "Unauthorized." });
  }
  return next();
}

function getTransporter() {
  const { SMTP_HOST, SMTP_PORT, SMTP_SECURE, SMTP_USER, SMTP_PASS } = process.env;

  if (!SMTP_HOST || !SMTP_PORT || !SMTP_USER || !SMTP_PASS) {
    return null;
  }

  return nodemailer.createTransport({
    host: SMTP_HOST,
    port: Number(SMTP_PORT),
    secure: String(SMTP_SECURE).toLowerCase() === "true",
    connectionTimeout: SMTP_TIMEOUT_MS,
    greetingTimeout: SMTP_TIMEOUT_MS,
    socketTimeout: SMTP_TIMEOUT_MS,
    auth: {
      user: SMTP_USER,
      pass: SMTP_PASS,
    },
  });
}

async function deliverMessage({ name, email, message }) {
  const transporter = getTransporter();
  const toEmail = process.env.CONTACT_TO_EMAIL;
  const fromEmail = process.env.CONTACT_FROM_EMAIL || process.env.SMTP_USER;

  if (!transporter || !toEmail || !fromEmail) {
    console.log(
      `[contact][${new Date().toISOString()}] name="${name}" email="${email}" message="${message}"`
    );
    return {
      mode: "log",
      message:
        "Message saved. Email delivery is not configured yet on the server.",
    };
  }

  try {
    await transporter.sendMail({
      from: fromEmail,
      to: toEmail,
      replyTo: email,
      subject: `Portfolio Contact: ${name}`,
      text: `Name: ${name}\nEmail: ${email}\n\nMessage:\n${message}`,
    });
  } catch (error) {
    console.error("SMTP delivery failed:", error);
    return {
      mode: "stored",
      message:
        "Message saved, but email delivery failed on the server. Check SMTP settings in Render logs.",
    };
  }

  return {
    mode: "smtp",
    message: "Message sent successfully.",
  };
}

async function persistContactMessage({ name, email, message, deliveryMode }) {
  if (!database) return;
  await database.saveContactMessage({
    name,
    email,
    message,
    deliveryMode,
  });
}

app.get("/api/content", async (req, res) => {
  return res.status(200).json({ ok: true, content: contentStore });
});

app.get("/api/health", async (req, res) => {
  try {
    if (database) {
      await database.healthCheck();
    }

    return res.status(200).json({
      ok: true,
      mode: persistenceMode,
      database: Boolean(database),
      uptimeSeconds: Math.round(process.uptime()),
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Health check failed:", error);
    return res.status(500).json({
      ok: false,
      mode: persistenceMode,
      database: Boolean(database),
      message: "Health check failed.",
    });
  }
});

app.post("/api/admin/login", async (req, res) => {
  const password = String(req.body.password || "").trim();
  if (!password || !safeStringEqual(password, ADMIN_PASSWORD)) {
    return res.status(401).json({ ok: false, message: "Invalid password." });
  }

  return res.status(200).json({
    ok: true,
    token: createAdminToken(),
    expiresInMs: ADMIN_TOKEN_TTL_MS,
  });
});

app.get("/api/admin/content", requireAdmin, async (req, res) => {
  return res.status(200).json({ ok: true, content: contentStore });
});

app.put("/api/admin/content", requireAdmin, async (req, res) => {
  try {
    const incoming = req.body?.content ?? req.body;
    const updated = await saveContent(incoming);
    return res.status(200).json({ ok: true, content: updated });
  } catch (error) {
    console.error("Failed to save content:", error);
    return res.status(500).json({ ok: false, message: "Failed to save content." });
  }
});

app.post("/api/contact", async (req, res) => {
  try {
    const name = String(req.body.name || "").trim();
    const email = String(req.body.email || "").trim();
    const message = String(req.body.message || "").trim();

    if (!name || !email || !message) {
      return res.status(400).json({
        ok: false,
        message: "Name, email, and message are required.",
      });
    }

    if (!isValidEmail(email)) {
      return res.status(400).json({
        ok: false,
        message: "Please provide a valid email address.",
      });
    }

    if (name.length > 80 || email.length > 160 || message.length > 3000) {
      return res.status(400).json({
        ok: false,
        message: "Input exceeds allowed length.",
      });
    }

    const result = await deliverMessage({ name, email, message });

    await persistContactMessage({
      name,
      email,
      message,
      deliveryMode: result.mode,
    });

    const statusCode = result.mode === "smtp" ? 200 : 202;
    return res.status(statusCode).json({
      ok: true,
      mode: result.mode,
      message: result.message,
    });
  } catch (error) {
    console.error("Contact API error:", error);
    return res.status(500).json({
      ok: false,
      message: "Unable to process your request right now.",
    });
  }
});

app.get("/admin", (req, res) => {
  return res.sendFile(path.join(ROOT_DIR, "admin.html"));
});

app.get("*", (req, res, next) => {
  if (req.path.startsWith("/api/")) {
    return next();
  }
  if (req.path === "/admin.html") {
    return res.sendFile(path.join(ROOT_DIR, "admin.html"));
  }
  return res.sendFile(path.join(ROOT_DIR, "index.html"));
});

app.use((req, res) => {
  res.status(404).json({ ok: false, message: "Not found." });
});

assertRuntimeConfig();

const shutdown = async (signal) => {
  try {
    if (database) {
      await database.close();
    }
  } catch (error) {
    console.error(`Failed to close database during ${signal}:`, error);
  } finally {
    process.exit(0);
  }
};

["SIGINT", "SIGTERM"].forEach((signal) => {
  process.on(signal, () => {
    shutdown(signal);
  });
});

loadContent()
  .then(() => {
    app.listen(PORT, () => {
      console.log(
        `Server is running on http://localhost:${PORT} using ${persistenceMode} persistence`
      );
    });
  })
  .catch((error) => {
    console.error("Failed to initialize content store:", error);
    process.exit(1);
  });

