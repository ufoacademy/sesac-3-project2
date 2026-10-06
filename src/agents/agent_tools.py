"""Tools exposed to the company and candidate subagents."""

import json
from pathlib import Path

from langchain_core.tools import tool

from src.services.company_loader import load_company_profile
from src.services.company_registry import company_profile_path
from src.services.pdf_loader import extract_pdf_text
from src.services.rag import retrieve


@tool
def inspect_company_profile(company_id: str) -> str:
    """Load the validated culture profile for a company."""

    profile = load_company_profile(company_profile_path(company_id))
    return profile.model_dump_json(ensure_ascii=False)


@tool
def search_company_documents(
    company_id: str,
    query: str,
    k: int = 3,
) -> str:
    """Search the company's source documents and return grounded excerpts."""

    documents = retrieve(query, company_id=company_id, k=k)
    results = [
        {
            "source": document.metadata.get("source", ""),
            "text": document.page_content,
        }
        for document in documents
    ]
    return json.dumps(results, ensure_ascii=False)


@tool
def extract_application_pdf(path: str) -> str:
    """Extract all text from an applicant PDF at the given path."""

    return extract_pdf_text(Path(path))


@tool
def search_application_evidence(
    application_text: str,
    query: str,
) -> str:
    """Find text passages in an extracted application relevant to a query."""

    normalized_query = {
        token.strip(".,!?()[]{}")
        for token in query.split()
        if token.strip(".,!?()[]{}")
    }
    paragraphs = [
        paragraph.strip()
        for paragraph in application_text.splitlines()
        if paragraph.strip()
    ]
    matching = [
        paragraph
        for paragraph in paragraphs
        if normalized_query.intersection(paragraph.split())
    ]

    if not matching:
        return "관련 문장을 찾지 못했습니다."
    return "\n".join(matching[:5])


@tool
def verify_application_quote(
    quote: str,
    application_text: str,
) -> str:
    """Verify that a proposed quote occurs in the extracted application text."""

    normalized_quote = " ".join(quote.split())
    normalized_text = " ".join(application_text.split())
    if normalized_quote and normalized_quote in normalized_text:
        return "verified"
    return "not_verified"
