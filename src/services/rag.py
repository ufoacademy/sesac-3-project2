from dotenv import load_dotenv
load_dotenv() 
import os
import glob
from functools import lru_cache
from typing import Optional, List
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from src.services.company_registry import SOURCE_DIRECTORY, list_company_ids

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    timeout=45,
    max_retries=1,
)

def _load_documents() -> List[Document]:
    docs = []
    for company_id in list_company_ids():
        folder = SOURCE_DIRECTORY / company_id
        for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            docs.append(Document(
                page_content=text,
                metadata={"company_id": company_id, "source": os.path.basename(path)},
            ))
    return docs

def _source_signature() -> tuple[tuple[str, int, int], ...]:
    """Make the vector-store cache change when source files change."""

    files = [
        path
        for company_id in list_company_ids()
        for path in (SOURCE_DIRECTORY / company_id).glob("*.txt")
        if path.is_file()
    ]
    return tuple(
        sorted(
            (
                str(path),
                path.stat().st_mtime_ns,
                path.stat().st_size,
            )
            for path in files
        )
    )


@lru_cache(maxsize=4)
def _get_vector_store(
    source_signature: tuple[tuple[str, int, int], ...],
) -> InMemoryVectorStore:
    store = InMemoryVectorStore(embeddings)
    store.add_documents(_load_documents())
    return store

def get_vector_store() -> InMemoryVectorStore:
    """Return a store rebuilt automatically when source data changes."""

    return _get_vector_store(_source_signature())

def retrieve(query: str, company_id: Optional[str] = None, k: int = 3) -> List[Document]:
    store = get_vector_store()
    filter_fn = (lambda doc: doc.metadata.get("company_id") == company_id) if company_id else None
    return store.similarity_search(query, k=k, filter=filter_fn)
