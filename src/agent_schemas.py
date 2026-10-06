from typing import Literal

from pydantic import BaseModel, Field


class CompanyEvidenceItem(BaseModel):
    source: str
    text: str
    relevance: str = ""
    source_type: Literal["local", "web"] = "local"
    url: str | None = None


class CompanyEvidenceResult(BaseModel):
    summary: str
    evidence: list[CompanyEvidenceItem] = Field(
        min_length=1,
        max_length=6,
    )
