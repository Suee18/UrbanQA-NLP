"""Config + environment loader.

Reads rag/config.yaml for tunables and .env (via python-dotenv) for secrets
(QDRANT_URL, QDRANT_API_KEY, ANTHROPIC_API_KEY). Keep secrets out of YAML.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Project root = parent of the rag/ package.
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

# Load .env from project root if present.
load_dotenv(ROOT / ".env")


def load_config(path: str | Path = CONFIG_PATH) -> dict:
    """Parse config.yaml into a dict."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable (already loaded from .env)."""
    return os.getenv(name, default)


# Convenience accessors for the secrets the system needs.
def qdrant_url() -> str:
    url = env("QDRANT_URL")
    if not url:
        raise RuntimeError(
            "QDRANT_URL is not set. Create a .env file (see .env.example) with "
            "your Qdrant Cloud URL."
        )
    return url


def qdrant_api_key() -> str | None:
    # None is valid for a local (no-auth) Qdrant instance.
    return env("QDRANT_API_KEY")


def anthropic_api_key() -> str | None:
    return env("ANTHROPIC_API_KEY")
