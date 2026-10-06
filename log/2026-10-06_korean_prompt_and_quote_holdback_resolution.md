# 영문 출력 문제 및 인용문 보류(Missing) 원인 분석 및 해결 보고서

## 1. 개요
- **일자**: 2026-10-06
- **문제 제기**:
  1. "점수 판단 이유와 추천 면접 질문이 왜 영어로 반환될까요?"
  2. "지원자 원문 근거가 '확인 가능한 원문 근거가 없습니다'로 나오고, 점수 판단 이유가 'LLM이 제시한 근거 문장을 입력 원문에서 확인할 수 없어 점수를 보류했습니다'로 뜨는데, 이 보류 문제를 해결해야 해요."

---

## 2. 문제 원인 정밀 분석

### 2.1 영문 출력의 원인
- **원인**: `src/agents/deep_agents.py`의 `candidate_subagent` 및 `company_subagent`의 시스템 프롬프트(`system_prompt`)와 사용자 프롬프트(`prompt`)가 **100% 영어**로 작성되어 있었습니다.
  ```python
  # 기존 코드 (deep_agents.py)
  system_prompt = "You are the applicant-culture subagent. Analyze only the supplied..."
  prompt = "Analyze this applicant. The supervisor already extracted..."
  ```
- **결과**: `gpt-4o-mini` 모델은 시스템 프롬프트의 언어를 기본 응답 언어로 인식하므로, `reasoning`(점수 판단 이유), `follow_up_question`(추천 면접 질문), `summary`(종합 요약)를 모두 **영어**로 생성했습니다.

### 2.2 인용문 '보류(missing)' 발생 원인
- **원인 1: 단일 문장(Single Sentence) 분할의 한계**:
  - 기존 `find_best_matching_quote`는 원문을 정규표현식으로 1개 문장씩만 쪼개어 유사도를 비교했습니다.
  - 하지만 지원서 이력서는 줄바꿈(`\n`)이나 불릿 기호(`-`, `*`)로 잘게 나뉘어 있습니다.
    - 예: `- 담당: 마케팅 총괄` / `- 성과: 매출 20% 신장`
  - 모델이 이 두 줄을 엮어 `"마케팅 총괄하며 매출 20% 신장"`으로 인용하면, 단일 문장과의 일치율은 50% 안팎으로 떨어져 기준치(65%)를 넘지 못했습니다.
- **원인 2: 영문 번역 인용 위험**:
  - 모델이 영어 프롬프트의 영향을 받아 지원서 원문 문장을 영어로 번역하거나 영문으로 의역하여 인용할 경우, 한국어 자소서 원문과의 일치율이 0%가 되어 즉시 보류(`missing`) 처리되었습니다.

---

## 3. 해결 방안 및 아키텍처 개선

### 3.1 완전한 한국어 프롬프트 및 언어 규칙 강제 (`deep_agents.py`)
- 모든 시스템 프롬프트와 사용자 프롬프트를 **정중하고 명확한 한국어**로 전면 전환.
- **언어 규칙 명시**: `summary`, `reasoning`, `follow_up_question` 등 모든 서술형 텍스트는 100% 자연스러운 한국어로만 작성하도록 강제.
- **한국어 원문 인용 규칙**: `evidence_quote`는 지원서에 적힌 한국어 구절을 그대로 발췌하고 절대로 영어로 번역하지 않도록 명시.
- **상황 답변(scenario answers) 적극 활용**: 지원서에 직접 언급이 적은 문화축(예: `growth_ambition`)도 5개 상황 답변의 행동 양식을 종합 분석하여 근거를 누락 없이 포착하도록 지시.

### 3.2 3단계 다차원 유연 인용구 매칭 알고리즘 (`candidate_analyzer.py`)
```
[LLM 추출 인용구]
       │
       ▼
[1단계] 완전 일치 검사 (Exact Match) ──> 일치 시 즉시 1.0 통과!
       │
       ▼
[2단계] 단일 문장 바이그램 매칭 (Single Sentence Overlap) ──> 65% 이상 통과!
       │
       ▼
[3단계] 슬라이딩 2문장 윈도우 매칭 (Adjacent Window) ──> 인접 불릿/복합 구절 65% 이상 통과!
       │
       ▼
[4단계] 문서 전체 바이그램 포함율 검사 (Document-level Overlap) ──> 핵심 어휘 65% 이상 통과!
       │
       ▼
(위 모든 단계 실패 시에만 명백한 허위 날조로 판정하고 보류 처리)
```

---

## 4. 변경된 파일 및 코드
1. **`src/agents/deep_agents.py`**:
   - `get_company_subagent`, `get_candidate_subagent`, `run_company_subagent`, `run_candidate_subagent` 전면 한국어화 및 언어 규칙 추가.
2. **`src/agents/candidate_analyzer.py`**:
   - `find_best_matching_quote`: 2문장 슬라이딩 윈도우 및 전체 문서 바이그램 매칭 추가.
3. **`tests/test_candidate_analyzer.py`**:
   - `test_multi_clause_bullet_quote_is_accepted`: 여러 줄 불릿 항목 인용 통과 단위 테스트 추가.

---

## 5. 검증 결과
- 단위 테스트 36개 전체 통과 (`Ran 36 tests in 0.913s - OK`).
- 불릿 항목 기반 복합 인용문 테스트 정상 통과 확인.
