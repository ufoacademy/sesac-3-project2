# CandidateCultureProfile 루트 summary 누락 장애 (1 validation error) 분석 및 수정 보고서

## 1. 개요
- **일자**: 2026-10-06
- **장애 위치**: `src/nodes.py:analyze_candidate_node` → `src/agents/deep_agents.py:run_candidate_subagent` → LangChain `_handle_model_output` → `_parse_with_schema`
- **에러**: `StructuredOutputValidationError: Failed to parse structured output for tool 'CandidateCultureProfile': Failed to parse data to CandidateCultureProfile: 1 validation error for CandidateCultureProfile summary Field required [type=missing]`
- **증상**: 13개 validation error 수정 직후, 이번에는 루트 레벨의 `summary` 키가 누락되어 다시 전체 그래프가 중단됨.

---

## 2. 왜 같은 종류의 에러가 계속 반복되는가? (근본 원인 분석)

### 2.1 모델 관점의 원인 (gpt-4o-mini의 특성)
- `gpt-4o-mini`는 복잡한 맥락(긴 자기소개서 + 5개 시나리오 답변)을 처리하고 6개 문화축의 세부 근거를 집중해서 작성하다 보면, **최상위(Root) 객체의 메타데이터 키(`summary`) 생성을 깜빡하고 누락(Field Dropping)**하는 현상이 자주 일어납니다.
- 이번에도 모델은 6개 문화축(`dimensions`)은 열심히 작성했으나, 최상위의 `summary`를 빼먹고 `{"dimensions": [...]}` 형태의 JSON만 반환했습니다.

### 2.2 코드 관점의 원인 (이전 수정의 사각지대)
- 이전 수정에서는 자식 객체인 **`CandidateDimension`**에 누락 필드 보정기(`fill_omitted_fields`)를 달아서 `status`, `follow_up_question`, `score` 등의 오류 13개를 완벽하게 해결했습니다.
- 그러나 부모 객체인 **`CandidateCultureProfile`**에는 사전 검증기(`mode="before"`)가 없었습니다.
- 따라서 Pydantic은 부모 객체에서 `summary`가 없다는 이유로 즉시 `Field required` 에러를 던지며 전체 파이프라인을 중단시킨 것입니다.

---

## 3. 해결 방안 (영구적 자가 치유 아키텍처)

더 이상 모델이 필드를 빼먹더라도 시스템이 죽지 않도록 **3중 자가 치유(Self-Healing) 로직**을 적용했습니다:

1. **`summary` 자동 합성 (Auto-Synthesize)**:
   - LLM이 `summary`를 빼먹거나 `overview`, `description` 등 다른 이름으로 보냈을 경우 자동 탐색.
   - 아예 존재하지 않는 경우, 분석된 6개 문화축의 관찰 상태를 집계하여 **"지원자 6대 업무문화축 분석 완료 (관찰된 근거: N개 축)"** 형태의 의미 있는 요약문을 파이썬 코드가 자동으로 즉시 생성하여 채워 넣음.
2. **`dimensions` 키 별칭 지원 (Alias Tolerant)**:
   - 모델이 `dimensions` 대신 `culture_dimensions`나 `traits`로 이름을 바꿔 출력하더라도 안전하게 매핑.
3. **6개 문화축 자동 보충 (Missing Dimensions Fallback)**:
   - 모델이 실수로 6개 중 1~2개 축을 누락하고 4~5개만 반환하더라도, 빠진 문화축을 자동으로 `status="missing"` 항목으로 보충하여 Pydantic의 `require_all_six_dimensions` 예외를 방지.
4. **시스템 프롬프트 명시 강화**:
   - `deep_agents.py`의 프롬프트 최상단에 루트 객체에 `'summary'`와 `'dimensions'`가 반드시 포함되어야 함을 못 박음.

---

## 4. 변경된 파일 및 코드

### 4.1 `src/schemas.py` - `CandidateCultureProfile.normalize_profile`
```python
@model_validator(mode="before")
@classmethod
def normalize_profile(cls, data: Any) -> Any:
    if not isinstance(data, dict):
        return data

    normalized = dict(data)

    # 1. dimensions 키 별칭 대응
    raw_dims = (
        normalized.get("dimensions")
        or normalized.get("culture_dimensions")
        or normalized.get("traits")
        or []
    )
    if not isinstance(raw_dims, list):
        raw_dims = []

    # 2. summary 필드 누락 시 자동 합성
    summary = (
        normalized.get("summary")
        or normalized.get("candidate_summary")
        or normalized.get("overview")
        or normalized.get("description")
    )
    if not summary:
        observed_count = sum(
            1 for d in raw_dims if isinstance(d, dict) and d.get("status") == "observed"
        )
        summary = (
            f"지원자 6대 업무문화축 분석 완료 (관찰된 근거: {observed_count}개 축)"
            if raw_dims
            else "지원자 업무 성향 및 문화 적합도 종합 분석 결과입니다."
        )
    normalized["summary"] = str(summary)

    # 3. 6개 축 중 누락된 축 자동 보충
    present_ids = {
        d.get("dimension_id")
        for d in raw_dims
        if isinstance(d, dict) and "dimension_id" in d
    }
    for dim_id in sorted(DIMENSION_IDS):
        if dim_id not in present_ids:
            raw_dims.append({
                "dimension_id": dim_id,
                "score": None,
                "confidence": 0.0,
                "evidence_quote": None,
                "evidence_source": "missing",
                "reasoning": "LLM 분석 결과에서 해당 문화축이 누락되어 정보 부족으로 자동 처리되었습니다.",
                "status": "missing",
                "follow_up_question": DEFAULT_FOLLOW_UP_QUESTIONS.get(
                    dim_id, "이 문화축과 관련된 구체적인 경험을 말씀해 주세요."
                ),
            })

    normalized["dimensions"] = raw_dims
    return normalized
```

### 4.2 `src/agents/deep_agents.py`
시스템 프롬프트에 `1. 'summary'`, `2. 'dimensions'` 형식 규칙 추가.

---

## 5. 검증 결과
- `tests/test_candidate_schema_coercion.py`에 회귀 테스트 추가:
  - `test_missing_summary_is_auto_generated`: `summary` 누락 시 자동 합성 검증
  - `test_missing_dimensions_are_auto_supplemented`: 4개 축만 반환 시 6개로 자동 보충 검증
  - `test_culture_dimensions_alias_key_is_supported`: 별칭 키 매핑 검증
- 전체 36개 단위 테스트 통과 (`Ran 36 tests in 0.980s - OK`).
- LangChain 내부 `_parse_with_schema`로 실제 실패 페이로드 파싱 성공 확인.
