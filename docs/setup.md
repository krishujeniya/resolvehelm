# ResolveHelm Setup & Deployment Guide

## Prerequisites

- Python 3.13 (or 3.11+)
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20+ and npm (for frontend dashboard development)
- Docker & Docker Compose (for containerized deployment)

---

## 1. Local Development Setup

### 1.1 Clone and Install Dependencies

```bash
git clone <repo-url> resolvehelm-ai
cd resolvehelm-ai

# Install backend dependencies
uv sync --all-extras

# Install frontend dependencies
npm --prefix dashboard install
```

### 1.2 Environment Configuration

Copy the example environment configuration:

```bash
cp .env.example .env
```

Edit `.env` to supply required credentials:
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` (see Gmail setup below)
- `DATABASE_URL` (Supabase connection string or leave default for SQLite testing)
- `ANTHROPIC_API_KEY` (Anthropic API key)
- `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`

### 1.3 Seed the Knowledge Base

```bash
uv run python scripts/seed_kb.py
```

### 1.4 Run Automated Tests & Evaluations

```bash
# Run unit and integration tests
uv run pytest -v

# Run 18 golden evaluations and extended safety suite
uv run python -m evals.run_evals
```

---

## 2. Gmail OAuth Provisioning

1. Create a project in Google Cloud Console.
2. Enable the **Gmail API**.
3. Configure the OAuth Consent screen (User Type: External, Testing mode). Add your support Gmail address as a Test User.
4. Create Credentials -> OAuth Client ID (Application type: Desktop App).
5. Download client secrets as `credentials.json` into project root (never commit to Git).
6. Run authorization script:
   ```bash
   uv run python scripts/auth_gmail.py
   ```
7. Copy the generated `GOOGLE_REFRESH_TOKEN` into your `.env` file.

---

## 3. Production Deployment with Docker Compose

1. Build frontend bundle:
   ```bash
   npm --prefix dashboard run build
   ```

2. Launch Docker services:
   ```bash
   docker compose up -d --build
   ```

3. Open SSH tunnel for private dashboard access:
   ```bash
   ssh -L 8080:localhost:8080 user@your-server-ip
   ```

4. Navigate to `http://localhost:8080` in your web browser.
