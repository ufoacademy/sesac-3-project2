"""Tool-using subagents orchestrated by the LangGraph supervisor."""

import json
from functools import lru_cache

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from src.agent_schemas import CompanyEvidenceResult
from src.agents.agent_tools import (
    extract_application_pdf,
    inspect_company_profile,
    search_application_evidence,
    search_company_documents,
    verify_application_quote,
)
from src.schemas import CandidateCultureProfile


AGENT_TIMEOUT_SECONDS = 45
AGENT_RECURSION_LIMIT = 12


@lru_cache(maxsize=1)
def get_company_subagent():
    """Create the company-culture research subagent once per process."""

    return create_agent(
        model=ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            timeout=AGENT_TIMEOUT_SECONDS,
            max_retries=1,
        ),
        tools=[inspect_company_profile, search_company_documents],
        system_prompt=(
            "You are the company-culture research subagent. "
            "Use inspect_company_profile and search_company_documents before "
            "writing your answer. Search at least three focused queries covering "
            "work style, decision making, risk, collaboration, and growth. "
            "Only include evidence returned by the tools. Return the requested "
            "CompanyEvidenceResult with concise grounded excerpts."
        ),
        response_format=CompanyEvidenceResult,
        name="company_culture_subagent",
    )


@lru_cache(maxsize=1)
def get_candidate_subagent():
    """Create the applicant-analysis subagent once per process."""

    return create_agent(
        model=ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            timeout=AGENT_TIMEOUT_SECONDS,
            max_retries=1,
        ),
        tools=[
            extract_application_pdf,
            search_application_evidence,
            verify_application_quote,
        ],
        system_prompt=(
            "You are the applicant-culture subagent. Analyze only the supplied "
            "application and scenario answers. Use extract_application_pdf to "
            "verify the PDF text, use search_application_evidence for relevant "
            "passages, and use verify_application_quote before accepting each "
            "application quote. Return all six culture dimensions in the exact "
            "CandidateCultureProfile schema. Do not invent evidence; mark a "
            "dimension missing when there is not enough support."
        ),
        response_format=CandidateCultureProfile,
        name="candidate_culture_subagent",
    )


def run_company_subagent(company_id: str) -> CompanyEvidenceResult:
    """Run the company subagent with a focused research request."""

    result = get_company_subagent().invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Analyze company '{company_id}'. "
                        "Produce evidence useful for comparing a candidate across "
                        "pace, autonomy, hierarchy, risk, collaboration, and growth."
                    ),
                }
            ]
        },
        config={"recursion_limit": AGENT_RECURSION_LIMIT},
    )
    structured_response = result.get("structured_response")
    if structured_response is None:
        raise ValueError("회사 서브에이전트가 구조화된 결과를 반환하지 않았습니다.")
    return CompanyEvidenceResult.model_validate(structured_response)


def run_candidate_subagent(
    application_path: str,
    application_text: str,
    answers: dict[str, str],
) -> CandidateCultureProfile:
    """Run the candidate subagent with extracted PDF text and answers."""

    prompt = (
        "Analyze this applicant. The supervisor already extracted the PDF text, "
        "but you may re-extract it with the tool to verify it.\n\n"
        f"PDF path: {application_path}\n\n"
        f"Extracted application text:\n{application_text}\n\n"
        f"Scenario answers:\n{json.dumps(answers, ensure_ascii=False, indent=2)}"
    )
    result = get_candidate_subagent().invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"recursion_limit": AGENT_RECURSION_LIMIT},
    )
    structured_response = result.get("structured_response")
    if structured_response is None:
        raise ValueError("지원자 서브에이전트가 구조화된 결과를 반환하지 않았습니다.")
    return CandidateCultureProfile.model_validate(structured_response)
