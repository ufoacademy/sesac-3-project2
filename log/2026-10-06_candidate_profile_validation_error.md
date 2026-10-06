# CandidateCultureProfile 구조화 출력 파싱 장애 (13 validation errors) 분석 및 수정 보고서

## 1. 개요
- **일자**: 2026-10-06
- **장애 위치**: `src/nodes.py:analyze_candidate_node` → `src/agents/deep_agents.py:run_candidate_subagent` → LangChain `create_agent` 내부 `_handle_model_output` → `_parse_with_schema`
- **에러**: `StructuredOutputValidationError: Failed to parse structured output for tool 'CandidateCultureProfile' ... 13 validation errors`
- **증상**: 지원자 분석 단계에서 그래프 전체가 중단됨 (반복 발생).

## 2. 에러 내용 해석 (쉽게)
LLM(gpt-4o-mini)이 돌려준 JSON이 우리가 정한 양식(`CandidateDimension`)과 달랐습니다.

| 에러 | 개수 | 의미 |
| --- | --- | --- |
| `dimensions.N.status Field required` | 6 | 6개 문화축 모두 `status`(observed/missing)를 빼먹음 |
| `dimensions.N.follow_up_question Field required` | 6 | 6개 문화축 모두 면접 후속 질문을 빼먹음 |
| `dimensions.4.score less_than_equal 5 (input 8)` | 1 | 협업 스타일에 **10점 척도**로 8점을 줌 |

합계 6 + 6 + 1 = **13개**.

## 3. 근본 원인 (Root Cause)
1. **비엄격(non-strict) 구조화 출력**
   - `create_agent(response_format=CandidateCultureProfile)` 는 LangChain 1.4.2에서 `ProviderStrategy`를 사용하며, `strict` 기본값이 `None`입니다.
   - 따라서 OpenAI는 JSON 스키마를 "참고"만 하고 **필수 필드 누락·범위 위반을 막아주지 않습니다.**
2. **프롬프트에 필드 규칙이 없었음**
   - 시스템 프롬프트는 "exact CandidateCultureProfile schema"라고만 했고, 어떤 키가 필수인지·점수 척도가 1~5인지 명시하지 않았습니다.
   - 스키마 필드에 `description`도 없어서 모델이 `status`, `follow_up_question`의 용도를 알기 어려웠습니다.
3. **스키마에 복구 장치가 없었음**
   - 앞서 `CompanyEvidenceItem`에는 `mode="before"` 보정기를 넣었지만, `CandidateDimension`에는 없어서 사소한 누락도 곧바로 전체 실패로 이어졌습니다.

## 4. 수정 과정 (시간 순)
1. 트레이스백에서 실패 지점이 `provider_strategy_binding.parse` 임을 확인 → Provider 방식(비엄격) 파싱임을 파악.
2. `.venv/Lib/site-packages/langchain/agents/structured_output.py` 확인: `ProviderStrategy(strict=None)` 기본값 → strict 미적용 확인.
3. `src/schemas.py` 확인: `status`, `follow_up_question` 기본값 없음, `score`는 `le=5`.
4. 수정 방향 결정: **(1) 프롬프트로 예방 + (2) 스키마에서 복구** 의 이중 방어.
   - strict=True 전환은 OpenAI strict 모드가 Optional/기본값 필드 처리에 제약이 있어 실호출 검증 없이 적용하면 다른 장애를 낳을 위험이 있어 이번에는 보류 (향후 과제).
5. `src/schemas.py`에 `CandidateDimension.fill_omitted_fields` (`model_validator(mode="before")`) 추가.
6. `src/agents/deep_agents.py` 시스템 프롬프트에 필수 키 목록·1~5 척도·status 규칙 명시.
7. 장애 페이로드를 그대로 재현한 회귀 테스트 `tests/test_candidate_schema_coercion.py` 작성.
8. 전체 테스트 실행 → 34개 통과.
9. LangChain의 실제 파서 `_parse_with_schema(CandidateCultureProfile, 'pydantic', payload)`로 직접 호출하여 통과 확인.

## 5. 보정 규칙 (`fill_omitted_fields`)
| 입력 상황 | 보정 결과 |
| --- | --- |
| `score` 5 초과 10 이하 (예: 8) | 10점 척도로 보고 절반 환산 → 4.0 |
| `score` 10 초과 또는 1 미만 | 1~5로 clamp |
| `score` 숫자가 아님 | None |
| `evidence_source` 누락/이상값 | 인용이 있으면 `application`, 없으면 `missing` |
| `status` 누락 | 점수+인용+출처가 있으면 `observed`, 아니면 `missing` |
| `status=observed`인데 점수나 인용이 없음 | `missing`으로 강등 (기존엔 예외로 중단) |
| `status=missing` | score/evidence_quote = None, evidence_source = `missing` |
| `follow_up_question` 누락 | 문화축별 기본 면접 질문 |
| `reasoning` 누락 | "LLM이 판단 이유를 제공하지 않았습니다." |
| `confidence` 누락/범위 밖 | 0~1 clamp (누락 시 observed 0.5 / missing 0.0) |
| `dimension_id` 잘못됨, 6개 미만 | **여전히 실패** (임의로 만들어내지 않음) |

## 6. Before / After
- **Before**: 위 페이로드 → `StructuredOutputValidationError` → 그래프 중단.
- **After**:
```
[('pace_preference', 4.0, 'observed'), ('autonomy_preference', 4.0, 'observed'),
 ('hierarchy_tolerance', 3.0, 'observed'), ('risk_tolerance', 3.0, 'observed'),
 ('collaboration_style', 4.0, 'observed'), ('growth_ambition', 4.0, 'observed')]
```

## 7. 변경 파일
- `src/schemas.py`: `DEFAULT_FOLLOW_UP_QUESTIONS`, `_normalize_candidate_score`, `CandidateDimension.fill_omitted_fields`, 필드 `description` 추가
- `src/agents/deep_agents.py`: 지원자 서브에이전트 프롬프트에 형식 규칙 추가
- `tests/test_candidate_schema_coercion.py`: 회귀 테스트 6건

## 8. 알려진 한계
- 8점 → 4점 환산은 "모델이 10점 척도를 썼다"는 가정입니다. 모델이 1~5 척도에서 실수로 6을 쓴 경우엔 3점으로 낮게 보정될 수 있습니다. 프롬프트에서 1~5를 명시했으므로 발생 빈도는 낮다고 판단했습니다.
- 기본 `follow_up_question`은 일반 질문이라 지원자 맞춤형이 아닙니다.
- 실제 OpenAI 호출(E2E)은 이 수정 과정에서 수행하지 않았습니다. Streamlit에서 동일 지원서로 재실행하여 확인이 필요합니다.

## 9. 향후 개선
- `ProviderStrategy(CandidateCultureProfile, strict=True)` 전환 검토 (OpenAI strict 스키마 제약 확인 후).
- 보정이 일어난 필드를 로그/LangSmith 메타데이터로 남겨 모델 품질 모니터링.
