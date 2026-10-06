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
    set_current_application_text,
    verify_application_quote,
)
from src.schemas import CandidateCultureProfile


AGENT_TIMEOUT_SECONDS = 120
AGENT_RECURSION_LIMIT = 12


@lru_cache(maxsize=1)
def get_company_subagent():
    """Create the company-culture research subagent once per process."""

    return create_agent(
        model=ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            timeout=AGENT_TIMEOUT_SECONDS,
            max_retries=3,
        ),
        tools=[inspect_company_profile, search_company_documents],
        system_prompt=(
            "당신은 기업의 조직문화를 조사하고 분석하는 전문 서브에이전트입니다. "
            "반드시 inspect_company_profile과 search_company_documents 도구를 활용하여 "
            "실행 속도(pace), 자율성(autonomy), 위계(hierarchy), 위험 감수(risk), 협업(collaboration), 성장(growth) 축의 "
            "구체적이고 신뢰할 수 있는 근거를 조사하세요. "
            "도구가 반환한 정보만을 바탕으로 CompanyEvidenceResult 형식으로 작성하세요.\n"
            "핵심 규칙:\n"
            "1. 언어 규칙: summary, text, relevance 등 모든 서술형 텍스트는 반드시 자연스럽고 정중한 한국어로 작성하세요. 영어를 절대 사용하지 마세요.\n"
            "2. 형식 규칙: 각 evidence 항목의 'source'는 반드시 단일 문자열(예: '공식 가치 문서', '채용 공고')이어야 하며, 딕셔너리나 객체여서는 안 됩니다."
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
            max_retries=3,
        ),
        tools=[
            extract_application_pdf,
            search_application_evidence,
            verify_application_quote,
        ],
        system_prompt=(
            "당신은 지원자의 업무 성향과 조직문화 적합도를 분석하는 전문 서브에이전트입니다. "
            "제공된 지원서 원문(PDF 추출 텍스트)과 5개 문제해결 상황 답변을 종합적으로 분석하여 "
            "6대 업무문화축(실행 속도, 자율성, 위계 수용, 위험 감수, 협업 스타일, 성장 지향성) 프로필을 도출하세요. "
            "지원서 텍스트는 이미 도구에 로드되어 있으므로 verify_application_quote 호출 시 'quote' 파라미터만 전달하면 됩니다.\n"
            "핵심 작성 원칙:\n"
            "1. 언어 규칙 (필수): summary, reasoning, follow_up_question 등 모든 텍스트는 반드시 자연스럽고 정중한 한국어로 작성하세요. 절대로 영어를 사용하지 마세요.\n"
            "2. 원문 인용 규칙: evidence_quote는 지원서 원문이나 상황 답변에 실제로 적혀 있는 한국어 문장을 그대로 발췌하세요. 절대로 영어로 번역하지 마세요.\n"
            "3. 상황 답변 적극 활용: 지원서에 특정 문화축(예: 성장 지향성, 위험 감수)의 직접적 언급이 부족하더라도 5개 상황 답변(scenario answers)에서 드러나는 지원자의 행동 패턴과 의도를 면밀히 포착하여 최대한 근거를 확보하세요.\n"
            "4. 스키마 필수 규칙:\n"
            "- 최상위 객체에는 반드시 'summary'(한국어 1~2문장 종합 요약)와 'dimensions'(6개 축 목록)가 포함되어야 합니다.\n"
            "- 각 dimension 객체는 8개 키(dimension_id, score, confidence, evidence_quote, evidence_source, reasoning, status, follow_up_question)를 모두 포함해야 합니다.\n"
            "- score는 1~5 정수 척도만 사용하세요 (10점 척도 절대 금지).\n"
            "- status는 행동 근거가 확인되면 'observed', 근거가 전혀 없을 때만 'missing'으로 작성하세요.\n"
            "- status가 'missing'인 경우 score와 evidence_quote는 null로 비우고, evidence_source는 'missing'으로 지정하세요.\n"
            "- follow_up_question은 면접관이 지원자에게 심층 확인할 수 있는 정중한 한국어 질문 1문장으로 작성하세요."
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
                        f"기업 '{company_id}'의 조직문화를 정밀 분석하세요. "
                        "실행 속도, 자율성, 위계, 위험 감수, 협업, 성장 6개 축을 포괄하는 "
                        "핵심 근거를 수집하고 모든 내용을 반드시 한국어로 작성하세요."
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

    set_current_application_text(application_text)
    prompt = (
        "다음 지원자의 서류와 상황 답변을 분석하여 6대 업무문화축 프로필을 도출하세요.\n"
        "지원서 원문뿐만 아니라 5개 상황 질문 답변 전체를 면밀히 검토하여, "
        "성장 지향성(growth_ambition)을 포함한 모든 문화축의 행동 근거를 누락 없이 포착하세요.\n\n"
        f"지원서 파일: {application_path}\n\n"
        f"[지원서 추출 원문]\n{application_text}\n\n"
        f"[문제해결 상황 답변]\n{json.dumps(answers, ensure_ascii=False, indent=2)}\n\n"
        "주의: summary, reasoning, follow_up_question 등 모든 답변은 반드시 100% 자연스러운 한국어로 작성하세요."
    )
    result = get_candidate_subagent().invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"recursion_limit": AGENT_RECURSION_LIMIT},
    )
    structured_response = result.get("structured_response")
    if structured_response is None:
        raise ValueError("지원자 서브에이전트가 구조화된 결과를 반환하지 않았습니다.")
    return CandidateCultureProfile.model_validate(structured_response)
