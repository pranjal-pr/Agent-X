---
title: Groq Stock Analysis Syndicate
colorFrom: green
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# Groq Multi-Agent Stock Analysis Syndicate

Low-latency multi-agent stock analysis built with CrewAI, Groq, yfinance, and DuckDuckGo search.

## Runtime

- Backend: FastAPI
- UI: static frontend served by FastAPI
- Deployment: Docker Space on Hugging Face

## Required Space Secrets

- `GROQ_API_KEY`
- `GROQ_MODEL` optional, defaults to `llama-3.3-70b-versatile`
