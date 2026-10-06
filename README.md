# Culture Fit Agent

## 회사 데이터 추가

새 회사를 추가할 때는 회사 ID를 폴더명과 파일명에 동일하게 사용합니다.

1. `data/sources/<company_id>/` 폴더를 만들고 원본 `.txt` 문서를 넣습니다.
2. 프로필을 생성합니다.

   ```powershell
   uv run python scripts/build_company_profiles.py <company_id>
   ```

   회사 ID를 생략하면 `data/sources` 아래의 모든 회사를 처리합니다.
3. 생성된 `data/companies/<company_id>.json`의 6개 trait 점수와 필수 필드를 확인합니다.
4. `data/applications_pdf/`에 테스트할 지원자 PDF를 넣고 Streamlit을 다시 실행합니다.

회사 선택 목록은 `data/companies/*.json`에서 자동으로 만들어집니다. 원본 문서를 추가하거나 수정하면 RAG 벡터 저장소도 다음 조회 때 자동으로 다시 만들어집니다.

## 실행

```powershell
uv run streamlit run streamlit_app.py
```

## 병렬 슈퍼에이전트 분석 구조

분석 그래프는 PDF 텍스트를 먼저 추출한 다음 회사 분석과 지원자 분석을 동시에 실행합니다.

```text
validate_input
  -> load_company
  -> extract_pdf
       ├─ company_subagent
       └─ candidate_subagent
            ↓ (두 결과가 모두 끝날 때까지 대기)
       join_subagents
  -> calculate_fit
  -> generate_report
  -> save_result
```

`company_subagent`는 회사 프로필 조회 툴과 회사 원본 문서 RAG 검색 툴을 사용합니다. `candidate_subagent`는 PDF 재추출 툴, 지원서 근거 검색 툴, 인용 검증 툴을 사용해 `CandidateCultureProfile`을 만듭니다. 두 에이전트는 `src/deep_agents.py`에 정의되어 있고, LangGraph의 상위 그래프가 슈퍼바이저 역할을 합니다.

새 PDF를 `data/applications_pdf/`에 넣으면 Streamlit이 다음 실행 시 목록에 표시하고, `extract_pdf` 노드가 전체 페이지의 텍스트를 추출합니다. 텍스트가 없는 스캔 PDF는 현재 OCR 대상이 아니므로 분석 전에 오류로 안내됩니다.
