# ResolveHelm Deployment Guide

This guide details how to deploy the **FastAPI Backend on Vercel** and the **React + Vite Dashboard on GitHub Pages**.

---

## Architecture Overview

```
┌──────────────────────────────────────────────┐
│  GitHub Pages (Frontend)                     │
│  https://<username>.github.io/<repo-name>/   │
│  - React 18 + Vite + TypeScript + Tailwind   │
│  - Dynamic API URL configuration             │
└──────────────────────┬───────────────────────┘
                       │ HTTPS / CORS
                       ▼
┌──────────────────────────────────────────────┐
│  Vercel Serverless (Backend)                 │
│  https://<project-name>.vercel.app           │
│  - FastAPI ASGI on Python 3.12 Serverless    │
│  - Entrypoint: api/index.py                  │
│  - Database: Supabase / Postgres / /tmp DB   │
└──────────────────────────────────────────────┘
```

---

## 1. Backend Deployment (Vercel)

### Prerequisites
- [Vercel Account](https://vercel.com)
- [Vercel CLI](https://vercel.com/docs/cli) installed (`vercel`)

### Option A: Deploy via Vercel CLI

1. Run the deployment command from the project root:
   ```bash
   vercel --yes
   ```
2. For production deployment:
   ```bash
   vercel --prod
   ```
3. Once deployed, note your Vercel deployment URL (e.g., `https://resolvehelm-backend.vercel.app`).

### Option B: Deploy via Vercel Web Dashboard (Git Integration)

1. Push this repository to GitHub.
2. In Vercel, click **Add New Project** and select this repository.
3. Framework Preset: **Other** (Vercel automatically detects `vercel.json` and `api/index.py`).
4. Root Directory: `./` (leave default).

### Recommended Vercel Environment Variables

Configure these in the Vercel Dashboard under **Project Settings → Environment Variables**:

| Variable | Description | Recommended Production Value |
|---|---|---|
| `APP_ENV` | Application environment | `production` |
| `DASHBOARD_USERNAME` | Admin login username | `admin` |
| `DASHBOARD_PASSWORD` | Strong password for admin panel | *Set a secure random password* |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend domains | `*` or `https://<user>.github.io` |
| `DATABASE_URL` | Supabase or PostgreSQL connection string | `postgresql://postgres:...@...supabase.co:5432/postgres` |
| `AI_PROVIDER` | AI provider | `gemini` or `anthropic` or `openai` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | `sk-ant-...` |
| `GOOGLE_CLIENT_ID` | Gmail API OAuth client ID | `...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET`| Gmail API OAuth secret | `GOCSPX-...` |
| `GOOGLE_REFRESH_TOKEN`| Gmail API OAuth refresh token | `1//...` |

---

## 2. Frontend Deployment (GitHub Pages)

### Configuration
The project includes a ready-to-use GitHub Actions workflow:
`.github/workflows/deploy-pages.yml`

### Step 1: Enable GitHub Pages in your Repository
1. Navigate to your GitHub repository: **Settings → Pages**.
2. Under **Build and deployment → Source**, select **GitHub Actions**.

### Step 2: (Optional) Set Default Backend URL Secret
If you want the dashboard to automatically point to your Vercel backend without entering it in the login screen:
1. In repository **Settings → Secrets and variables → Actions → Variables**.
2. Add a repository variable named `VITE_API_URL` with your Vercel URL:
   ```
   VITE_API_URL=https://<your-project>.vercel.app
   ```

### Step 3: Trigger the Workflow
- Push any commit to `main`, or:
- Go to the **Actions** tab → **Deploy Frontend to GitHub Pages** → **Run workflow**.

Your dashboard will be live at:
`https://<username>.github.io/<repo-name>/`

---

## 3. Connecting Frontend and Backend

1. Open your GitHub Pages dashboard URL.
2. On the login screen, click **Configure Backend Server URL**.
3. Enter your Vercel backend URL (e.g. `https://resolvehelm-backend.vercel.app`).
4. Enter your `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`.
5. Click **Sign In**. The dashboard will securely verify credentials and load your tickets, events, and knowledge base.
