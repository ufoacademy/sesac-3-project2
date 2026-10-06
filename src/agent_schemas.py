import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class CompanyEvidenceItem(BaseModel):
    source: str = Field(
        description="출처 문서명 또는 웹페이지 제목 (단일 문자열이어야 함. 예: 'Official Values Document', 'Job Posting Excerpt')"
    )
    text: str = Field(
        description="문서에서 발췌한 핵심 문장 또는 요약 내용"
    )
    relevance: str = Field(
        default="",
        description="해당 근거가 조직문화와 어떤 관련이 있는지 설명"
    )
    source_type: Literal["local", "web"] = Field(
        default="local",
        description="자료 출처 유형 ('local' 또는 'web')"
    )
    url: str | None = Field(
        default=None,
        description="웹 검색 결과인 경우 해당 페이지 URL"
    )

    @field_validator("source", mode="before")
    @classmethod
    def coerce_source_to_str(cls, value: Any) -> str:
        """LLM이 source를 {'title': '...', 'type': '...'} 형태의 딕셔너리로 반환할 때 문자열로 자동 변환한다."""
        if isinstance(value, dict):
            return str(
                value.get("title")
                or value.get("name")
                or value.get("source")
                or json.dumps(value, ensure_ascii=False)
            )
        if value is None:
            return ""
        return str(value)

    @field_validator("text", mode="before")
    @classmethod
    def coerce_text_to_str(cls, value: Any) -> str:
        """text 필드가 딕셔너리나 리스트로 전달될 경우 안전하게 문자열 변환한다."""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value or "")

    @field_validator("source_type", mode="before")
    @classmethod
    def coerce_source_type(cls, value: Any) -> str:
        """source_type이 딕셔너리로 넘어오거나 예상치 못한 값일 때 안전하게 보정한다."""
        if isinstance(value, dict):
            return value.get("type", "local")
        if value not in ("local", "web"):
            return "local"
        return value


class CompanyEvidenceResult(BaseModel):
    summary: str = Field(
        description="회사 조직문화 분석 전체 요약문"
    )
    evidence: list[CompanyEvidenceItem] = Field(
        min_length=1,
        max_length=6,
        description="회사 조직문화를 뒷받침하는 1~6개의 핵심 근거 항목 목록"
    )
