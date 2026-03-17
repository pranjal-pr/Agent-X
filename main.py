from __future__ import annotations

import argparse
import asyncio
import json
import os

import uvicorn
from dotenv import load_dotenv

from crew_service import analyze_stock


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Groq-powered multi-agent stock analysis syndicate."
    )
    parser.add_argument("--ticker", help="Run a single CLI analysis for a ticker such as NVDA.")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the FastAPI server and browser UI.",
    )
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    return parser.parse_args()


def run_cli(ticker: str) -> None:
    result = asyncio.run(analyze_stock(ticker))
    print(json.dumps(result.model_dump(mode="json"), indent=2))


def run_server(host: str, port: int) -> None:
    uvicorn.run("api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    load_dotenv()
    args = parse_args()

    if args.serve:
        run_server(args.host, args.port)
    elif args.ticker:
        run_cli(args.ticker)
    else:
        raise SystemExit("Use --serve to launch the UI or --ticker NVDA to run a CLI analysis.")
