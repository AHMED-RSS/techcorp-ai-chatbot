from __future__ import annotations

import hashlib

from typing import Any

import chromadb

from config.settings import Settings
from core.exceptions import FileProcessingError
from core.logging_config import get_logger
from core.providers import (
    AIProvider,
)
from services.rag_service import (
    RAGService,
    SearchResult,
    split_text_into_chunks,
)


logger = get_logger(__name__)


def user_collection_name(
    user_id: str,
) -> str:
    digest = hashlib.sha256(
        user_id.encode("utf-8")
    ).hexdigest()[:24]

    return (
        "techcorp_user_documents_"
        f"{digest}"
    )


class DatabaseRAGService(RAGService):
    """
    ChromaDB document index isolated to one authenticated user.
    """

    def __init__(
        self,
        *,
        user_id: str,
        settings: Settings,
        ai_provider: AIProvider | None = None,
        ollama_manager: AIProvider | None = None,
    ) -> None:
        cleaned_user_id = str(
            user_id or ""
        ).strip()

        if not cleaned_user_id:
            raise FileProcessingError(
                "A user ID is required for document indexing."
            )

        self.user_id = cleaned_user_id

        if ai_provider is None:
            ai_provider = ollama_manager

        self.settings = settings
        self.ai = ai_provider

        self.settings.chroma_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.collection_name = (
            user_collection_name(
                self.user_id
            )
        )

        try:
            self.client = (
                chromadb.PersistentClient(
                    path=str(
                        self.settings.chroma_folder
                    )
                )
            )

            self.collection = (
                self.client
                .get_or_create_collection(
                    name=self.collection_name,
                    metadata={
                        "hnsw:space": "cosine",
                        "owner_hash": (
                            hashlib.sha256(
                                self.user_id.encode(
                                    "utf-8"
                                )
                            ).hexdigest()
                        ),
                    },
                )
            )

        except Exception as exc:
            raise FileProcessingError(
                "Could not initialise the "
                f"user document index: {exc}"
            ) from exc

    def count_chunks(
        self,
    ) -> int:
        try:
            return int(
                self.collection.count()
            )

        except Exception:
            return 0

    def index_document(
        self,
        document: dict[str, Any],
    ) -> dict[str, Any]:
        document_owner = str(
            document.get("user_id")
            or self.user_id
        ).strip()

        if document_owner != self.user_id:
            raise FileProcessingError(
                "Cannot index another user's document."
            )

        document_id = str(
            document.get("id")
            or document.get("document_id")
            or ""
        ).strip()

        if not document_id:
            raise FileProcessingError(
                "Document has no identifier."
            )

        filename = str(
            document.get("original_name")
            or document.get("filename")
            or "unknown"
        )

        document_title = str(
            document.get("title")
            or filename
        )

        text = str(
            document.get("text")
            or document.get("extracted_text")
            or ""
        )

        if not text.strip():
            return {
                "indexed": False,
                "document_id": document_id,
                "chunk_count": 0,
                "reason": "Empty document text",
            }

        chunks = split_text_into_chunks(
            document_id=document_id,
            document_title=document_title,
            original_name=filename,
            text=text,
        )

        if not chunks:
            return {
                "indexed": False,
                "document_id": document_id,
                "chunk_count": 0,
                "reason": "No chunks generated",
            }

        self.delete_document(
            document_id
        )

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []
        embeddings: list[list[float]] = []

        for chunk in chunks:
            ids.append(
                chunk.id
            )

            texts.append(
                chunk.text
            )

            metadata = chunk.metadata()
            metadata["user_id"] = (
                self.user_id
            )

            metadatas.append(
                metadata
            )

            embeddings.append(
                self.ai.embed(
                    chunk.text,
                    model=(
                        self.settings
                        .ollama_embed_model
                    ),
                )
            )

        try:
            self.collection.upsert(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings,
            )

        except Exception as exc:
            raise FileProcessingError(
                "Could not index the user "
                f"document: {exc}"
            ) from exc

        logger.info(
            "Indexed %s chunks for user collection %s",
            len(chunks),
            self.collection_name,
        )

        return {
            "indexed": True,
            "document_id": document_id,
            "chunk_count": len(chunks),
        }

    def search(
        self,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        cleaned_query = str(
            query or ""
        ).strip()

        if not cleaned_query:
            return []

        if self.count_chunks() == 0:
            return []

        selected_ids = [
            str(document_id).strip()
            for document_id in (
                document_ids or []
            )
            if str(document_id).strip()
        ]

        where: dict[str, Any] | None = None

        if len(selected_ids) == 1:
            where = {
                "document_id": {
                    "$eq": selected_ids[0]
                }
            }

        elif len(selected_ids) > 1:
            where = {
                "document_id": {
                    "$in": selected_ids
                }
            }

        try:
            embedding = self.ai.embed(
                cleaned_query,
                model=(
                    self.settings
                    .ollama_embed_model
                ),
            )

            arguments: dict[str, Any] = {
                "query_embeddings": [
                    embedding
                ],
                "n_results": max(
                    1,
                    min(
                        int(top_k),
                        self.count_chunks(),
                    ),
                ),
            }

            if where is not None:
                arguments["where"] = where

            result = self.collection.query(
                **arguments
            )

        except Exception as exc:
            raise FileProcessingError(
                "Could not search the user "
                f"document index: {exc}"
            ) from exc

        ids = result.get(
            "ids",
            [[]],
        )[0]

        documents = result.get(
            "documents",
            [[]],
        )[0]

        metadatas = result.get(
            "metadatas",
            [[]],
        )[0]

        distances = result.get(
            "distances",
            [[]],
        )[0]

        results: list[
            SearchResult
        ] = []

        for index, text in enumerate(
            documents
        ):
            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else {}
            ) or {}

            if (
                str(
                    metadata.get(
                        "user_id",
                        "",
                    )
                )
                != self.user_id
            ):
                continue

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            score = (
                1 - float(distance)
                if distance is not None
                else None
            )

            results.append(
                SearchResult(
                    chunk_id=(
                        ids[index]
                        if index < len(ids)
                        else ""
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
                            "",
                        )
                    ),
                    original_name=str(
                        metadata.get(
                            "original_name",
                            "",
                        )
                    ),
                    text=str(
                        text or ""
                    ),
                    chunk_index=int(
                        metadata.get(
                            "chunk_index",
                            0,
                        )
                    ),
                    distance=distance,
                    relevance_score=score,
                )
            )

        return results

    def delete_document(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        cleaned_id = str(
            document_id or ""
        ).strip()

        if not cleaned_id:
            return {
                "deleted": False,
                "document_id": "",
                "deleted_chunks": 0,
            }

        try:
            result = self.collection.get(
                where={
                    "document_id": {
                        "$eq": cleaned_id
                    }
                }
            )

            ids = list(
                result.get(
                    "ids",
                    [],
                )
            )

            if ids:
                self.collection.delete(
                    ids=ids
                )

            return {
                "deleted": True,
                "document_id": cleaned_id,
                "deleted_chunks": len(ids),
            }

        except Exception as exc:
            raise FileProcessingError(
                "Could not delete the user "
                f"document index: {exc}"
            ) from exc

    def reindex_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            existing = self.collection.get()

            existing_ids = list(
                existing.get(
                    "ids",
                    [],
                )
            )

            if existing_ids:
                self.collection.delete(
                    ids=existing_ids
                )

        except Exception as exc:
            raise FileProcessingError(
                "Could not clear the user "
                f"document index: {exc}"
            ) from exc

        indexed = 0
        total_chunks = 0
        failures: list[str] = []

        for document in documents:
            try:
                result = self.index_document(
                    document
                )

                if result.get(
                    "indexed"
                ):
                    indexed += 1

                    total_chunks += int(
                        result.get(
                            "chunk_count",
                            0,
                        )
                    )

            except Exception as exc:
                failures.append(
                    str(exc)
                )

        return {
            "indexed_documents": indexed,
            "failed_documents": failures,
            "total_chunks": total_chunks,
        }

    def delete_user_index(
        self,
    ) -> dict[str, int | str | bool]:
        """
        Delete this authenticated user's complete collection.
        """

        deleted_chunks = self.count_chunks()

        try:
            self.client.delete_collection(
                name=self.collection_name
            )

        except Exception as exc:
            raise FileProcessingError(
                "Could not delete the user's "
                f"document index: {exc}"
            ) from exc

        return {
            "deleted": True,
            "collection": self.collection_name,
            "deleted_chunks": deleted_chunks,
        }






