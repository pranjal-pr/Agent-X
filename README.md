# Groq Multi-Agent Stock Analysis Syndicate

Portfolio-grade stock analysis demo that combines CrewAI orchestration, Groq inference, yfinance technical indicators, DuckDuckGo news retrieval, and a FastAPI UI layer.

## Runtime Baseline

- Python: `3.11` recommended for local dev, CI, and deployment
- Deployment target: Hugging Face Docker Space
- CI/CD: GitHub Actions

## Features

- Three-agent CrewAI workflow: Data Miner, News Sentinel, Quantitative Strategist
- Groq-backed inference via `langchain_groq.ChatGroq`
- Typed Pydantic contracts for API inputs, tool outputs, and final recommendation
- FastAPI backend with a static browser UI
- Concurrent technical and news gathering before final synthesis

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `GROQ_API_KEY` in `.env`, then start the UI:

```bash
python main.py --serve
```

Open `http://127.0.0.1:8000`.

Run a one-off CLI analysis:

```bash
python main.py --ticker NVDA
```

## Exact Groq Integration

`agents.py` initializes Groq through CrewAI's `LLM` wrapper and injects it into each agent through `llm=...`:

```python
llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1,
    max_tokens=1200,
    timeout=8,
)

agent = Agent(
    role="Data Miner",
    goal="Extract fresh technical signals for a stock ticker.",
    llm=llm,
    tools=[YFinanceTechnicalsTool()],
)
```

`langchain_groq` remains in `requirements.txt` if you want a standalone LangChain Groq client outside CrewAI, but the current runtime path in this project uses CrewAI's native `LLM` for compatibility with `crewai==0.102.0`.

## GitHub CI/CD to Hugging Face

The repo now includes two GitHub Actions workflows:

- `.github/workflows/ci.yml`
  - installs dependencies on Python `3.11`
  - runs `python -m compileall .`
  - runs smoke tests from `tests/test_smoke.py`
  - builds the Docker image to catch deployment regressions early
- `.github/workflows/deploy-huggingface.yml`
  - waits for the CI workflow to succeed on `main`
  - swaps in `README.space.md` for Hugging Face metadata
  - force-pushes the validated commit to your Hugging Face Space repo

### GitHub Secrets

Add these repository secrets in GitHub:

- `HF_TOKEN`: a Hugging Face user access token with write access to the target Space
- `HF_SPACE_REPO`: the Space identifier in the form `username/space-name`

### Hugging Face Space Setup

1. Create a new Docker Space on Hugging Face.
2. Set these Space secrets:
   - `GROQ_API_KEY`
   - `GROQ_MODEL` optional
3. Push this project to GitHub.
4. Set the GitHub repository secrets listed above.
5. Merge or push to `main` to trigger CI and automatic deployment.

The Docker runtime is defined in `Dockerfile`, and Hugging Face Space metadata lives in `README.space.md`.

## Project Layout

- `tools.py`: tool wrappers for yfinance technicals and DuckDuckGo news
- `agents.py`: CrewAI agents with Groq-backed prompts
- `tasks.py`: task graph and hand-offs
- `crew_service.py`: crew execution and response assembly
- `api.py`: FastAPI server and API routes
- `main.py`: CLI and server entry point
- `static/`: frontend UI
- `Dockerfile`: deployment image for Hugging Face Spaces
- `.github/workflows/`: CI and CD pipelines
