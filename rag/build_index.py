"""Build the Qdrant knowledge base. Run once (and after editing locations).

Usage:
    python -m rag.build_index

Requires a .env with QDRANT_URL / QDRANT_API_KEY (see .env.example).
"""

from rag.config import load_config
from rag.ingest import build_index


def main():
    config = load_config()
    print(f"Locations: {', '.join(config['locations'])}")
    build_index(config)


if __name__ == "__main__":
    main()
