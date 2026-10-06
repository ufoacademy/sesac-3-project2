# 장애 분석 및 해결 보고서 (Incident Post-Mortem)

- **일시**: 2026-10-06 14:07 KST
- **발생 위치**: Streamlit "Culture-Fit 분석 시작" 버튼 클릭 시 (`streamlit_app.py` line 576 -> `nodes.py` line 179 -> `deep_agents.py` line 82)
- **에러 명칭**: `StructuredOutputValidationError` / `pydantic_core.ValidationError`
- **해결 상태**: 해결 완료 (Pydantic v2 사전 검증기 추가 및 시스템 프롬프트 제약 명시, 단위 테스트 검증 완료)

---

## 1. 장애 증상 및 원본 에러 로그

Streamlit UI에서 "Culture-Fit 분석 시작" 버튼을 눌렀을 때, `company_subagent` 실행 중 다음과 같은 에러가 발생하며 파이프라인이 중단되었습니다:

```text
StructuredOutputValidationError: Failed to parse structured output for tool 'CompanyEvidenceResult': 
Failed to parse data to CompanyEvidenceResult: 6 validation errors for CompanyEvidenceResult
evidence.0.source
  Input should be a valid string [type=string_type, input_value={'title': 'Official Values Document', 'type': 'local'}, input_type=dict]
evidence.1.source
  Input should be a valid string [type=string_type, input_value={'title': 'Job Posting Excerpt', 'type': 'local'}, input_type=dict]
evidence.2.source
  Input should be a valid string [type=string_type, input_value={'title': 'Employee Review Summary', 'type': 'local'}, input_type=dict]
evidence.3.source
  Input should be a valid string [type=string_type, input_value={'title': 'News Summary', 'type': 'local'}, input_type=dict]
evidence.4.source
  Input should be a valid string [type=string_type, input_value={'title': 'Job Posting Excerpt', 'type': 'local'}, input_type=dict]
evidence.5.source
  Input should be a valid string [type=string_type, input_value={'title': 'Employee Review Summary', 'type': 'local'}, input_type=dict]
```

---

## 2. 정확한 발생 위치 및 원인 분석 (Root Cause Analysis)

### 2.1. 발생 코드 위치
1. **호출 체인**:
   - `streamlit_app.py` (line 576): `graph.invoke({...})`
   - `src/nodes.py` (line 179): `analyze_company_node` -> `run_company_subagent(state["selected_company"])`
   - `src/agents/deep_agents.py` (line 82): `get_company_subagent().invoke(...)`
   - `langchain/agents/structured_output.py` (line 99): `adapter.validate_python(data)`
2. **원인 모듈**:
   - `src/agent_schemas.py`의 `CompanyEvidenceItem.source` 필드 타입 정의 (`source: str`)

### 2.2. 왜 이 에러가 발생했는가?
1. **LLM 모델(`gpt-4o-mini`)의 비정형 객체 반환**:
   - `get_company_subagent()`는 회사 문서를 RAG 검색한 뒤 `CompanyEvidenceResult` 구조화 출력을 생성합니다.
   - 이때 OpenAI 모델은 출처(`source`)를 단순 문자열(`"Official Values Document"`) 대신 제목과 유형이 묶인 딕셔너리(`{'title': 'Official Values Document', 'type': 'local'}`) 객체로 구조화하여 반환했습니다.
2. **Pydantic v2의 엄격한 타입 검증 (Strict Typing)**:
   - `src/agent_schemas.py`의 기존 정의는 `source: str`로만 선언되어 있었고, Pydantic은 입력값이 `dict` 타입이므로 파싱 단계에서 즉시 `pydantic_core.ValidationError`를 발생시켰습니다.
3. **스키마 및 프롬프트 제약 부족**:
   - Pydantic 스키마에 `Field(description=...)`이 없었고, `system_prompt`에도 `source`가 문자열이어야 한다는 명시적 서술이 없어서 LLM이 자체 판단으로 dict 객체를 생성했습니다.

---

## 3. 해결 방안 및 설계 의도 (Why & What For)

### 3.1. 2중 방어(Defense-in-Depth) 전략 채택
단순히 프롬프트만 수정하거나, 단순히 스키마만 수정해서는 LLM의 비결정론적 특성을 완전히 방어할 수 없습니다. 따라서 **"프롬프트 가이드"와 "런타임 Pydantic 자동 변환(Coercion)"을 동시에 적용**했습니다.

1. **Pydantic `@field_validator(mode="before")` 사전 변환기 적용**:
   - LLM이 설령 `{'title': '...', 'type': '...'}`과 같은 딕셔너리를 반환하더라도, 파싱 에러를 던지지 않고 자동으로 내부의 `title`, `name`, `source` 키값을 추출하여 단일 문자열로 변환합니다.
   - `text` 필드가 dict/list로 넘어올 경우 `json.dumps`로 안전 변환.
   - `source_type` 필드 또한 방어적으로 `'local'` / `'web'` 검증 처리.
2. **시스템 프롬프트 명시 (`deep_agents.py`)**:
   - 시스템 프롬프트에 `CRITICAL FORMAT RULE`을 추가하여 애초에 LLM이 dict 형태를 만들지 않고 문자열 문서명만 전달하도록 지시.

---

## 4. 코드 변경 내역 (수정 전 vs 수정 후)

### 4.1. `src/agent_schemas.py`

#### [수정 전 코드]
```python
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
```

#### [수정 후 코드]
```python
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
```

---

### 4.2. `src/agents/deep_agents.py`

#### [수정 전 코드]
```python
        system_prompt=(
            "You are the company-culture research subagent. "
            "Use inspect_company_profile and search_company_documents before "
            "writing your answer. Search at least three focused queries covering "
            "work style, decision making, risk, collaboration, and growth. "
            "Only include evidence returned by the tools. Return the requested "
            "CompanyEvidenceResult with concise grounded excerpts."
        ),
```

#### [수정 후 코드]
```python
        system_prompt=(
            "You are the company-culture research subagent. "
            "Use inspect_company_profile and search_company_documents before "
            "writing your answer. Search at least three focused queries covering "
            "work style, decision making, risk, collaboration, and growth. "
            "Only include evidence returned by the tools. Return the requested "
            "CompanyEvidenceResult with concise grounded excerpts. "
            "CRITICAL FORMAT RULE: For each evidence item, 'source' must be a single string "
            "(e.g. document name or title), NEVER a dictionary or object."
        ),
```

---

## 5. 검증 결과 (Verification)

1. **신규 단위 테스트(`tests/test_agent_schemas.py`) 생성**:
   - `test_evidence_item_coerces_dict_source_to_string`: `source: {'title': '...', 'type': 'local'}` 입력 시 `"Official Values Document"`로 정상 변환 검증.
   - `test_evidence_result_validates_with_dict_sources`: 실제 장애 발생 페이로드 검증.
2. **전체 테스트 스위트 실행 결과**:
   ```powershell
   .venv\Scripts\python -m unittest discover tests
   ```
   - 총 25개 테스트 전체 통과 (`Ran 25 tests in 1.168s - OK`).
