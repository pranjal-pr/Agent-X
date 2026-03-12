# Pranjal Portfolio

Express portfolio app with:

- public portfolio site
- admin console at `/admin`
- content persistence in Neon Postgres
- contact API with optional SMTP delivery

## Local Run

1. Create a `.env` file from `.env.example`
2. Set at minimum:
   - `ADMIN_PASSWORD`
   - `ADMIN_SESSION_SECRET`
3. Optional for full Postgres persistence:
   - `DATABASE_URL`
4. Start the app:

```powershell
npm install
npm start
```

Validation scripts:

```powershell
npm run check
npm run smoke
npm run ci
```

App URLs:

- `http://localhost:3000`
- `http://localhost:3000/admin`
- `http://localhost:3000/api/health`

## Render + Neon

1. Create a Neon Postgres project and copy the pooled `DATABASE_URL`
2. Create a Render Web Service from this repo
3. Use `render.yaml`
4. Set these environment variables in Render:
   - `DATABASE_URL`
   - `ADMIN_PASSWORD`
   - `ADMIN_SESSION_SECRET`
5. Optional SMTP variables if you want contact form emails delivered
6. Connect the GitHub repository to Render
7. Keep auto deploy set to CI checks pass

## GitHub CI/CD

This repo includes a GitHub Actions workflow at `.github/workflows/ci.yml`.

Pipeline behavior:

- every push and PR runs `npm ci` and `npm run ci`
- `npm run ci` performs syntax checks and an end-to-end smoke test
- Render is configured with `autoDeployTrigger: checksPass` in `render.yaml`
- when the `main` branch checks pass, Render deploys automatically

This is cleaner than using a deploy hook because GitHub owns the checks and Render only deploys verified commits.

The app auto-creates these tables on first boot:

- `site_content`
- `contact_messages`

On first startup, the database is seeded from `content.json`.
