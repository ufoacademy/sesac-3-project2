from typing import List, Literal, Optional

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


class CandidateDimension(BaseModel):
    dimension_id: DimensionId

    score: Optional[float] = Field(
        default=None,
        ge=1,
        le=5,
    )

    confidence: float = Field(
        ge=0,
        le=1,
    )

    evidence_quote: Optional[str] = None

    evidence_source: Literal[
        "application",
        "scenario",
        "missing",
    ]

    reasoning: str

    status: Literal[
        "observed",
        "missing",
    ]

    follow_up_question: str

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
    summary: str
    dimensions: List[CandidateDimension]

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