# 🧸 Buddy – English for Kids (age < 7)

A friendly chatbot that teaches English in 3 levels, senses the child's mood/mode, supports emotions (SEL),
remembers progress, and replies in under 2 seconds.

- **Live demo:** `<PASTE YOUR RENDER URL HERE>`
- **Docs:** [System design](docs/DESIGN.md) · [Architecture diagram](docs/architecture.svg)

## Features
- L1 words → L2 phrases → L3 sentences; automatic level-up from mastery
- Modes: LEARNING / CONVERSATION / ENGAGEMENT (games, rhymes) / SUPPORT (emotional care)
- SEL: names feelings, calming steps, growth-mindset praise, stars for effort
- Context-aware (name, level, history); voice in/out via browser Web Speech API
- LLM timeout + template fallback → bot never hangs

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add GROQ_API_KEY (free at console.groq.com/keys)
export $(grep -v '^#' .env | xargs)   # Windows PowerShell: set vars manually
uvicorn app.main:app --reload
# open http://localhost:8000
pytest                      # run tests
```
Without a key the app still works using built-in template replies.

## Deploy (Render, free)
1. Push to GitHub (below). 2. Render → **New → Blueprint** → select the repo (`render.yaml` is picked up).
3. Add env var `GROQ_API_KEY`. 4. Deploy; open the `onrender.com` URL. Health check: `/health`.
(Free instances sleep after idle: open the URL once before the demo to warm it up. SQLite resets on redeploy.)

## GitHub
```bash
git init && git add . && git commit -m "Buddy: English for kids chatbot"
git branch -M main && git remote add origin https://github.com/<you>/buddy-english-kids.git && git push -u origin main
```
Repo → Settings → Collaborators → add the two reviewers.

## API
`POST /chat {"child_id":"abc","message":"hello"}` →
`{reply, mode, emotion, level, stars, mastered, leveled_up, target, used_llm, latency_ms}`

## Structure
`app/main.py` orchestrator · `modes.py` mode/emotion · `curriculum.py` levels/mastery · `llm.py` Groq client · `store.py` SQLite · `static/index.html` UI
