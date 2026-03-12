const { Pool } = require("pg");

function resolveSslConfig(connectionString) {
  const explicit = String(process.env.DATABASE_SSL || "auto").trim().toLowerCase();
  if (explicit === "false" || explicit === "0" || explicit === "off") {
    return false;
  }
  if (explicit === "true" || explicit === "1" || explicit === "on") {
    return { rejectUnauthorized: false };
  }
  if (
    connectionString.includes("sslmode=require") ||
    connectionString.includes("neon.tech") ||
    connectionString.includes("render.com")
  ) {
    return { rejectUnauthorized: false };
  }
  return false;
}

function createDatabaseClient(connectionString) {
  if (!connectionString) return null;

  const pool = new Pool({
    connectionString,
    ssl: resolveSslConfig(connectionString),
  });

  return {
    async init(seedContent) {
      await pool.query(`
        CREATE TABLE IF NOT EXISTS site_content (
          id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
          content JSONB NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
      `);

      await pool.query(`
        CREATE TABLE IF NOT EXISTS contact_messages (
          id BIGSERIAL PRIMARY KEY,
          name VARCHAR(80) NOT NULL,
          email VARCHAR(160) NOT NULL,
          message TEXT NOT NULL,
          delivery_mode VARCHAR(24) NOT NULL DEFAULT 'log',
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
      `);

      const existing = await pool.query(
        "SELECT content FROM site_content WHERE id = 1 LIMIT 1"
      );

      if (existing.rows[0]?.content) {
        return existing.rows[0].content;
      }

      const inserted = await pool.query(
        `
          INSERT INTO site_content (id, content, updated_at)
          VALUES (1, $1::jsonb, NOW())
          ON CONFLICT (id) DO UPDATE SET
            content = EXCLUDED.content,
            updated_at = NOW()
          RETURNING content
        `,
        [JSON.stringify(seedContent)]
      );

      return inserted.rows[0].content;
    },

    async getContent() {
      const result = await pool.query(
        "SELECT content FROM site_content WHERE id = 1 LIMIT 1"
      );
      return result.rows[0]?.content || null;
    },

    async saveContent(content) {
      const result = await pool.query(
        `
          INSERT INTO site_content (id, content, updated_at)
          VALUES (1, $1::jsonb, NOW())
          ON CONFLICT (id) DO UPDATE SET
            content = EXCLUDED.content,
            updated_at = NOW()
          RETURNING content
        `,
        [JSON.stringify(content)]
      );
      return result.rows[0].content;
    },

    async saveContactMessage(message) {
      await pool.query(
        `
          INSERT INTO contact_messages (name, email, message, delivery_mode)
          VALUES ($1, $2, $3, $4)
        `,
        [
          message.name,
          message.email,
          message.message,
          message.deliveryMode || "log",
        ]
      );
    },

    async healthCheck() {
      await pool.query("SELECT 1");
      return true;
    },

    async close() {
      await pool.end();
    },
  };
}

module.exports = {
  createDatabaseClient,
};
