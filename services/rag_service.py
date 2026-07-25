from __future__ import annotations

import hashlib
import re

from dataclasses import dataclass
from typing import Any

import chromadb

from config.settings import Settings
from core.exceptions import (
    FileProcessingError,
    OllamaConnectionError,
    OllamaModelError,
)
from core.logging_config import get_logger
from core.ollama_client import OllamaManager


logger = get_logger(__name__)


COLLECTION_NAME = (
    "techcorp_local_documents_v1"
)


@dataclass(slots=True)
class TextChunk:
    id: str
    document_id: str
    document_title: str
    original_name: str
    text: str
    chunk_index: int
    character_start: int
    character_end: int

    def metadata(
        self,
    ) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_title": (
                self.document_title
            ),
            "original_name": (
                self.original_name
            ),
            "chunk_index": self.chunk_index,
            "character_start": (
                self.character_start
            ),
            "character_end": (
                self.character_end
            ),
        }


@dataclass(slots=True)
class SearchResult:
    chunk_id: str
    document_id: str
    document_title: str
    original_name: str
    text: str
    chunk_index: int
    distance: float | None
    relevance_score: float | None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": (
                self.document_id
            ),
            "document_title": (
                self.document_title
            ),
            "original_name": (
                self.original_name
            ),
            "text": self.text,
            "chunk_index": (
                self.chunk_index
            ),
            "distance": self.distance,
            "relevance_score": (
                self.relevance_score
            ),
        }


def normalise_chunk_text(
    text: str,
) -> str:
    text = str(
        text or ""
    ).replace(
        "\x00",
        " ",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def stable_chunk_id(
    document_id: str,
    chunk_index: int,
    text: str,
) -> str:
    digest = hashlib.sha256(
        (
            document_id
            + ":"
            + str(chunk_index)
            + ":"
            + text
        ).encode(
            "utf-8"
        )
    ).hexdigest()[:20]

    return (
        f"{document_id}_"
        f"{chunk_index}_"
        f"{digest}"
    )


def split_text_into_chunks(
    *,
    document_id: str,
    document_title: str,
    original_name: str,
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[TextChunk]:
    """
    Split text using paragraph-aware boundaries.

    Large paragraphs are split by character windows. Each chunk keeps
    overlap with the previous chunk to preserve surrounding context.
    """

    cleaned_text = normalise_chunk_text(
        text
    )

    if not cleaned_text:
        return []

    if chunk_size < 200:
        raise ValueError(
            "chunk_size must be at least 200."
        )

    if (
        chunk_overlap < 0
        or chunk_overlap >= chunk_size
    ):
        raise ValueError(
            "chunk_overlap must be smaller "
            "than chunk_size."
        )

    chunks: list[TextChunk] = []
    text_length = len(cleaned_text)
    start = 0
    chunk_index = 0

    while start < text_length:
        target_end = min(
            start + chunk_size,
            text_length,
        )

        end = target_end

        if target_end < text_length:
            search_window_start = max(
                start + int(
                    chunk_size * 0.55
                ),
                start,
            )

            search_window = cleaned_text[
                search_window_start:
                target_end
            ]

            paragraph_break = (
                search_window.rfind(
                    "\n\n"
                )
            )

            sentence_break = max(
                search_window.rfind(". "),
                search_window.rfind("? "),
                search_window.rfind("! "),
            )

            line_break = (
                search_window.rfind(
                    "\n"
                )
            )

            preferred_break = max(
                paragraph_break,
                sentence_break,
                line_break,
            )

            if preferred_break >= 0:
                end = (
                    search_window_start
                    + preferred_break
                    + 1
                )

        chunk_text = (
            cleaned_text[start:end]
            .strip()
        )

        if chunk_text:
            chunks.append(
                TextChunk(
                    id=stable_chunk_id(
                        document_id,
                        chunk_index,
                        chunk_text,
                    ),
                    document_id=document_id,
                    document_title=(
                        document_title
                    ),
                    original_name=(
                        original_name
                    ),
                    text=chunk_text,
                    chunk_index=(
                        chunk_index
                    ),
                    character_start=start,
                    character_end=end,
                )
            )

            chunk_index += 1

        if end >= text_length:
            break

        next_start = (
            end - chunk_overlap
        )

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


class RAGService:
    """
    Local semantic retrieval service using:

    - Ollama for embeddings
    - ChromaDB for persistent vector storage
    """

    def __init__(
        self,
        settings: Settings,
        ollama_manager: OllamaManager,
    ) -> None:
        self.settings = settings
        self.ollama = ollama_manager

        self.settings.chroma_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            self.client = (
                chromadb.PersistentClient(
                    path=str(
                        self.settings
                        .chroma_folder
                    )
                )
            )

            self.collection = (
                self.client
                .get_or_create_collection(
                    name=COLLECTION_NAME,
                    metadata={
                        "hnsw:space": "cosine",
                        "embedding_model": (
                            self.settings
                            .ollama_embed_model
                        ),
                    },
                )
            )

        except Exception as exc:
            raise FileProcessingError(
                "Could not initialise local "
                f"ChromaDB storage: {exc}"
            ) from exc

    def count_chunks(
        self,
    ) -> int:
        try:
            return int(
                self.collection.count()
            )

        except Exception as exc:
            logger.warning(
                "Could not count RAG chunks: %s",
                exc,
            )

            return 0

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        if not document_id:
            return

        try:
            self.collection.delete(
                where={
                    "document_id": (
                        document_id
                    )
                }
            )

        except Exception as exc:
            raise FileProcessingError(
                "Could not remove document "
                f"embeddings: {exc}"
            ) from exc

    def index_document(
        self,
        document: dict[str, Any],
        *,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
        embedding_batch_size: int = 24,
    ) -> dict[str, Any]:
        document_id = str(
            document.get(
                "id",
                "",
            )
        ).strip()

        if not document_id:
            raise FileProcessingError(
                "Document has no identifier."
            )

        document_text = str(
            document.get(
                "text",
                "",
            )
        ).strip()

        if not document_text:
            self.delete_document(
                document_id
            )

            return {
                "document_id": document_id,
                "indexed": False,
                "chunk_count": 0,
                "reason": (
                    "Document has no extracted text."
                ),
            }

        document_title = str(
            document.get(
                "title",
                "Untitled document",
            )
        )

        original_name = str(
            document.get(
                "original_name",
                document_title,
            )
        )

        chunks = split_text_into_chunks(
            document_id=document_id,
            document_title=document_title,
            original_name=original_name,
            text=document_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        if not chunks:
            return {
                "document_id": document_id,
                "indexed": False,
                "chunk_count": 0,
                "reason": (
                    "No searchable chunks "
                    "were generated."
                ),
            }

        try:
            self.delete_document(
                document_id
            )

            for batch_start in range(
                0,
                len(chunks),
                embedding_batch_size,
            ):
                batch = chunks[
                    batch_start:
                    batch_start
                    + embedding_batch_size
                ]

                texts = [
                    chunk.text
                    for chunk in batch
                ]

                embeddings = (
                    self.ollama.embed_many(
                        texts=texts,
                        model=(
                            self.settings
                            .ollama_embed_model
                        ),
                    )
                )

                self.collection.upsert(
                    ids=[
                        chunk.id
                        for chunk in batch
                    ],
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=[
                        chunk.metadata()
                        for chunk in batch
                    ],
                )

            return {
                "document_id": document_id,
                "indexed": True,
                "chunk_count": len(chunks),
                "reason": None,
            }

        except (
            OllamaConnectionError,
            OllamaModelError,
        ):
            raise

        except Exception as exc:
            logger.exception(
                "Could not index document %s",
                document_id,
            )

            raise FileProcessingError(
                "Could not index document "
                f"for semantic search: {exc}"
            ) from exc

    def search(
        self,
        query: str,
        *,
        document_ids: list[str] | None = None,
        top_k: int = 6,
    ) -> list[SearchResult]:
        cleaned_query = str(
            query or ""
        ).strip()

        if not cleaned_query:
            return []

        if self.count_chunks() == 0:
            return []

        query_embedding = self.ollama.embed(
            cleaned_query,
            model=(
                self.settings
                .ollama_embed_model
            ),
        )

        where_filter: (
            dict[str, Any]
            | None
        ) = None

        valid_document_ids = [
            str(document_id)
            for document_id in (
                document_ids or []
            )
            if str(document_id).strip()
        ]

        if len(valid_document_ids) == 1:
            where_filter = {
                "document_id": (
                    valid_document_ids[0]
                )
            }

        elif len(valid_document_ids) > 1:
            where_filter = {
                "document_id": {
                    "$in": (
                        valid_document_ids
                    )
                }
            }

        query_arguments: dict[
            str,
            Any,
        ] = {
            "query_embeddings": [
                query_embedding
            ],
            "n_results": max(
                1,
                min(top_k, 20),
            ),
            "include": [
                "documents",
                "metadatas",
                "distances",
            ],
        }

        if where_filter:
            query_arguments["where"] = (
                where_filter
            )

        try:
            response = (
                self.collection.query(
                    **query_arguments
                )
            )

        except Exception as exc:
            raise FileProcessingError(
                "Semantic document search "
                f"failed: {exc}"
            ) from exc

        ids_groups = (
            response.get("ids")
            if isinstance(response, dict)
            else getattr(
                response,
                "ids",
                None,
            )
        ) or []

        document_groups = (
            response.get("documents")
            if isinstance(response, dict)
            else getattr(
                response,
                "documents",
                None,
            )
        ) or []

        metadata_groups = (
            response.get("metadatas")
            if isinstance(response, dict)
            else getattr(
                response,
                "metadatas",
                None,
            )
        ) or []

        distance_groups = (
            response.get("distances")
            if isinstance(response, dict)
            else getattr(
                response,
                "distances",
                None,
            )
        ) or []

        ids = (
            ids_groups[0]
            if ids_groups
            else []
        )

        documents = (
            document_groups[0]
            if document_groups
            else []
        )

        metadatas = (
            metadata_groups[0]
            if metadata_groups
            else []
        )

        distances = (
            distance_groups[0]
            if distance_groups
            else []
        )

        results: list[
            SearchResult
        ] = []

        for index, chunk_id in enumerate(
            ids
        ):
            metadata = (
                metadatas[index]
                if index < len(metadatas)
                and metadatas[index]
                else {}
            )

            document_text = (
                documents[index]
                if index < len(documents)
                and documents[index]
                else ""
            )

            raw_distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            distance = (
                float(raw_distance)
                if raw_distance is not None
                else None
            )

            relevance_score = (
                max(
                    0.0,
                    min(
                        1.0,
                        1.0 - distance,
                    ),
                )
                if distance is not None
                else None
            )

            results.append(
                SearchResult(
                    chunk_id=str(
                        chunk_id
                    ),
                    document_id=str(
                        metadata.get(
                            "document_id",
                            "",
                        )
                    ),
                    document_title=str(
                        metadata.get(
                            "document_title",
                            "Untitled document",
                        )
                    ),
                    original_name=str(
                        metadata.get(
                            "original_name",
                            "",
                        )
                    ),
                    text=str(
                        document_text
                    ),
                    chunk_index=int(
                        metadata.get(
                            "chunk_index",
                            index,
                        )
                    ),
                    distance=distance,
                    relevance_score=(
                        relevance_score
                    ),
                )
            )

        return results

    def build_context(
        self,
        results: list[SearchResult],
        *,
        maximum_characters: int = 18_000,
    ) -> str:
        sections: list[str] = []
        used_characters = 0

        for source_number, result in enumerate(
            results,
            start=1,
        ):
            score_text = (
                f"{result.relevance_score:.2f}"
                if result.relevance_score
                is not None
                else "unknown"
            )

            section = (
                f"[Source {source_number}]\n"
                f"Document: "
                f"{result.document_title}\n"
                f"File: "
                f"{result.original_name}\n"
                f"Chunk: "
                f"{result.chunk_index + 1}\n"
                f"Relevance: "
                f"{score_text}\n\n"
                f"{result.text}"
            )

            remaining = (
                maximum_characters
                - used_characters
            )

            if remaining <= 0:
                break

            section = section[:remaining]

            sections.append(section)
            used_characters += len(section)

        return "\n\n---\n\n".join(
            sections
        )

    def reindex_documents(
        self,
        documents: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:
        indexed = 0
        skipped = 0
        failed: list[str] = []
        total_chunks = 0

        for document in documents:
            try:
                result = (
                    self.index_document(
                        document
                    )
                )

                if result["indexed"]:
                    indexed += 1
                    total_chunks += int(
                        result["chunk_count"]
                    )

                else:
                    skipped += 1

            except Exception as exc:
                failed.append(
                    f"{document.get('title', 'Untitled')}: "
                    f"{exc}"
                )

        return {
            "indexed_documents": indexed,
            "skipped_documents": skipped,
            "failed_documents": failed,
            "total_chunks": total_chunks,
        }