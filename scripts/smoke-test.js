const { spawn } = require("child_process");

const PORT = process.env.PORT || "4173";
const BASE_URL = `http://127.0.0.1:${PORT}`;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, options);
  const text = await response.text();
  let json = null;

  try {
    json = text ? JSON.parse(text) : null;
  } catch (error) {
    json = null;
  }

  return { response, json, text };
}

async function waitForHealth(maxAttempts = 30) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const { response, json } = await request("/api/health");
      if (response.ok && json?.ok) {
        return json;
      }
    } catch (error) {
      // Server is still starting.
    }
    await delay(500);
  }

  throw new Error("Timed out waiting for /api/health");
}

async function main() {
  const env = {
    ...process.env,
    PORT,
    NODE_ENV: "test",
    DATABASE_URL: "",
    DATABASE_SSL: "false",
    ADMIN_PASSWORD: "1234",
    ADMIN_SESSION_SECRET: "test_admin_session_secret",
  };

  const server = spawn(process.execPath, ["server.js"], {
    cwd: process.cwd(),
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });

  let stderr = "";
  server.stderr.on("data", (chunk) => {
    stderr += String(chunk);
  });

  try {
    const health = await waitForHealth();
    if (health.mode !== "file") {
      throw new Error(`Expected file mode in smoke test, received ${health.mode}`);
    }

    const content = await request("/api/content");
    if (!content.response.ok || !content.json?.content?.hero) {
      throw new Error("Public content endpoint did not return hero content");
    }

    const badLogin = await request("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: "wrong-password" }),
    });
    if (badLogin.response.status !== 401) {
      throw new Error(`Expected 401 for invalid login, received ${badLogin.response.status}`);
    }

    const login = await request("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: "1234" }),
    });
    if (!login.response.ok || !login.json?.token) {
      throw new Error("Admin login failed in smoke test");
    }

    const authHeaders = {
      Authorization: `Bearer ${login.json.token}`,
    };

    const adminContent = await request("/api/admin/content", {
      headers: authHeaders,
    });
    if (!adminContent.response.ok || !adminContent.json?.content?.projects) {
      throw new Error("Admin content endpoint failed in smoke test");
    }

    const save = await request("/api/admin/content", {
      method: "PUT",
      headers: {
        ...authHeaders,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content: adminContent.json.content }),
    });
    if (!save.response.ok || !save.json?.ok) {
      throw new Error("Admin save endpoint failed in smoke test");
    }

    const contact = await request("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "CI Smoke Test",
        email: "ci@example.com",
        message: "Smoke test contact message",
      }),
    });
    if (!contact.response.ok || !contact.json?.ok) {
      throw new Error("Contact endpoint failed in smoke test");
    }

    console.log("Smoke test passed.");
  } finally {
    server.kill("SIGTERM");
    await delay(500);
    if (!server.killed) {
      server.kill("SIGKILL");
    }

    if (server.exitCode && server.exitCode !== 0) {
      throw new Error(`Server exited with code ${server.exitCode}\n${stderr}`);
    }
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
