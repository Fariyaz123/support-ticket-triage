from pathlib import Path

from app.config import get_settings
from app.services.knowledge import FAQRetriever


def main() -> None:
    settings = get_settings()
    Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
    retriever = FAQRetriever(settings)
    print(f"Indexed {len(retriever.documents)} FAQ sections into ChromaDB")


if __name__ == "__main__":
    main()

