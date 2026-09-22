from dotenv import load_dotenv
load_dotenv()  # .env 파일의 환경변수(OPENAI_API_KEY 등)를 메모리로 불러옴

import os
import glob
from functools import lru_cache
from typing import Optional, List
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document

COMPANY_IDS = ["toss", "hyundai", "baemin"]
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def _load_documents() -> List[Document]:
    docs = []
    for company_id in COMPANY_IDS:
        folder = os.path.join("data", "sources", company_id)
        for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            docs.append(Document(
                page_content=text,
                metadata={"company_id": company_id, "source": os.path.basename(path)},
            ))
    return docs

@lru_cache(maxsize=1)
def get_vector_store() -> InMemoryVectorStore:
    store = InMemoryVectorStore(embeddings)
    store.add_documents(_load_documents())
    return store

def retrieve(query: str, company_id: Optional[str] = None, k: int = 3) -> List[Document]:
    store = get_vector_store()
    filter_fn = (lambda doc: doc.metadata.get("company_id") == company_id) if company_id else None
    return store.similarity_search(query, k=k, filter=filter_fn)