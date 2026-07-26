from __future__ import annotations

import hashlib
import re

from dataclasses import dataclass
from typing import Any

import chromadb

from config.settings import Settings

from core.exceptions import FileProcessingError

from core.logging_config import get_logger

from core.ollama_client import OllamaManager


logger = get_logger(__name__)


COLLECTION_NAME = "techcorp_local_documents_v1"



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

            "document_id":
                self.document_id,

            "document_title":
                self.document_title,

            "original_name":
                self.original_name,

            "chunk_index":
                self.chunk_index,

            "character_start":
                self.character_start,

            "character_end":
                self.character_end,

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

            "chunk_id":
                self.chunk_id,

            "document_id":
                self.document_id,

            "document_title":
                self.document_title,

            "original_name":
                self.original_name,

            "text":
                self.text,

            "chunk_index":
                self.chunk_index,

            "distance":
                self.distance,

            "relevance_score":
                self.relevance_score,

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


    cleaned_text = normalise_chunk_text(
        text
    )


    if not cleaned_text:

        return []



    chunks = []

    text_length = len(cleaned_text)

    start = 0

    chunk_index = 0



    while start < text_length:


        end = min(

            start + chunk_size,

            text_length

        )


        chunk_text = cleaned_text[start:end].strip()



        if chunk_text:


            chunks.append(

                TextChunk(

                    id=stable_chunk_id(

                        document_id,

                        chunk_index,

                        chunk_text,

                    ),

                    document_id=document_id,

                    document_title=document_title,

                    original_name=original_name,

                    text=chunk_text,

                    chunk_index=chunk_index,

                    character_start=start,

                    character_end=end,

                )

            )


            chunk_index += 1



        if end >= text_length:

            break



        start = max(

            end - chunk_overlap,

            0

        )



    return chunks





class RAGService:


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

            self.client = chromadb.PersistentClient(

                path=str(

                    self.settings.chroma_folder

                )

            )



            self.collection = (

                self.client

                .get_or_create_collection(

                    name=COLLECTION_NAME,

                    metadata={

                        "hnsw:space":

                            "cosine",

                    },

                )

            )


        except Exception as exc:


            raise FileProcessingError(

                f"Could not initialise ChromaDB: {exc}"

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

        filename = str(
            document.get(
                "original_name",
                document.get(
                    "filename",
                    "unknown",
                ),
            )
        )

        text = str(
            document.get(
                "text",
                "",
            )
        )

        if not text.strip():

            return {
                "indexed": False,
                "chunk_count": 0,
                "reason": "Empty document text",
            }

        document_id = hashlib.sha256(
            filename.encode("utf-8")
        ).hexdigest()[:16]


        chunks = split_text_into_chunks(
            document_id=document_id,
            document_title=filename,
            original_name=filename,
            text=text,
        )


        ids = []
        documents = []
        metadatas = []
        embeddings = []


        for chunk in chunks:

            ids.append(chunk.id)

            documents.append(
                chunk.text
            )

            metadatas.append(
                chunk.metadata()
            )

            embeddings.append(
                self.ollama.embed(
                    chunk.text,
                    model=self.settings.ollama_embed_model,
                )
            )


        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )


        return {
            "indexed": True,
            "document_id": document_id,
            "chunk_count": len(chunks),
        }




    def index_document(
        self,
        document: dict[str, Any],
    ) -> dict[str, Any]:


        filename = str(

            document.get(

                "original_name",

                document.get(

                    "filename",

                    "unknown",

                ),

            )

        )



        document_id = str(

            document.get(

                "document_id",

                hashlib.sha256(

                    filename.encode(

                        "utf-8"

                    )

                ).hexdigest()[:16],

            )

        )



        document_title = str(

            document.get(

                "document_title",

                document.get(

                    "title",

                    filename,

                ),

            )

        )



        text = str(

            document.get(

                "text",

                "",

            )

        )


        if not text.strip():

            return {

                "indexed": False,

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

                "chunk_count": 0,

                "reason": "No chunks generated",

            }
        ids = []

        documents = []

        metadatas = []

        embeddings = []



        for chunk in chunks:


            ids.append(

                chunk.id

            )


            documents.append(

                chunk.text

            )


            metadatas.append(

                chunk.metadata()

            )


            embeddings.append(

                self.ollama.embed(

                    chunk.text,

                    model=self.settings.ollama_embed_model,

                )

            )



        self.collection.upsert(

            ids=ids,

            documents=documents,

            metadatas=metadatas,

            embeddings=embeddings,

        )



        logger.info(

            "Indexed %s chunks from %s",

            len(chunks),

            filename,

        )



        return {

            "indexed": True,

            "document_id": document_id,

            "chunk_count": len(chunks),

        }





    def build_context(
        self,
        results: list[SearchResult],
        *,
        maximum_characters: int = 18000,
    ) -> str:


        sections = []

        current_length = 0



        for index, result in enumerate(

            results,

            start=1

        ):


            section = (

                f"[Source {index}]\n"

                f"Document: {result.document_title}\n"

                f"File: {result.original_name}\n"

                f"Chunk: {result.chunk_index}\n\n"

                f"{result.text}"

            )



            if (

                current_length + len(section)

                > maximum_characters

            ):

                break



            sections.append(

                section

            )


            current_length += len(section)



        return "\n\n---\n\n".join(

            sections

        )





    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:


        embedding = self.ollama.embed(

            query,

            model=self.settings.ollama_embed_model,

        )



        result = self.collection.query(

            query_embeddings=[embedding],

            n_results=top_k,

        )



        results = []



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



        for index, text in enumerate(documents):


            metadata = (

                metadatas[index]

                if index < len(metadatas)

                else {}

            )



            distance = (

                distances[index]

                if index < len(distances)

                else None

            )



            score = None



            if distance is not None:

                score = 1 - float(distance)



            results.append(

                SearchResult(

                    chunk_id=(

                        ids[index]

                        if index < len(ids)

                        else ""

                    ),

                    document_id=metadata.get(

                        "document_id",

                        "",

                    ),

                    document_title=metadata.get(

                        "document_title",

                        "",

                    ),

                    original_name=metadata.get(

                        "original_name",

                        "",

                    ),

                    text=text,

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


    def reindex_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:


        indexed = 0

        failed = []

        total_chunks = 0



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


                failed.append(

                    str(exc)

                )



        return {

            "indexed_documents":

                indexed,


            "failed_documents":

                failed,


            "total_chunks":

                total_chunks,

        }





    def delete_document(
        self,
        document_id: str,
    ) -> dict[str, Any]:


        try:


            result = self.collection.get(

                where={

                    "document_id":

                        document_id

                }

            )


            ids = result.get(

                "ids",

                []

            )


            if ids:


                self.collection.delete(

                    ids=ids

                )



            return {

                "deleted": True,

                "document_id": document_id,

                "deleted_chunks": len(ids),

            }



        except Exception as exc:


            logger.error(

                "Failed deleting document %s: %s",

                document_id,

                exc,

            )


            return {

                "deleted": False,

                "document_id": document_id,

                "error": str(exc),

            }

        