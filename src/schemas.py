from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class TraitScores(BaseModel):
    pace_preference: int = Field(ge=1, le=5, description="신중함(1)~초고속 실행(5)")
    autonomy_preference: int = Field(ge=1, le=5, description="명확한 지시 선호(1)~완전 자율·책임(5)")
    hierarchy_tolerance: int = Field(ge=1, le=5, description="완전 수평 선호(1)~위계·프로세스 수용(5)")
    risk_tolerance: int = Field(ge=1, le=5, description="안정 추구(1)~과감한 도전(5)")
    collaboration_style: int = Field(ge=1, le=5, description="조화·합의 선호(1)~직설적 토론·피드백 선호(5)")
    growth_ambition: int = Field(ge=1, le=5, description="워라밸·안정 선호(1)~고성과·고압박 성장 선호(5)")


class CompanyCultureProfile(BaseModel):
    name: str = Field(description="기업 정식 명칭")
    one_line: str = Field(description="조직문화 한 줄 요약")
    core_values: List[str] = Field(description="핵심 가치 3~5개")
    work_style: str = Field(description="일하는 방식 서술")
    decision_making: str = Field(description="의사결정 방식 서술")
    traits: TraitScores
    who_thrives: List[str] = Field(description="이 조직에서 잘 적응하는 성향 3개")
    who_leaves_early: List[str] = Field(description="조기 퇴사 위험이 높은 성향 3개, 구체적 이유 포함")


class PersonalityProfile(TraitScores):
    personality_summary: str = Field(description="지원자 성향 한 줄 요약")


class FitAssessment(BaseModel):
    fit_score: int = Field(description="0~100 사이의 조직 적합도 점수")
    turnover_risk: Literal["낮음", "중간", "높음"] = Field(description="조기 퇴사 위험도")
    key_reasons: List[str] = Field(description="점수와 위험도 판단 근거 2~4개")
    onboarding_tip: str = Field(description="이 지원자가 해당 기업에 적응하기 위한 조언 한 문장")


DimensionId = Literal[
    "pace_preference",
    "autonomy_preference",
    "hierarchy_tolerance",
    "risk_tolerance",
    "collaboration_style",
    "growth_ambition",
]


DIMENSION_IDS = {
    "pace_preference",
    "autonomy_preference",
    "hierarchy_tolerance",
    "risk_tolerance",
    "collaboration_style",
    "growth_ambition",
}


DEFAULT_FOLLOW_UP_QUESTIONS = {
    "pace_preference": "빠른 실행과 신중한 검토 중 하나를 선택해야 했던 경험을 말씀해 주세요.",
    "autonomy_preference": "명확한 지시 없이 스스로 일을 정의하고 진행했던 경험을 말씀해 주세요.",
    "hierarchy_tolerance": "상급자의 결정에 동의하지 않았을 때 어떻게 대응했는지 말씀해 주세요.",
    "risk_tolerance": "실패 가능성이 큰 시도를 선택했던 경험과 그 결과를 말씀해 주세요.",
    "collaboration_style": "동료와 의견이 크게 엇갈렸을 때 어떻게 피드백을 주고받았는지 말씀해 주세요.",
    "growth_ambition": "높은 성과 압박 속에서 성장했던 경험이나 피했던 경험을 말씀해 주세요.",
}

TEN_POINT_SCALE_MAX = 10
FIVE_POINT_SCALE_MAX = 5


def _normalize_candidate_score(raw_score: Any) -> Optional[float]:
    """LLM이 반환한 점수를 1~5 범위로 보정한다.

    - None/빈 값/숫자가 아닌 값 -> None
    - 5 초과 10 이하 -> 10점 척도로 간주하여 절반으로 환산 (예: 8 -> 4.0)
    - 그 외 범위 밖 값 -> 1~5로 clamp
    """
    if raw_score is None or raw_score == "":
        return None
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return None
    if FIVE_POINT_SCALE_MAX < score <= TEN_POINT_SCALE_MAX:
        score = score / 2
    return min(max(score, 1.0), float(FIVE_POINT_SCALE_MAX))


class CandidateDimension(BaseModel):
    dimension_id: DimensionId

    score: Optional[float] = Field(
        default=None,
        ge=1,
        le=5,
        description="1~5 정수 척도 점수. 10점 척도 금지. status가 missing이면 null.",
    )

    confidence: float = Field(
        ge=0,
        le=1,
        description="근거 확실성 0.0~1.0",
    )

    evidence_quote: Optional[str] = Field(
        default=None,
        description="지원서/상황 답변 원문 구절. status가 missing이면 null.",
    )

    evidence_source: Literal[
        "application",
        "scenario",
        "missing",
    ] = Field(description="application, scenario, missing 중 하나")

    reasoning: str = Field(description="점수 판단 이유")

    status: Literal[
        "observed",
        "missing",
    ] = Field(description="필수. 근거가 있으면 observed, 없으면 missing")

    follow_up_question: str = Field(
        description="필수. 면접에서 확인할 후속 질문 한 문장",
    )

    @model_validator(mode="before")
    @classmethod
    def fill_omitted_fields(cls, data: Any) -> Any:
        """비엄격(non-strict) 구조화 출력에서 LLM이 누락/오기한 필드를 보정한다.

        - score: 10점 척도 등 범위 밖 값을 1~5로 환산
        - status 누락: score/evidence_quote/evidence_source로 추론
        - evidence_source 누락: 인용이 있으면 application, 없으면 missing
        - follow_up_question/reasoning/confidence 누락: 안전한 기본값
        - status가 missing이면 score/evidence_quote를 비우고 출처를 missing으로 정렬
        """
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        normalized["score"] = _normalize_candidate_score(normalized.get("score"))

        quote = normalized.get("evidence_quote") or None
        normalized["evidence_quote"] = quote

        source = normalized.get("evidence_source")
        if source not in ("application", "scenario", "missing"):
            source = "application" if quote else "missing"
        normalized["evidence_source"] = source

        has_score_and_quote = (
            normalized["score"] is not None and quote is not None
        )
        status = normalized.get("status")
        if status not in ("observed", "missing"):
            status = (
                "observed"
                if has_score_and_quote and source != "missing"
                else "missing"
            )
        if status == "observed" and not has_score_and_quote:
            # observed라고 했지만 점수나 인용이 없으면 근거 부족으로 강등
            status = "missing"
        if status == "observed" and source == "missing":
            normalized["evidence_source"] = "application"
        normalized["status"] = status

        if status == "missing":
            normalized["score"] = None
            normalized["evidence_quote"] = None
            normalized["evidence_source"] = "missing"

        if not normalized.get("follow_up_question"):
            normalized["follow_up_question"] = DEFAULT_FOLLOW_UP_QUESTIONS.get(
                normalized.get("dimension_id"),
                "이 성향을 보여주는 구체적인 경험을 말씀해 주세요.",
            )

        if not normalized.get("reasoning"):
            normalized["reasoning"] = "LLM이 판단 이유를 제공하지 않았습니다."

        try:
            confidence = float(normalized.get("confidence"))
        except (TypeError, ValueError):
            confidence = 0.0 if status == "missing" else 0.5
        normalized["confidence"] = min(max(confidence, 0.0), 1.0)

        return normalized

    @model_validator(mode="after")
    def validate_status_and_evidence(self):
        if self.status == "observed":
            if self.score is None:
                raise ValueError(
                    "근거가 있는 문화축에는 점수가 필요합니다."
                )

            if not self.evidence_quote:
                raise ValueError(
                    "근거가 있는 문화축에는 원문 인용이 필요합니다."
                )

            if self.evidence_source == "missing":
                raise ValueError(
                    "근거가 있는 문화축의 출처는 missing일 수 없습니다."
                )

        if self.status == "missing":
            if self.score is not None:
                raise ValueError(
                    "근거가 없는 문화축의 점수는 비워야 합니다."
                )

            if self.evidence_source != "missing":
                raise ValueError(
                    "근거가 없는 문화축의 출처는 missing이어야 합니다."
                )

        return self


class CandidateCultureProfile(BaseModel):
    summary: str = Field(
        description="지원자 조직문화 성향 1~2문장 종합 요약문"
    )
    dimensions: List[CandidateDimension] = Field(
        description="6개 문화축 분석 결과 목록"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_profile(cls, data: Any) -> Any:
        """LLM이 summary 필드를 누락하거나 dimensions 키를 다른 이름으로 반환할 때 안전하게 자동 보정한다."""
        if not isinstance(data, dict):
            return data

        normalized = dict(data)

        # 1. dimensions 필드 키 별칭 대응 (culture_dimensions, traits 등)
        raw_dims = (
            normalized.get("dimensions")
            or normalized.get("culture_dimensions")
            or normalized.get("traits")
            or []
        )
        if not isinstance(raw_dims, list):
            raw_dims = []

        # 2. summary 필드 누락 보정 (overview, description 등 별칭 확인 후 미제공 시 자동 합성)
        summary = (
            normalized.get("summary")
            or normalized.get("candidate_summary")
            or normalized.get("overview")
            or normalized.get("description")
        )
        if not summary:
            observed_count = sum(
                1
                for d in raw_dims
                if isinstance(d, dict) and d.get("status") == "observed"
            )
            summary = (
                f"지원자 6대 업무문화축 분석 완료 (관찰된 근거: {observed_count}개 축)"
                if raw_dims
                else "지원자 업무 성향 및 문화 적합도 종합 분석 결과입니다."
            )
        normalized["summary"] = str(summary)

        # 3. 6개 문화축 중 빠진 축이 있는 경우 자동으로 missing 항목으로 보충하여 충돌 방지
        present_ids = {
            d.get("dimension_id")
            for d in raw_dims
            if isinstance(d, dict) and "dimension_id" in d
        }
        for dim_id in sorted(DIMENSION_IDS):
            if dim_id not in present_ids:
                raw_dims.append(
                    {
                        "dimension_id": dim_id,
                        "score": None,
                        "confidence": 0.0,
                        "evidence_quote": None,
                        "evidence_source": "missing",
                        "reasoning": (
                            "LLM 분석 결과에서 해당 문화축이 누락되어 정보 부족으로 자동 처리되었습니다."
                        ),
                        "status": "missing",
                        "follow_up_question": DEFAULT_FOLLOW_UP_QUESTIONS.get(
                            dim_id,
                            "이 문화축과 관련된 구체적인 경험을 말씀해 주세요.",
                        ),
                    }
                )

        normalized["dimensions"] = raw_dims
        return normalized

    @model_validator(mode="after")
    def require_all_six_dimensions(self):
        dimension_ids = [
            item.dimension_id
            for item in self.dimensions
        ]

        if (
            len(dimension_ids) != 6
            or set(dimension_ids) != DIMENSION_IDS
        ):
            raise ValueError(
                "지원자 프로필에는 서로 다른 6개 문화축이 필요합니다."
            )

        return self