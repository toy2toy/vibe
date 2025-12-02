import os
from pathlib import Path

from dotenv import load_dotenv


def load_env():
    """Load env vars from project-level .env and ensure API key exists."""
    project_root = Path(__file__).resolve().parent
    load_dotenv(project_root / ".env", override=False)
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set. Add it to cctv/.env or export it.")


__all__ = ["load_env"]
