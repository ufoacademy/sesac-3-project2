# 인용문 완전 일치(Exact Match) 취약점 분석 및 한국어 유연 유사도(Fuzzy Matching) 개선 보고서

## 1. 개요 (Overview)
- **일자**: 2026-10-06
- **문제 제기**: 사용자 피드백 ("근데 원문 그대로 하는데 별로에요 원문이 조금만 달라도 의도가 틀어지면 0점 아니에요?")
- **핵심 문제**: `candidate_analyzer.py`의 `mark_invalid_quotes_as_missing`에서 단순 문자열 완전 포함(`in`) 검사만을 고수하여, 조사·어미의 사소한 변형이나 축약 등 지원자의 정당한 의도와 역량이 포함된 내용임에도 불구하고 해당 문화축 점수를 `None`(0점/보류)으로 처리하는 **거짓 음성(False Negative / 과도한 탈락)** 취약점 발생.
- **해결 방안**: 한국어 음절 바이그램(Character Bi-gram) 기반 유연 유사도(Fuzzy Match) 및 원문 문장 자동 정렬(Auto-alignment) 알고리즘 도입.

---

## 2. 문제 원인 및 한계 분석 (Root Cause & Limitation)

### 2.1 기존 로직
```python
quote_is_valid = normalized_quote and normalized_quote in normalized_sources

if not quote_is_valid:
    dimension["score"] = None
    dimension["confidence"] = 0.0
    dimension["evidence_quote"] = None
    dimension["status"] = "missing"
```

### 2.2 실세계 발생 예시 및 문제점
- **지원자 실제 원문**:
  > "저는 스타트업에서 빠르게 MVP를 제작해 배포하고 사용자 피드백을 주 단위로 수집하여 서비스를 개선했습니다."
- **LLM이 추출한 인용구 (의도 100% 동일, 표현 축약)**:
  > "빠르게 MVP를 제작하여 배포하고 사용자 피드백을 주단위로 수집해 서비스 개선"
- **기존 로직의 동작**:
  - `normalized_quote in normalized_sources` -> `False` 판정
  - `score = None`, `confidence = 0.0`, `status = "missing"`
- **결과적인 부작용**:
  - 지원자는 분명히 빠른 실행(`pace_preference`)과 고객 중심 개선 역량을 보유하고 있으나, LLM의 경미한 자연어 요약 버릇 때문에 억울하게 **0점(보류) 탈락** 처리됨.

---

## 3. 개선 설계 (Improvement Architecture)

### 3.1 이원화 검증 알고리즘 (2-Step Resilient Verification)
1. **1단계: 완전 일치 검사 (Exact Match)**
   - 원문에 완전히 동일하게 포함된 경우 유사도 1.0으로 즉시 통과 (연산 비용 최소화).
2. **2단계: 유연 유사도 매칭 (Character Bi-gram Overlap)**
   - 한국어는 조사(`에`, `를`, `으로`)와 어미(`~하여`, `~해`)가 발달한 교착어이므로 단순 공백 분리 토큰 매칭보다 **연속 2글자(Character Bi-gram) 집합 교집합** 비율이 형태소 변형에 강건함.
   - 지원서 원문을 문장 단위(`re.split(r"(?<=[.?!])\s+|\n+", text)`)로 분할하여 가장 높은 바이그램 일치율을 가진 문장을 탐색.
   - 일치율(Overlap Ratio)이 임계치(0.65, 65%) 이상인 경우:
     - ✅ **점수 인정**: 해당 문화축 점수(`score`)와 관찰 상태(`observed`) 정상 유지.
     - 🔍 **원문 보정 (Auto-alignment)**: `evidence_quote`를 지원자가 실제로 작성한 원문 문장으로 자동 대체하여 평가 투명성 확보.
   - 일치율이 0.65 미만인 경우 (완전한 거짓 인용, 허위 날조):
     - ❌ **환각 차단**: `status = "missing"`, `score = None`으로 보류하여 환각 방어선 유지.

---

## 4. 변경된 코드 및 파일 (Code Changes)

1. **`src/agents/candidate_analyzer.py`**:
   - `_extract_char_bigrams(text)` 함수 추가.
   - `find_best_matching_quote(quote, source_text, threshold=0.65)` 함수 구현.
   - `mark_invalid_quotes_as_missing()`: 유사도 65% 이상 시 원문 구절 자동 정렬 및 점수 보존.
   - `validate_candidate_quotes()`: 임계치 검사로 유연성 적용.
2. **`src/agents/agent_tools.py`**:
   - `verify_application_quote` 도구에 `find_best_matching_quote` 연동.
3. **`tests/test_candidate_analyzer.py`**:
   - `test_fuzzy_quote_with_slight_rephrasing_is_accepted_and_aligned`: 변형 인용구 정상 통과 및 보정 검증.
   - `test_completely_hallucinated_quote_is_marked_as_missing`: 환각 인용구의 정확한 차단 검증.
   - `test_validate_candidate_quotes_allows_fuzzy_match`: 유연성 검증.
   - `test_validate_candidate_quotes_rejects_hallucination`: 환각 예외 발생 검증.

---

## 5. 검증 결과 (Verification Results)
- 총 28개 단위 테스트 일괄 통과 (`Ran 28 tests in 0.876s - OK`).
- 사소한 형태소 변형 인용문도 탈락 없이 정당하게 점수 반영됨을 확인.
