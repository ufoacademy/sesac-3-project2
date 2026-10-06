# OpenAIRateLimitError 429 (insufficient_quota / credit_balance_exhausted) 분석 보고서

## 1. 개요
- **일자**: 2026-10-06
- **장애 위치**: `src/nodes.py:analyze_candidate_node` → `src/agents/deep_agents.py:run_candidate_subagent` → `ChatOpenAI._generate`
- **에러**: `OpenAIRateLimitError: Error code: 429 - type 'insufficient_quota', code 'credit_balance_exhausted'`
- **메시지**: "You have no credits remaining. Add credits to continue using the API"

## 2. 원인 (쉽게)
- **코드 버그가 아닙니다.** OpenAI 계정(조직)의 **선불 크레딧 잔액이 0**이 되어 OpenAI 서버가 모든 요청을 거절했습니다.
- 같은 429 코드라도 두 종류가 있습니다.

| 종류 | `type` | 의미 | 기다리면 해결? |
| --- | --- | --- | --- |
| 속도 제한 | `rate_limit_exceeded` | 1분당 요청/토큰이 너무 많음 | O (재시도로 해결) |
| **크레딧 소진** | `insufficient_quota` | 돈(크레딧)이 없음 | **X (충전 필요)** |

- 이번은 두 번째입니다. 따라서 `max_retries=3`, 타임아웃 상향 등 코드 측 재시도로는 해결되지 않습니다.
- 오늘 디버깅·노트북 실행·Streamlit 테스트 반복으로 gpt-4o-mini 호출이 누적되어 잔액이 소진된 것으로 보입니다. (정확한 사용량은 OpenAI 대시보드 Usage 페이지에서 확인 필요)

## 3. 해결 방법 (사용자 조치)
1. https://platform.openai.com/settings/organization/billing/ 접속 → 크레딧 충전.
   - 또는 크레딧이 있는 다른 API 키로 `.env`의 `OPENAI_API_KEY` 교체.
2. 충전 직후에는 반영까지 수 분 걸릴 수 있음.
3. **Streamlit 앱 재시작** (`get_candidate_subagent`, `get_company_subagent`는 `lru_cache`로 클라이언트를 캐시하므로 키를 바꿨다면 재시작해야 새 키가 적용됨).
4. 같은 지원서로 다시 분석 실행.

## 4. 코드 수정 과정
1. 트레이스백의 `body.type == 'insufficient_quota'` 확인 → 계정 크레딧 문제로 판단.
2. `streamlit_app.py` 확인: 그래프 실행은 이미 `try/except`로 감싸져 있어 앱이 죽지는 않지만, 원시 트레이스백만 보여 원인 파악이 어려움.
3. `streamlit_app.py` 분석 실행 `except` 블록에 `insufficient_quota` 감지 시 충전 안내 `st.warning` 추가 (트레이스백은 그대로 함께 표시).
4. 파이썬 문법 검사(`py_compile`)와 전체 단위 테스트 실행으로 회귀 없음 확인.

## 5. 변경 파일
- `streamlit_app.py`: 크레딧 소진 시 안내 메시지 추가 (동작 변경 없음, 표시만 추가)

## 6. 알려진 한계 / 향후 개선
- 문자열(`"insufficient_quota" in str(error)`)로 감지하므로 OpenAI 에러 포맷이 바뀌면 안내가 안 뜰 수 있음 (트레이스백은 여전히 표시됨).
- 개발 중 비용 절감: 노트북/테스트에서는 실제 API 대신 Mock 모델 사용, LangSmith로 토큰 사용량 모니터링 권장 (`test/notebooks/token_optimization_experiment.ipynb` 참고).
