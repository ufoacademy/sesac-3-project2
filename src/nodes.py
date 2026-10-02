import hashlib
from pathlib import Path

from src.candidate_analyzer import analyze_candidate
from src.company_loader import load_company_profile
from src.database import (
    load_cached_candidate_profile,
    save_analysis,
)
from src.pdf_loader import extract_pdf_text
from src.rag import retrieve
from src.schemas import CandidateCultureProfile
from src.scoring import calculate_fit
from src.state import State


PROJECT_ROOT = Path(__file__).resolve().parents[1]


COMPANY_IDS = {
    "toss",
    "hyundai",
    "baemin",
}


REQUIRED_ANSWER_IDS = {
    "q1",
    "q2",
    "q3",
    "q4",
    "q5",
}


DIMENSION_IDS = {
    "pace_preference",
    "autonomy_preference",
    "hierarchy_tolerance",
    "risk_tolerance",
    "collaboration_style",
    "growth_ambition",
}


def validate_input_node(
    state: State,
) -> dict:
    """회사, PDF, 상황 답변 입력을 검사한다."""

    selected_company = state.get(
        "selected_company"
    )

    if selected_company not in COMPANY_IDS:
        raise ValueError(
            "토스, 현대차, 배민 중 회사를 선택해야 합니다."
        )

    application_path = Path(
        state.get("application_path", "")
    )

    if (
        not application_path.exists()
        or application_path.suffix.lower() != ".pdf"
    ):
        raise ValueError(
            "분석할 지원자 PDF를 선택해야 합니다."
        )

    answers = state.get(
        "scenario_answers",
        {},
    )

    answers_are_invalid = (
        set(answers) != REQUIRED_ANSWER_IDS
        or any(
            not isinstance(answer, str)
            or not answer.strip()
            for answer in answers.values()
        )
    )

    if answers_are_invalid:
        raise ValueError(
            "문제해결 상황 5개에 모두 답변해야 합니다."
        )

    if not state.get("db_path"):
        raise ValueError(
            "분석 결과를 저장할 DB 경로가 필요합니다."
        )

    return {
        "status": "validated",
        "retry_count": state.get(
            "retry_count",
            0,
        ),
        "error": None,
    }


def load_company_node(
    state: State,
) -> dict:
    """선택한 회사의 조직문화 JSON을 읽는다."""

    company_path = (
        PROJECT_ROOT
        / "data"
        / "companies"
        / f"{state['selected_company']}.json"
    )

    company_profile = load_company_profile(
        company_path
    )

    return {
        "company_data": company_profile.model_dump()
    }


def extract_pdf_node(
    state: State,
) -> dict:
    """지원자 PDF에서 자기소개서 글자를 추출한다."""

    application_text = extract_pdf_text(
        Path(state["application_path"])
    )

    return {
        "application_text": application_text
    }


def retrieve_company_evidence_node(
    state: State,
) -> dict:
    """RAG로 선택한 회사의 조직문화 근거를 검색한다."""

    query = (
        "조직문화 업무 속도 자율성 승인 절차 "
        "위계 위험 감수 협업 피드백 성장 방식"
    )

    documents = retrieve(
        query,
        company_id=state["selected_company"],
        k=3,
    )

    evidence = [
        {
            "source": document.metadata.get(
                "source",
                "",
            ),
            "text": document.page_content,
        }
        for document in documents
    ]

    return {
        "company_evidence": evidence
    }

def analyze_candidate_node(
    state: State,
) -> dict:
    """같은 지원자 입력은 재사용하고, 처음인 경우에만 LLM으로 분석한다."""

    application_path = Path(
        state["application_path"]
    )

    source_hash = hashlib.sha256(
        application_path.read_bytes()
    ).hexdigest()

    cached_profile_data = (
        load_cached_candidate_profile(
            Path(state["db_path"]),
            source_hash,
            state["scenario_answers"],
        )
    )

    if cached_profile_data is not None:
        cached_profile = (
            CandidateCultureProfile.model_validate(
                cached_profile_data
            )
        )

        return {
            "candidate_profile": (
                cached_profile.model_dump()
            ),
            "error": None,
            "status": "candidate_reused",
        }

    try:
        profile = analyze_candidate(
            state["application_text"],
            state["scenario_answers"],
        )

    except ValueError as error:
        return {
            "candidate_profile": {},
            "retry_count": (
                state.get("retry_count", 0)
                + 1
            ),
            "error": str(error),
        }

    return {
        "candidate_profile": profile.model_dump(),
        "error": None,
        "status": "candidate_analyzed",
    }


def calculate_fit_node(
    state: State,
) -> dict:
    """회사 점수와 지원자 점수의 적합도를 계산한다."""

    candidate_profile = (
        CandidateCultureProfile.model_validate(
            state["candidate_profile"]
        )
    )

    candidate_scores = {
        dimension.dimension_id: dimension.score
        for dimension in candidate_profile.dimensions
    }

    company_scores = state[
        "company_data"
    ]["traits"]

    fit_result = calculate_fit(
        company_scores,
        candidate_scores,
    )

    return {
        "fit_result": fit_result
    }


def generate_report_node(
    state: State,
) -> dict:
    """계산 결과와 근거를 하나의 최종 보고서로 결합한다."""

    candidate_profile = (
        CandidateCultureProfile.model_validate(
            state["candidate_profile"]
        )
    )

    candidate_by_dimension = {
        dimension.dimension_id: dimension
        for dimension in candidate_profile.dimensions
    }

    dimensions = {
        dimension_id: detail.copy()
        for dimension_id, detail
        in state["fit_result"]["dimensions"].items()
    }

    for dimension_id, result in dimensions.items():
        candidate_detail = candidate_by_dimension[
            dimension_id
        ]

        result["confidence"] = (
            candidate_detail.confidence
        )
        result["evidence_quote"] = (
            candidate_detail.evidence_quote
        )
        result["evidence_source"] = (
            candidate_detail.evidence_source
        )
        result["reasoning"] = (
            candidate_detail.reasoning
        )
        result["status"] = (
            candidate_detail.status
        )
        result["follow_up_question"] = (
            candidate_detail.follow_up_question
        )

    application_path = Path(
        state["application_path"]
    )

    source_hash = hashlib.sha256(
        application_path.read_bytes()
    ).hexdigest()

    report = {
        "company_id": state["selected_company"],
        "applicant_id": application_path.stem,
        "source_file": application_path.name,
        "source_hash": source_hash,
        "extracted_text": state[
            "application_text"
        ],
        "scenario_answers": state[
            "scenario_answers"
        ],
        "candidate_summary": (
            candidate_profile.summary
        ),
        "overall_fit": state[
            "fit_result"
        ]["overall_fit"],
        "coverage": state[
            "fit_result"
        ]["coverage"],
        "dimensions": dimensions,
        "company_evidence": state.get(
            "company_evidence",
            [],
        ),
    }

    return {
        "final_report": report
    }


def validate_result_node(
    state: State,
) -> dict:
    """최종 보고서에 필요한 결과가 모두 있는지 검사한다."""

    report = state["final_report"]

    if (
        set(report["dimensions"])
        != DIMENSION_IDS
    ):
        raise ValueError(
            "최종 결과에 6개 문화축이 모두 필요합니다."
        )

    if report["coverage"] <= 0:
        raise ValueError(
            "지원자 분석 근거가 하나 이상 필요합니다."
        )

    return {
        "status": "result_validated"
    }


def save_result_node(
    state: State,
) -> dict:
    """최종 보고서를 SQLite에 저장한다."""

    analysis_id = save_analysis(
        Path(state["db_path"]),
        state["final_report"],
    )

    return {
        "analysis_id": analysis_id,
        "status": "saved",
    }