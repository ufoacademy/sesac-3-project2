import json
from pathlib import Path

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 🧭 Culture-Fit 분석 파이프라인 종합 검증 및 해설 노트북\n",
                "\n",
                "이 노트북은 **조직문화 적합도(Culture-Fit) 분석 에이전트 시스템**의 모든 계층을 단계별로 실행하고,\n",
                "각 코드가 **어디에 존재하고, 왜 존재하며, 어떤 입력(Input)을 받아 어떤 출력(Output)을 반환하는지**\n",
                "실제 데이터로 직접 검증할 수 있도록 작성된 실행 설명서입니다.\n",
                "\n",
                "---\n",
                "### 📋 테스트 목차\n",
                "1. **환경 설정**: 프로젝트 루트 경로 및 `.env` 환경 변수 등록\n",
                "2. **스키마 복원력 검증 (`src/agent_schemas.py`)**: 장애가 발생했던 LangSmith 실제 페이로드 자가 치유(Self-healing) 검증\n",
                "3. **데이터 I/O 서비스 검증 (`src/services/`)**: PDF 텍스트 추출 및 RAG 벡터 검색 검증\n",
                "4. **회사 분석 서브에이전트 검증 (`src/agents/deep_agents.py`)**: `company_subagent` 도구 호출 및 구조화 출력 검증\n",
                "5. **지원자 분석 서브에이전트 검증 (`src/agents/deep_agents.py`)**: `candidate_subagent` 인용 검증 및 성향 추출 검증\n",
                "6. **적합도 점수 계산 엔진 검증 (`src/agents/scoring.py`)**: 6대 문화축 핏 및 종합 점수 알고리즘 검증\n",
                "7. **최상위 LangGraph 슈퍼바이저 E2E 검증 (`src/app.py`)**: `graph.stream()`을 통한 노드별 실시간 상태 변화 및 최종 리포트 출력"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. 환경 설정 및 프로젝트 루트 등록\n",
                "\n",
                "- **코드 위치**: 노트북 시작 셀\n",
                "- **존재 이유**: 노트북이 `test/notebooks/` 하위 폴더에 위치하므로, 상위 2단계 부모 디렉터리(`sesac-3-project2`)를 `sys.path`에 추가해야 `from src...` 절대 임포트가 작동합니다.\n",
                "- **Input**: 현재 작업 디렉터리(`Path.cwd()`)\n",
                "- **Output**: 프로젝트 루트 경로 등록 및 OpenAI API Key 로드 완료"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import sys\n",
                "from pathlib import Path\n",
                "from dotenv import load_dotenv\n",
                "\n",
                "# 프로젝트 루트를 탐색하여 sys.path의 맨 앞에 추가\n",
                "current_dir = Path.cwd()\n",
                "project_root = current_dir.parents[1] if current_dir.name == \"notebooks\" else (\n",
                "    current_dir.parent if current_dir.name == \"test\" else current_dir\n",
                ")\n",
                "\n",
                "if str(project_root) not in sys.path:\n",
                "    sys.path.insert(0, str(project_root))\n",
                "\n",
                "# .env 환경 변수 로드\n",
                "load_dotenv(project_root / \".env\")\n",
                "\n",
                "api_key = os.getenv(\"OPENAI_API_KEY\")\n",
                "print(f\"✅ [1. 환경 설정 완료]\")\n",
                "print(f\"   - 프로젝트 루트: {project_root}\")\n",
                "print(f\"   - OPENAI_API_KEY 설정 여부: {'성공 (설정됨)' if api_key else '❌ 미설정 (.env 확인 필요)'}\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. 스키마 복원력 검증 (장애 재현 및 자가 치유)\n",
                "\n",
                "- **코드 위치**: `src/agent_schemas.py`\n",
                "- **존재 이유**:\n",
                "  - LLM(`gpt-4o-mini`)은 출처 정보를 단순 문자열이 아니라 `{'title': 'Official Values Document', 'type': 'local'}`처럼 객체 형태로 반환할 때가 있습니다.\n",
                "  - 기존 Pydantic 코드는 `source: str`로 고정되어 있어 `ValidationError`로 전체 서버가 죽었습니다.\n",
                "  - 새로 추가된 `@field_validator('source', mode='before')`가 이를 자동 감지하고 `title` 문자열로 변환하는지 실측합니다.\n",
                "- **Input**: 실제 LangSmith 장애 로그에서 수집된 원본 딕셔너리(`raw_trace_payload`)\n",
                "- **Output**: `CompanyEvidenceResult` 객체 (모든 `source`가 순수 문자열로 자동 변환됨)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.agent_schemas import CompanyEvidenceResult\n",
                "\n",
                "# 사용자가 실제 겪었던 LangSmith 장애 원본 페이로드\n",
                "raw_trace_payload = {\n",
                "    \"summary\": \"Baemin fosters an innovative culture that emphasizes autonomy, flexibility, and rapid execution.\",\n",
                "    \"evidence\": [\n",
                "        {\n",
                "            \"source\": {\"title\": \"Official Values Document\", \"type\": \"local\"},  # 딕셔너리 입력!\n",
                "            \"text\": \"우아한형제들은 공식적으로 '송파구에서 일 잘하는 방법'이라는 문서를 통해 업무 원칙을 공유한다.\",\n",
                "            \"relevance\": \"자율성과 수평적 소통을 강조하는 업무 방식을 설명함.\",\n",
                "            \"source_type\": \"local\",\n",
                "            \"url\": None,\n",
                "        },\n",
                "        {\n",
                "            \"source\": {\"title\": \"Job Posting Excerpt\", \"type\": \"local\"},       # 딕셔너리 입력!\n",
                "            \"text\": \"채용공고 우대사항에는 '모호한 문제를 정의하고 빠르게 실행해본 경험'이 포함된다.\",\n",
                "            \"relevance\": \"빠른 실행과 위험 감수 역량을 요구함.\",\n",
                "            \"source_type\": \"local\",\n",
                "            \"url\": None,\n",
                "        },\n",
                "        {\n",
                "            \"source\": \"02_news_summary.txt\",                                    # 일반 문자열 입력!\n",
                "            \"text\": \"언론 보도에서는 우아한형제들의 유쾌하고 자유로운 마케팅 사례가 자주 소개된다.\",\n",
                "            \"relevance\": \"자유로운 기업문화를 나타냄.\",\n",
                "            \"source_type\": \"local\",\n",
                "            \"url\": None,\n",
                "        }\n",
                "    ]\n",
                "}\n",
                "\n",
                "# Pydantic v2 파싱 실행\n",
                "parsed_result = CompanyEvidenceResult.model_validate(raw_trace_payload)\n",
                "\n",
                "print(\"✅ [2. 스키마 복원력 검증 성공]\")\n",
                "print(f\"   - 요약: {parsed_result.summary}\")\n",
                "for idx, item in enumerate(parsed_result.evidence, 1):\n",
                "    print(f\"   [{idx}] source: '{item.source}' (타입: {type(item.source).__name__}) | source_type: '{item.source_type}'\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. 데이터 I/O 서비스 계층 검증\n",
                "\n",
                "- **코드 위치**:\n",
                "  - `src/services/pdf_loader.py` (`extract_pdf_text`)\n",
                "  - `src/services/company_registry.py` (`list_company_ids`, `company_profile_path`)\n",
                "  - `src/services/rag.py` (`retrieve`)\n",
                "- **존재 이유**:\n",
                "  - 지원자 이력서(PDF)와 기업 원본 문서(TXT)는 비구조화 데이터이므로, 에이전트가 읽을 수 있도록 텍스트 추출 및 임베딩 벡터 검색을 수행해야 합니다.\n",
                "- **Input**:\n",
                "  - PDF 경로: `data/applications_pdf/01_김철수.pdf`\n",
                "  - RAG 질의어: `\"의사결정 방식 및 실행 속도\"` (회사 ID: `\"baemin\"`)\n",
                "- **Output**:\n",
                "  - PDF 추출 원문 문자열 (`str`)\n",
                "  - RAG 검색된 상위 3개 문서 조각 (`list[Document]`)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.services.pdf_loader import extract_pdf_text\n",
                "from src.services.company_registry import list_company_ids, company_profile_path\n",
                "from src.services.company_loader import load_company_profile\n",
                "from src.services.rag import retrieve\n",
                "\n",
                "# 1. 등록된 회사 목록 및 배민 프로필 검증\n",
                "companies = list_company_ids()\n",
                "baemin_profile = load_company_profile(company_profile_path(\"baemin\"))\n",
                "\n",
                "# 2. 지원자 PDF 텍스트 추출\n",
                "pdf_path = project_root / \"data\" / \"applications_pdf\" / \"01_김철수.pdf\"\n",
                "extracted_pdf_text = extract_pdf_text(pdf_path)\n",
                "\n",
                "# 3. 배민 관련 RAG 검색\n",
                "retrieved_docs = retrieve(\"의사결정 및 실행 속도\", company_id=\"baemin\", k=2)\n",
                "\n",
                "print(\"✅ [3. 데이터 서비스 검증 완료]\")\n",
                "print(f\"   - 등록 회사 목록: {companies}\")\n",
                "print(f\"   - 배민 핵심가치: {baemin_profile.core_values}\")\n",
                "print(f\"   - PDF 추출 텍스트 길이: {len(extracted_pdf_text)} 글자 (미리보기: '{extracted_pdf_text[:50]}...')\")\n",
                "print(f\"   - RAG 검색 결과 수: {len(retrieved_docs)}개 문서\")\n",
                "for doc in retrieved_docs:\n",
                "    print(f\"     • 출처: {doc.metadata.get('source')} | 미리보기: {doc.page_content[:40]}...\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. 회사 분석 서브에이전트 단독 검증\n",
                "\n",
                "- **코드 위치**: `src/agents/deep_agents.py` (`run_company_subagent`)\n",
                "- **존재 이유**:\n",
                "  - 회사명(`baemin`)만 전달받아 스스로 `inspect_company_profile`과 `search_company_documents` 툴을 호출하여 6대 문화축에 필요한 기업 측 증거를 수집합니다.\n",
                "- **Input**: `company_id = \"baemin\"`\n",
                "- **Output**: `CompanyEvidenceResult` (요약문 + 1~6개의 출처 근거 목록)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.agents.deep_agents import run_company_subagent\n",
                "\n",
                "print(\"⏳ [4. 회사 서브에이전트 실행 중...] (OpenAI LLM + Tool Calling 호출)\")\n",
                "company_result = run_company_subagent(\"baemin\")\n",
                "\n",
                "print(\"✅ [4. 회사 서브에이전트 실행 성공]\")\n",
                "print(f\"   - 종합 요약: {company_result.summary}\")\n",
                "print(f\"   - 수집된 근거 개수: {len(company_result.evidence)}개\")\n",
                "for idx, ev in enumerate(company_result.evidence, 1):\n",
                "    print(f\"     [{idx}] 출처: {ev.source} ({ev.source_type})\")\n",
                "    print(f\"         발췌: {ev.text[:60]}...\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 5. 지원자 분석 서브에이전트 단독 검증\n",
                "\n",
                "- **코드 위치**: `src/agents/deep_agents.py` (`run_candidate_subagent`)\n",
                "- **존재 이유**:\n",
                "  - 이력서 본문과 문제해결 5문항 답변을 읽고, 지원자의 6대 성향 점수(1~5점)와 **이력서 내 실제 인용구(`evidence_quote`)**를 추출합니다.\n",
                "  - `verify_application_quote` 도구를 스스로 호출하여 인용구가 조작되지 않았는지 자가 검증합니다.\n",
                "- **Input**:\n",
                "  - `application_path`: PDF 절대 경로\n",
                "  - `application_text`: 추출된 텍스트\n",
                "  - `answers`: 5문항 답변 딕셔너리 (`q1` ~ `q5`)\n",
                "- **Output**: `CandidateCultureProfile` (6개 차원별 점수, 신뢰도, 인용구, 판단 이유)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.agents.deep_agents import run_candidate_subagent\n",
                "\n",
                "# 5개 문항에 대한 구체적 테스트 답변 데이터\n",
                "test_answers = {\n",
                "    \"q1\": \"완벽한 정보를 기다리기보다는 MVP 최소 기능을 빠르게 출시하여 실제 사용자의 데이터 피드백을 수집한 후 반복 개선하겠습니다.\",\n",
                "    \"q2\": \"고객 피해나 서비스 장애를 막기 위한 조치는 현장에서 즉시 직접 판단하여 조치하고, 조치 경과와 배경을 상사에게 사후 보고하겠습니다.\",\n",
                "    \"q3\": \"피드백에 방어적으로 대하지 않고, 지적된 병목과 데이터 근거를 먼저 확인한 뒤 개선안 2가지를 빠르게 제안하겠습니다.\",\n",
                "    \"q4\": \"동료의 병목 업무를 파악해 제가 지원 가능한 부분을 적극 분담하여 전체 배포 일정을 반드시 준수하겠습니다.\",\n",
                "    \"q5\": \"기존의 방식으로는 달성 불가능하므로 불필요한 절차를 생략하고 새로운 자동화 도구를 과감히 도입하여 목표를 초과 달성하겠습니다.\",\n",
                "}\n",
                "\n",
                "print(\"⏳ [5. 지원자 서브에이전트 실행 중...] (인용 검증 도구 호출 포함)\")\n",
                "candidate_profile = run_candidate_subagent(\n",
                "    application_path=str(pdf_path),\n",
                "    application_text=extracted_pdf_text,\n",
                "    answers=test_answers,\n",
                ")\n",
                "\n",
                "print(\"✅ [5. 지원자 서브에이전트 실행 성공]\")\n",
                "for dim in candidate_profile.dimensions:\n",
                "    print(f\"   • {dim.dimension_id:22s}: {dim.score}점 (신뢰도: {dim.confidence})\")\n",
                "    print(f\"     인용구: \\\"{dim.evidence_quote}\\\"\")\n",
                "    print(f\"     판단 이유: {dim.reasoning[:50]}...\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 6. 적합도 점수 계산 엔진 검증\n",
                "\n",
                "- **코드 위치**: `src/agents/scoring.py` (`calculate_fit`, `dimension_fit`)\n",
                "- **존재 이유**:\n",
                "  - LLM의 주관적 환각 없이, 회사의 기준 점수(1~5점)와 지원자의 분석 점수(1~5점) 간의 오차를 수학적으로 계산(100점 만점)합니다.\n",
                "  - 공식: `fit_score = 100 * (1 - |company_score - candidate_score| / 4)`\n",
                "- **Input**:\n",
                "  - `company_scores`: `dict[str, float]` (예: `{'pace_preference': 4.0, ...}`)\n",
                "  - `candidate_scores`: `dict[str, float | None]`\n",
                "- **Output**:\n",
                "  - `fit_result`: 6개 축별 적합도 백분율, 종합 적합도(`overall_fit`), 지표 커버리지(`coverage`)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.agents.scoring import calculate_fit\n",
                "\n",
                "company_scores = baemin_profile.traits.model_dump()\n",
                "candidate_scores = {\n",
                "    dim.dimension_id: dim.score\n",
                "    for dim in candidate_profile.dimensions\n",
                "}\n",
                "\n",
                "fit_calculation = calculate_fit(company_scores, candidate_scores)\n",
                "\n",
                "print(\"✅ [6. 적합도 채점 알고리즘 계산 완료]\")\n",
                "print(f\"   - 종합 적합도 (Overall Fit): {fit_calculation['overall_fit']:.1f}점\")\n",
                "print(f\"   - 평가 지표 커버리지: {fit_calculation['coverage'] * 100:.1f}%\")\n",
                "print(\"\\n   [세부 지표별 매칭]\")\n",
                "for dim_id, fit_detail in fit_calculation[\"dimensions\"].items():\n",
                "    comp = fit_detail['company_score']\n",
                "    cand = fit_detail['candidate_score']\n",
                "    score = fit_detail['fit_score']\n",
                "    print(f\"   • {dim_id:22s} | 회사: {comp}점 vs 지원자: {cand}점 => 적합도: {score}%\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 7. 최상위 LangGraph 슈퍼바이저 E2E 전체 파이프라인 검증\n",
                "\n",
                "- **코드 위치**: `src/app.py` (`graph = build_graph()`)\n",
                "- **존재 이유**:\n",
                "  - 지금까지 개별적으로 테스트한 모든 노드들(`validate_input`, `load_company`, `extract_pdf`, `company_subagent`, `candidate_subagent`, `join_subagents`, `calculate_fit`, `generate_report`, `save_result`)을 하나의 통합 상태 머신 그래프로 엮어 원자적으로 실행합니다.\n",
                "- **Input**: `State` 사전\n",
                "  - `selected_company`: `\"baemin\"`\n",
                "  - `application_path`: PDF 절대 경로\n",
                "  - `scenario_answers`: 5문항 답변\n",
                "  - `db_path`: `data/culture_fit.db`\n",
                "- **Output**: 노드별 실시간 실행 로그(`graph.stream()`) 및 최종 리포트(`final_report`)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from src.app import graph\n",
                "\n",
                "full_pipeline_input = {\n",
                "    \"selected_company\": \"baemin\",\n",
                "    \"application_path\": str(pdf_path),\n",
                "    \"scenario_answers\": test_answers,\n",
                "    \"db_path\": str(project_root / \"data\" / \"culture_fit.db\"),\n",
                "    \"retry_count\": 0,\n",
                "}\n",
                "\n",
                "print(\"🚀 [7. LangGraph 슈퍼바이저 전체 파이프라인 스트리밍 시작]\\n\")\n",
                "\n",
                "# stream_mode='updates'를 사용하여 각 노드가 완료될 때마다 실시간으로 관측\n",
                "final_state = {}\n",
                "for step in graph.stream(full_pipeline_input, stream_mode=\"updates\"):\n",
                "    for node_name, output_data in step.items():\n",
                "        print(f\"📍 [노드 완료]: {node_name}\")\n",
                "        final_state.update(output_data)\n",
                "\n",
                "print(\"\\n🎉 [LangGraph 파이프라인 전체 완료]\")\n",
                "report = final_state.get(\"final_report\", {})\n",
                "print(f\"   - 최종 종합 적합도: {report.get('overall_fit')}점\")\n",
                "print(f\"   - 회사 요약: {report.get('company_analysis_summary')}\")\n",
                "print(f\"   - 분석 ID: {final_state.get('analysis_id')} (SQLite DB 영속화 완료)\")"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (.venv)",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.14.2"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

target_path = Path("e:/sesac-3-project2/test/notebooks/test_pipeline_verification.ipynb")
target_path.parent.mkdir(parents=True, exist_ok=True)
target_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Successfully generated notebook at: {target_path}")
