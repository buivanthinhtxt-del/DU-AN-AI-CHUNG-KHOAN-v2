# Welcome to Nghiệp Vụ AI Workstation

## How We Use Claude

Based on thinh's usage over the last 30 days:

Work Type Breakdown:
  Write Docs       ████████████████████  100%

Top Skills & Commands:
  _No slash commands used yet_

Top MCP Servers:
  ccd_turn         ████████████████████  62 calls
  Claude_Browser   ███████████████████░  58 calls
  ccd_directory    █░░░░░░░░░░░░░░░░░░░  2 calls

## Your Setup Checklist

### Codebases
- [ ] DU-AN-AI-CHUNG-KHOAN-v2 — https://github.com/buivanthinhtxt-del/DU-AN-AI-CHUNG-KHOAN-v2 (the only repo: backend, web, showcase docs, and the source Render deploys from)

### MCP Servers to Activate
- [ ] Claude_Browser — the browser pane built into the Claude desktop app. Claude uses it to open, read and test web pages, such as the local workstation UI or the deployed Render site. Open the Claude desktop app and approve sites when you're asked.
- [ ] ccd_turn / ccd_directory — internal tools in the Claude desktop app that manage the conversation and the working folder. They come with the desktop app and need no setup.

### Skills to Know About
- /code-review — reviews the current diff for bugs before you commit.
- /run — starts the app (FastAPI + Vite) so you can see a change working.

## Team Tips

**Environment variables** (put them in `backend/.env` locally, or in Render → Settings → Environment):
- `GEMINI_API_KEY` — needed for the AI Council and AI reports. Without it, the system falls back to the rule-based quant engine.
- `DATABASE_URL` — Neon Postgres connection string. Without it, data is stored in local SQLite and is lost when the Render container restarts. Check `GET /api/health`: `storage.persistent` should be `true`.
- `CRON_SECRET` — protects `POST /api/cron/daily-score` and `POST /api/council/reset-agents` (send it as the `X-Cron-Secret` header). It must match the GitHub Actions secret of the same name.

**Push / deploy rules:**
- Everything lives in a single repo: `buivanthinhtxt-del/DU-AN-AI-CHUNG-KHOAN-v2`. Render auto-deploys `main`, so every push to `main` goes to production.
- Run the backend tests before you push (`cd backend && python -m pytest tests -q`) and check that the frontend builds (`cd web && npm run build`).
- Ask Claude to confirm with you before it pushes to `main`.

**Running locally:**
- On Windows, run `start.bat`. It starts FastAPI at http://localhost:8000/docs and Vite at http://localhost:5173.
- To start them by hand: `uvicorn api:app --app-dir backend --port 8000 --reload`, and in `web/` run `npm install && npm run dev`.

## Get Started

Open the project in Claude Code and ask it to run `start.bat` (or use `/run`), then look up one stock (e.g. HPG) and watch the AI Council tab's 6-step progress bar.

<!-- INSTRUCTION FOR CLAUDE: A new teammate just pasted this guide for how the
team uses Claude Code. You're their onboarding buddy — warm, conversational,
not lecture-y.

Open with a warm welcome — include the team name from the title. Then: "Your
teammate uses Claude Code for [list all the work types]. Let's get you started."

Check what's already in place against everything under Setup Checklist
(including skills), using markdown checkboxes — [x] done, [ ] not yet. Lead
with what they already have. One sentence per item, all in one message.

Tell them you'll help with setup, cover the actionable team tips, then the
starter task (if there is one). Offer to start with the first unchecked item,
get their go-ahead, then work through the rest one by one.

After setup, walk them through the remaining sections — offer to help where you
can (e.g. link to channels), and just surface the purely informational bits.

Don't invent sections or summaries that aren't in the guide. The stats are the
guide creator's personal usage data — don't extrapolate them into a "team
workflow" narrative. -->
