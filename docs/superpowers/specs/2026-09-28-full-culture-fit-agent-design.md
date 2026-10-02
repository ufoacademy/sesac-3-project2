# 조직문화 적합성 전체 에이전트 설계 명세

작성일: 2026-09-28  
실제 프로젝트: `C:\Users\BAE\Desktop\sesac\sesac-3 project2`  
목표: 비개발자 수강생이 VS Code에서 직접 실행하고 각 기술의 역할을 설명할 수 있는 실험용 MVP

## 1. 제품 정의

HR 담당자가 회사와 지원자 PDF를 선택하고, 지원자가 문제해결 상황 5문항에 답하면 회사와 지원자의 업무방식을 같은 6개 축으로 비교한다. 결과는 전체 적합도, 축별 적합도, 회사 근거, 지원자 근거, 추가 확인 질문으로 보여준다.

전문 인적성 검사를 만드는 것이 아니라 다음 기술 흐름이 실제로 작동하는지 검증한다.

```text
Streamlit 입력
→ LangGraph 실행
→ PDF 및 회사 데이터 로드
→ LLM 구조화 분석
→ Python 적합도 계산
→ 결과 검증
→ SQLite 저장
→ Streamlit 출력
→ LangSmith 실행 추적
```

## 2. 현재 프로젝트 자산

- 회사 프로필: 토스, 현대차, 배민 JSON 각 1개
- 회사 근거 문서: 회사별 공식 가치, 뉴스, 재직자 리뷰 요약, 채용공고 발췌
- 지원자 데이터: `data/applications_pdf` 안의 텍스트 추출 가능한 PDF 7개
- 실행 환경: Python 3.14, uv, LangChain, LangGraph, LangSmith, pypdf, Pydantic
- 기존 그래프: 회사 문화를 채팅으로 설명하는 단일 노드 그래프
- 환경변수: OpenAI와 LangSmith 키 이름이 `.env`에 준비됨

## 3. 사용자 화면

프로젝트 최상위의 `streamlit_app.py`를 실행 화면으로 사용한다. 기존 `src/app.py`는 `langgraph.json`이 참조하는 그래프 조립 파일이므로 이름과 위치를 유지한다.

화면은 다음 순서로 구성한다.

1. 회사 선택: 토스, 현대차, 배민
2. 지원자 PDF 선택: 폴더 안의 PDF를 자동 검색
3. 추출된 지원자 원문 확인
4. 문제해결 상황 5문항 답변
5. Culture-Fit 분석 버튼
6. 전체 적합도와 6개 축 결과
7. 회사·지원자 원문 근거와 면접 확인 질문
8. 과거 분석 결과 조회

## 4. 공통 6개 문화축

기존 회사 프로필과 호환되도록 아래 ID와 1~5점 방향을 유지한다.

| ID | 1점 | 5점 |
|---|---|---|
| `pace_preference` | 충분히 검토한 뒤 실행 | 빠르게 실행하고 수정 |
| `autonomy_preference` | 명확한 지시 선호 | 스스로 결정하고 책임 |
| `hierarchy_tolerance` | 수평적 합의 선호 | 공식 승인·절차 수용 |
| `risk_tolerance` | 안정성과 예측 가능성 선호 | 불확실한 도전 수용 |
| `collaboration_style` | 조화와 완곡한 소통 | 직접적 토론과 피드백 |
| `growth_ambition` | 안정적이고 지속 가능한 성장 | 높은 목표와 빠른 성장 |

점수의 높고 낮음은 좋고 나쁨이 아니라 서로 다른 업무방식이다.

## 5. 문제해결 상황 5문항

문항은 MVP에서 고정한다. 지원자는 각 문항에 3~6문장으로 선택한 행동과 이유를 작성한다.

1. **마감과 불완전한 정보:** 마감까지 시간이 부족하고 필요한 정보를 모두 확인할 수 없다. 무엇을 먼저 실행하고 무엇을 확인할 것인가?
   - 주요 축: `pace_preference`, `risk_tolerance`
2. **지침 부재:** 담당자가 자리를 비운 상태에서 지침에 없는 문제가 발생했다. 어디까지 직접 결정하고 언제 확인을 요청할 것인가?
   - 주요 축: `autonomy_preference`, `hierarchy_tolerance`
3. **강한 수정 의견:** 작업 결과에 예상보다 강한 수정 의견을 받았다. 무엇을 확인하고 어떻게 반영할 것인가?
   - 주요 축: `collaboration_style`, `hierarchy_tolerance`
4. **동료 업무 지연:** 동료의 업무가 늦어 전체 일정이 밀릴 가능성이 있다. 역할과 일정을 어떻게 조정할 것인가?
   - 주요 축: `collaboration_style`, `pace_preference`
5. **높은 목표와 부족한 자원:** 현재 인력과 시간으로 달성하기 어려운 목표를 맡았다. 목표·범위·실행 방식을 어떻게 결정할 것인가?
   - 주요 축: `growth_ambition`, `risk_tolerance`, `autonomy_preference`

자기소개서는 여섯 축 전반의 기존 경험 근거를 제공하고, 상황답변은 자기소개서에 나타나지 않은 행동방식을 보완한다.

## 6. LangGraph 실행 흐름

```text
START
→ validate_input
→ load_company
→ extract_pdf
→ retrieve_company_evidence
→ analyze_candidate
→ calculate_fit
→ generate_report
→ validate_result
→ save_result
→ END
```

| 노드 | 입력 | 출력 |
|---|---|---|
| `validate_input` | 회사 ID, PDF 경로, 5개 답변 | 실행 가능 상태 또는 오류 |
| `load_company` | 회사 ID | 회사 프로필 JSON |
| `extract_pdf` | PDF 경로 | 페이지별 텍스트와 전체 원문 |
| `retrieve_company_evidence` | 회사 ID와 6개 축 | 회사 문서의 근거 문단 |
| `analyze_candidate` | PDF 원문과 5개 답변 | 지원자 6개 축 점수·신뢰도·원문 인용 |
| `calculate_fit` | 회사·지원자 점수 | 축별 적합도와 전체 적합도 |
| `generate_report` | 점수와 근거 | 일치·차이 설명과 확인 질문 |
| `validate_result` | 입력 원문과 보고서 | 통과 또는 1회 재분석 |
| `save_result` | 검증된 결과 | SQLite 분석 ID |

재분석 후에도 구조나 인용 검증이 실패하면 결과를 저장하지 않고 오류 이유를 화면에 표시한다.

## 7. 구조화된 LLM 출력

Pydantic 모델로 각 지원자 축을 아래 형식으로 받는다.

```json
{
  "dimension_id": "autonomy_preference",
  "score": 4,
  "confidence": 0.85,
  "evidence_quote": "가능한 선택지를 정리해 먼저 진행했습니다.",
  "evidence_source": "application",
  "reasoning": "지침이 부족한 상황에서 스스로 판단한 사례가 나타남"
}
```

검증 규칙은 다음과 같다.

- 6개 축이 모두 존재한다.
- 점수는 1~5다.
- 신뢰도는 0~1이다.
- 인용문은 PDF 원문 또는 상황답변에 실제로 존재한다.
- 근거가 부족하면 `score=null`, `status=missing`으로 표시한다.
- 근거가 없는 축을 LLM이 추측하지 않는다.

## 8. 적합도 계산

LLM은 지원자 축 점수 후보만 만든다. 최종 적합도는 Python이 계산한다.

```text
축별 적합도 = 100 × (1 - |회사 점수 - 지원자 점수| ÷ 4)
전체 적합도 = 값이 있는 축별 적합도의 평균
정보 충족률 = 지원자 점수가 있는 축 수 ÷ 6
```

MVP에서는 여섯 축에 동일 가중치를 사용한다. 근거가 없는 축은 0점으로 처리하지 않고 전체 평균에서 제외하며 정보 충족률을 함께 표시한다.

## 9. SQLite 데이터 구조

DB 파일은 `data/culture_fit.db`를 사용한다.

| 테이블 | 주요 필드 |
|---|---|
| `applicants` | `applicant_id`, `source_file`, `source_hash`, `extracted_text` |
| `scenario_answers` | `applicant_id`, `question_id`, `answer_text` |
| `analysis_runs` | `analysis_id`, `company_id`, `applicant_id`, `overall_fit`, `coverage`, `created_at` |
| `dimension_results` | `analysis_id`, `dimension_id`, `company_score`, `candidate_score`, `fit_score`, `confidence`, `evidence_quote` |

같은 지원자를 여러 회사와 비교하거나 같은 회사에 다시 분석할 때 과거 결과를 덮어쓰지 않고 새 `analysis_id`를 만든다.

## 10. LangSmith 추적

그래프 한 번의 실행을 하나의 trace로 기록하고 각 노드를 child run으로 확인한다. 프로젝트명은 `culture-fit-agent`를 사용한다.

확인 항목은 노드 실행 순서, 프롬프트와 구조화 출력, 토큰 사용량, 지연 시간, 오류, 재분석 횟수다. API 키나 PDF 원문 전체를 태그와 메타데이터에 넣지 않는다.

## 11. 파일 변경 계획

```text
Create  streamlit_app.py
Create  src/pdf_loader.py
Create  src/scoring.py
Create  src/database.py
Create  tests/test_pdf_loader.py
Create  tests/test_scoring.py
Create  tests/test_database.py
Create  tests/test_graph.py
Modify  src/state.py
Modify  src/schemas.py
Modify  src/nodes.py
Modify  src/routers.py
Modify  src/app.py
Modify  pyproject.toml
Modify  README.md
```

기존 회사 JSON, 회사 근거 문서, 지원자 PDF 원본은 수정하지 않는다.

## 12. 오류 처리

- PDF가 없거나 선택되지 않음: 분석 시작 전 차단
- 암호화 또는 텍스트가 없는 PDF: 추출 실패 메시지 표시
- 5개 답변 중 누락: 누락 문항 표시 후 분석 시작 차단
- 회사 JSON 누락 또는 형식 오류: 회사 ID와 파일 경로를 포함한 오류 표시
- OpenAI 호출 실패: 저장하지 않고 다시 실행 안내
- Pydantic 형식 오류: 1회 자동 재분석
- 인용문이 원문에 없음: 1회 자동 재분석 후 실패 시 저장 중단
- SQLite 저장 실패: 분석 결과를 화면에 확정 표시하지 않고 오류 표시

## 13. 테스트 기준

- 실제 PDF 7개에서 글자 추출 성공
- 빈 PDF와 잘못된 파일 오류 처리
- 점수 차이 0, 1, 4의 적합도 계산 확인
- 누락 축이 평균에서 제외되고 정보 충족률이 낮아지는지 확인
- SQLite 저장 후 동일 결과 조회
- 가짜 LLM을 사용한 LangGraph 전체 경로 테스트
- 구조화 출력 실패 시 한 번만 재분석하는지 확인
- Streamlit 앱이 예시 입력으로 오류 없이 열리는지 확인

실제 OpenAI 호출 테스트는 비용과 결과 변동 때문에 자동 테스트와 분리하고 수동 통합 테스트 한 건으로 수행한다.

## 14. 구현 완료 기준

1. VS Code 터미널에서 의존성을 설치할 수 있다.
2. Streamlit에서 회사와 PDF를 선택할 수 있다.
3. 5개 상황답변을 입력하고 분석할 수 있다.
4. 6개 축 점수·전체 적합도·정보 충족률·근거를 볼 수 있다.
5. 분석 결과가 SQLite에 저장되고 다시 조회된다.
6. LangSmith에서 한 번의 전체 실행 trace를 확인할 수 있다.
7. 모든 자동 테스트가 통과한다.
8. README만 읽고 다른 컴퓨터에서 같은 과정을 재현할 수 있다.

## 15. MVP 이후 고도화

- 회사별 문항 자동 조정
- 직무별 축 가중치
- 여러 회사 동시 비교
- 면접관 평가와 실제 입사 후 결과 연결
- 회사 조직문화 설문 결과의 정기 갱신

위 기능은 현재 MVP 완료 후 추가한다.
