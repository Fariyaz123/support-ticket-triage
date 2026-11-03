from dataclasses import dataclass
from pathlib import Path
import hashlib
import math
import re

from app.config import Settings


@dataclass
class RetrievedDocument:
    source_name: str
    section: str
    content: str
    relevance_score: float


class LocalHashEmbeddings:
    """Offline deterministic embeddings for the demo and tests."""

    dimensions = 128

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            index = int(hashlib.sha256(token.encode()).hexdigest(), 16) % self.dimensions
            vector[index] += 1.0
        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / magnitude for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def load_faq_documents(settings: Settings) -> list[RetrievedDocument]:
    documents: list[RetrievedDocument] = []
    for path in sorted(Path(settings.faq_directory).glob("*.md")):
        content = path.read_text(encoding="utf-8")
        sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
        for section_text in sections:
            section_text = section_text.strip()
            if not section_text:
                continue
            lines = section_text.splitlines()
            heading = lines[0].lstrip("# ").strip() if lines else path.stem
            body = "\n".join(lines[1:]).strip()
            documents.append(RetrievedDocument(path.name, heading, body, 0.0))
    return documents


class FAQRetriever:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.documents = load_faq_documents(settings)
        self.vector_store = None
        try:
            from langchain_chroma import Chroma

            self.vector_store = Chroma(
                collection_name="support_faq",
                embedding_function=LocalHashEmbeddings(),
                persist_directory=settings.chroma_persist_directory,
            )
            existing = self.vector_store.get(include=[]).get("ids", [])
            if not existing and self.documents:
                self.vector_store.add_texts(
                    [doc.content for doc in self.documents],
                    metadatas=[{"source_name": doc.source_name, "section": doc.section} for doc in self.documents],
                    ids=[f"{doc.source_name}:{index}" for index, doc in enumerate(self.documents)],
                )
        except Exception:
            self.vector_store = None

    def retrieve(self, query: str, k: int = 4) -> list[RetrievedDocument]:
        if self.vector_store is not None:
            try:
                results = self.vector_store.similarity_search_with_relevance_scores(query, k=k)
                return [
                    RetrievedDocument(
                        source_name=document.metadata.get("source_name", "unknown"),
                        section=document.metadata.get("section", "unknown"),
                        content=document.page_content,
                        relevance_score=max(0.0, min(1.0, float(score))),
                    )
                    for document, score in results
                ]
            except Exception:
                pass

        query_words = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored = []
        for document in self.documents:
            words = set(re.findall(r"[a-z0-9]+", f"{document.section} {document.content}".lower()))
            score = len(query_words & words) / max(1, len(query_words))
            scored.append(RetrievedDocument(document.source_name, document.section, document.content, score))
        return sorted(scored, key=lambda item: item.relevance_score, reverse=True)[:k]

