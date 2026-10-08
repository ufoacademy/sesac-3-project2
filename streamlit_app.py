import hashlib
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.app import graph
from src.services.company_registry import get_company_labels
from src.services.database import list_analyses
from src.services.pdf_loader import extract_pdf_text


PROJECT_ROOT = Path(__file__).resolve().parent

PDF_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "applications_pdf"
)

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "culture_fit.db"
)

UPLOAD_DIRECTORY = Path(tempfile.gettempdir()) / "culture_fit_uploads"


def persist_uploaded_pdf(uploaded_file) -> Path:
    """Persist an uploaded PDF for the current Streamlit process."""

    content = uploaded_file.getvalue()
    digest = hashlib.sha256(content).hexdigest()[:16]
    safe_name = Path(uploaded_file.name).name
    path = UPLOAD_DIRECTORY / f"{digest}_{safe_name}"
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_bytes(content)

    return path


COMPANY_LABELS = get_company_labels()

DIMENSION_LABELS = {
    "pace_preference": "실행 속도",
    "autonomy_preference": "자율성",
    "hierarchy_tolerance": "위계·절차 수용",
    "risk_tolerance": "위험 감수",
    "collaboration_style": "협업·피드백",
    "growth_ambition": "성장·성과 지향",
}


QUESTIONS = {
    "q1": (
        "마감까지 시간이 부족하고 필요한 정보를 모두 "
        "확인할 수 없습니다. 무엇을 먼저 실행하고 "
        "무엇을 추가로 확인하겠습니까?"
    ),
    "q2": (
        "담당자나 상사가 자리를 비운 상태에서 지침에 "
        "없는 문제가 발생했습니다. 어디까지 직접 "
        "결정하고 언제 확인을 요청하겠습니까?"
    ),
    "q3": (
        "내가 만든 결과물에 예상보다 강하고 직접적인 "
        "수정 의견을 받았습니다. 무엇을 확인하고 "
        "어떻게 대응하겠습니까?"
    ),
    "q4": (
        "동료의 업무가 늦어져서 전체 일정이 밀릴 "
        "가능성이 있습니다. 역할과 일정을 어떻게 "
        "조정하겠습니까?"
    ),
    "q5": (
        "현재 인력과 시간으로 달성하기 어려운 높은 "
        "목표를 맡았습니다. 목표, 범위, 실행 방식을 "
        "어떻게 결정하겠습니까?"
    ),
}


ANSWER_TEMPLATE = (
    "상황 판단 → 우선순위 → 내가 취할 행동 → "
    "동료·상사와 공유하는 방법 → 예상 결과"
)

def classify_turnover_risk(
    overall_fit: float | None,
) -> str:
    """문화 적합도 점수로 실험용 조기 퇴사 위험 신호를 분류한다."""

    if overall_fit is None:
        return "판단 보류"

    if overall_fit >= 75:
        return "낮음"

    if overall_fit >= 50:
        return "중간"

    return "높음"


def make_result_table(
    report: dict,
) -> pd.DataFrame:
    """여섯 문화축 결과를 화면용 표로 변환한다."""

    rows = []

    for dimension_id, detail in (
        report["dimensions"].items()
    ):
        rows.append(
            {
                "문화축 ID": dimension_id,
                "문화축": DIMENSION_LABELS[
                    dimension_id
                ],
                "회사 점수": detail[
                    "company_score"
                ],
                "지원자 점수": detail[
                    "candidate_score"
                ],
                "적합도": detail[
                    "fit_score"
                ],
                "신뢰도": detail[
                    "confidence"
                ],
                "분석 상태": detail[
                    "status"
                ],
            }
        )

    return pd.DataFrame(rows)


def render_analysis_report(
    report: dict,
    analysis_id: int,
) -> None:
    """LangGraph의 최종 분석 결과를 대시보드로 표시한다."""

    overall_fit = report.get(
        "overall_fit"
    )

    coverage = report.get(
        "coverage",
        0,
    )

    turnover_risk = classify_turnover_risk(
        overall_fit
    )

    result_table = make_result_table(
        report
    )

    st.divider()
    st.subheader("3. 같은 상황에서 선택한 업무 방식")
    st.caption(
        "회사 답변은 에이전트 설계 실습을 위해 만든 가상 자료입니다."
    )

    company_answers = {
        item["question_id"]: item
        for item in report.get("company_scenario_answers", [])
    }

    if not company_answers:
        st.info(
            "이전 분석에는 회사 상황 답변이 없습니다. "
            "새 분석을 실행하면 비교 결과가 표시됩니다."
        )

    for question_id, question in QUESTIONS.items():
        company_answer = company_answers.get(question_id)
        if company_answer is None:
            continue

        with st.expander(
            f"{question_id.upper()} · {question}",
            expanded=(question_id == "q1"),
        ):
            company_column, candidate_column = st.columns(2)

            with company_column:
                st.markdown("**회사 답변 · 가상 기준**")
                st.write(company_answer["answer_text"])
                st.caption(
                    "우선순위: "
                    + " → ".join(company_answer["priority_order"])
                )
                st.caption(
                    "감수하는 선택: "
                    + company_answer["accepted_tradeoff"]
                )

            with candidate_column:
                st.markdown("**지원자 답변**")
                st.write(
                    report.get("scenario_answers", {}).get(
                        question_id,
                        "답변 없음",
                    )
                )

    st.subheader("4. 문화축 점수 · 보조 자료")

    with st.container(horizontal=True):
        st.metric(
            "종합 적합도",
            (
                f"{overall_fit:.1f}점"
                if overall_fit is not None
                else "판단 보류"
            ),
            border=True,
        )

        st.metric(
            "조기 퇴사 위험 신호",
            turnover_risk,
            border=True,
        )

        st.metric(
            "정보 충족률",
            f"{coverage * 100:.0f}%",
            border=True,
        )

        st.metric(
            "분석 ID",
            str(analysis_id),
            border=True,
        )

    st.caption(
        "조기 퇴사 위험 신호는 조직문화 적합도만 사용한 "
        "실험용 규칙입니다. 75점 이상은 낮음, "
        "50점 이상 75점 미만은 중간, "
        "50점 미만은 높음으로 표시합니다."
    )

    with st.container(border=True):
        st.markdown("**지원자 업무 성향 요약**")

        st.write(
            report.get(
                "candidate_summary",
                "요약 정보가 없습니다.",
            )
        )

    st.subheader("5. 회사와 지원자 문화축 비교")

    chart_data = result_table[
        [
            "문화축",
            "회사 점수",
            "지원자 점수",
        ]
    ].dropna()

    st.bar_chart(
        chart_data,
        x="문화축",
        y=[
            "회사 점수",
            "지원자 점수",
        ],
        y_label="점수",
        color=[
            "#3B82F6",
            "#F97316",
        ],
        stack=False,
        sort=False,
        height=380,
    )

    st.dataframe(
        result_table[
            [
                "문화축",
                "회사 점수",
                "지원자 점수",
                "적합도",
                "신뢰도",
                "분석 상태",
            ]
        ],
        hide_index=True,
    )

    observed_rows = result_table.dropna(
        subset=["적합도"]
    )

    matching_dimensions = observed_rows[
        observed_rows["적합도"] >= 75
    ]["문화축"].tolist()

    different_dimensions = observed_rows[
        observed_rows["적합도"] < 75
    ]["문화축"].tolist()

    missing_dimensions = result_table[
        result_table["적합도"].isna()
    ]["문화축"].tolist()

    matching_column, difference_column = (
        st.columns(2, border=True)
    )

    with matching_column:
        st.markdown("**잘 맞는 문화축**")

        if matching_dimensions:
            for dimension_name in matching_dimensions:
                st.markdown(
                    f"- {dimension_name}"
                )
        else:
            st.write(
                "75점 이상인 문화축이 없습니다."
            )

    with difference_column:
        st.markdown("**차이를 확인할 문화축**")

        if different_dimensions:
            for dimension_name in different_dimensions:
                st.markdown(
                    f"- {dimension_name}"
                )
        else:
            st.write(
                "75점 미만인 문화축이 없습니다."
            )

        if missing_dimensions:
            st.markdown(
                "**추가 정보가 필요한 문화축**"
            )

            for dimension_name in missing_dimensions:
                st.markdown(
                    f"- {dimension_name}"
                )

    st.subheader("6. 문화축별 판단 근거와 면접 질문")

    for row in result_table.to_dict(
        orient="records"
    ):
        dimension_id = row["문화축 ID"]
        detail = report["dimensions"][
            dimension_id
        ]

        fit_score = detail.get(
            "fit_score"
        )

        fit_label = (
            f"{fit_score:.1f}점"
            if fit_score is not None
            else "정보 부족"
        )

        with st.expander(
            f"{row['문화축']} · 적합도 {fit_label}"
        ):
            st.markdown(
                "**지원자 원문 근거**"
            )

            st.write(
                detail.get(
                    "evidence_quote"
                )
                or "확인 가능한 원문 근거가 없습니다."
            )

            st.markdown(
                "**점수 판단 이유**"
            )

            st.write(
                detail.get(
                    "reasoning",
                    "판단 이유가 없습니다.",
                )
            )

            st.markdown(
                "**추천 면접 확인 질문**"
            )

            st.write(
                detail.get(
                    "follow_up_question",
                    "추가 질문이 없습니다.",
                )
            )

    st.subheader("7. 회사 조직문화 근거")

    company_summary = report.get("company_analysis_summary", "")
    if company_summary:
        st.info(company_summary)

    web_search_status = report.get("company_web_search_status", "")
    if web_search_status:
        st.caption(web_search_status)

    company_evidence = report.get(
        "company_evidence",
        [],
    )

    if not company_evidence:
        st.info(
            "검색된 회사 조직문화 근거가 없습니다."
        )

    for evidence in company_evidence:
        source = evidence.get(
            "source",
            "출처 미상",
        )

        with st.expander(source):
            source_type = evidence.get("source_type", "local")
            st.caption("외부 웹" if source_type == "web" else "등록된 회사 자료")
            st.write(
                evidence.get(
                    "text",
                    "근거 내용이 없습니다.",
                )
            )
            url = evidence.get("url")
            if source_type == "web" and url:
                st.link_button("원문 확인", url)


st.set_page_config(
    page_title="조직문화 적합성 분석 에이전트",
    page_icon="🧭",
    layout="wide",
)


st.title("조직문화 적합성 분석 에이전트")

st.write(
    "지원자의 자기소개서와 문제해결 상황 답변을 "
    "회사의 6개 조직문화 축과 비교합니다."
)

st.caption(
    "이 결과는 실험용 Culture-Fit 분석 결과이며, "
    "지원자의 업무방식과 조직문화의 차이를 확인하는 데 사용합니다."
)


st.session_state.setdefault(
    "latest_result",
    None,
)

st.session_state.setdefault(
    "latest_result",
    None,
)


analysis_tab, history_tab = st.tabs(
    [
        "새 분석",
        "이전 분석 이력",
    ]
)


with analysis_tab:
    st.subheader("1. 분석 대상 선택")

    company_id = st.selectbox(
        "회사 선택",
        options=list(COMPANY_LABELS),
        format_func=lambda value: COMPANY_LABELS[value],
    )

    pdf_paths = sorted(
        PDF_DIRECTORY.glob("*.pdf")
    )

    pdf_input_mode = st.radio(
        "Applicant PDF source",
        options=["Existing folder PDF", "Upload a different PDF"],
        index=0 if pdf_paths else 1,
        horizontal=True,
    )
    selected_pdf = None

    if pdf_input_mode == "Upload a different PDF":
        uploaded_pdf = st.file_uploader(
            "Upload a different applicant PDF",
            type=["pdf"],
            help=(
                "The uploaded PDF is stored temporarily and passed through "
                "the same extraction and analysis pipeline."
            ),
        )
        if uploaded_pdf is not None:
            selected_pdf = persist_uploaded_pdf(uploaded_pdf)
            pdf_paths = [selected_pdf]
            st.caption(f"Selected: {uploaded_pdf.name}")

    if pdf_input_mode == "Upload a different PDF" and selected_pdf is None:
        st.info("분석할 지원자 PDF를 업로드해 주세요.")
        st.stop()

    if not pdf_paths:
        st.error(
            "data/applications_pdf 폴더에서 "
            "지원자 PDF를 찾을 수 없습니다."
        )
        st.stop()

    selected_pdf = st.selectbox(
        "지원자 PDF 선택",
        options=pdf_paths,
        format_func=lambda path: path.name,
    )

    with st.expander(
        "PDF에서 추출한 자기소개서 확인"
    ):
        try:
            application_text = extract_pdf_text(
                selected_pdf
            )

        except Exception as error:
            st.error(str(error))

        else:
            preview_limit = 6000

            st.text(
                application_text[:preview_limit]
            )

            if len(application_text) > preview_limit:
                st.caption(
                    "화면에서는 앞부분 6,000자만 "
                    "보여주지만 분석에는 전체 글을 사용합니다."
                )

    st.subheader("2. 문제해결 상황 5문항")

    st.write(
        "정답을 찾는 문항이 아닙니다. 실제 업무에서 "
        "어떻게 판단하고 행동할지를 구체적으로 작성하세요."
    )

    with st.form(
        "culture_fit_analysis_form",
        border=True,
    ):
        answers = {}

        for index, (
            question_id,
            question,
        ) in enumerate(
            QUESTIONS.items(),
            start=1,
        ):
            answers[question_id] = st.text_area(
                label=f"{index}. {question}",
                key=f"answer_{question_id}",
                height=150,
                placeholder=ANSWER_TEMPLATE,
            )

        submitted = st.form_submit_button(
            "Culture-Fit 분석 시작",
            type="primary",
            width="stretch",
        )

    if submitted:
        answers_are_complete = all(
            answer.strip()
            for answer in answers.values()
        )

        if not answers_are_complete:
            st.error(
                "문제해결 상황 5개에 모두 답변해 주세요."
            )

        else:
            with st.spinner(
                "회사 문화 근거와 지원자 성향을 "
                "분석하고 있습니다..."
            ):
                try:
                    result = graph.invoke(
                        {
                            "selected_company": company_id,
                            "application_path": str(
                                selected_pdf
                            ),
                            "scenario_answers": answers,
                            "db_path": str(
                                DATABASE_PATH
                            ),
                            "retry_count": 0,
                        }
                    )

                except Exception as error:
                    st.session_state[
                        "latest_result"
                    ] = None

                    st.error(
                        "분석을 완료하지 못했습니다."
                    )

                    if "insufficient_quota" in str(error):
                        # 코드 문제가 아니라 OpenAI 계정 크레딧 소진(429). 재시도해도 해결되지 않음.
                        st.warning(
                            "OpenAI API 크레딧이 모두 소진되었습니다. "
                            "https://platform.openai.com/settings/organization/billing/ "
                            "에서 크레딧을 충전하거나 다른 API 키로 .env의 "
                            "OPENAI_API_KEY를 교체한 뒤 앱을 재시작하세요."
                        )

                    st.exception(error)

                else:
                    st.session_state[
                        "latest_result"
                    ] = {
                        "report": result[
                            "final_report"
                        ],
                        "analysis_id": result[
                            "analysis_id"
                        ],
                    }

                    st.success(
                        "분석을 완료하고 SQLite에 저장했습니다."
                    )

    latest_result = st.session_state.get(
        "latest_result"
    )

    if latest_result is not None:
        render_analysis_report(
            latest_result["report"],
            latest_result["analysis_id"],
        )

with history_tab:
    st.subheader("이전 분석 이력")

    st.write(
        "SQLite에 저장된 분석 결과를 최근 분석부터 확인합니다."
    )

    try:
        analyses = list_analyses(
            DATABASE_PATH
        )

    except Exception as error:
        st.error(
            "분석 이력을 불러오지 못했습니다."
        )
        st.exception(error)

    else:
        if not analyses:
            st.info(
                "아직 저장된 분석 결과가 없습니다."
            )

        else:
            history_rows = []

            for analysis in analyses:
                overall_fit = analysis.get(
                    "overall_fit"
                )

                history_rows.append(
                    {
                        "분석 ID": analysis[
                            "analysis_id"
                        ],
                        "회사": COMPANY_LABELS.get(
                            analysis.get(
                                "company_id"
                            ),
                            analysis.get(
                                "company_id",
                                "알 수 없음",
                            ),
                        ),
                        "지원자 PDF": analysis.get(
                            "source_file",
                            "알 수 없음",
                        ),
                        "종합 적합도": (
                            f"{overall_fit:.1f}점"
                            if overall_fit is not None
                            else "판단 보류"
                        ),
                        "위험 신호": (
                            classify_turnover_risk(
                                overall_fit
                            )
                        ),
                        "정보 충족률": (
                            f"{analysis.get('coverage', 0) * 100:.0f}%"
                        ),
                    }
                )

            history_table = pd.DataFrame(
                history_rows
            )

            st.dataframe(
                history_table,
                hide_index=True,
            )

            analysis_by_id = {
                analysis["analysis_id"]: analysis
                for analysis in analyses
            }

            def history_option_label(
                analysis_id: int,
            ) -> str:
                analysis = analysis_by_id[
                    analysis_id
                ]

                company_name = COMPANY_LABELS.get(
                    analysis.get("company_id"),
                    analysis.get(
                        "company_id",
                        "알 수 없음",
                    ),
                )

                source_file = analysis.get(
                    "source_file",
                    "알 수 없음",
                )

                return (
                    f"분석 #{analysis_id} · "
                    f"{company_name} · "
                    f"{source_file}"
                )

            selected_analysis_id = st.selectbox(
                "상세 결과를 확인할 분석 선택",
                options=list(analysis_by_id),
                format_func=history_option_label,
                key="selected_history_analysis_id",
            )

            selected_report = analysis_by_id[
                selected_analysis_id
            ]

            render_analysis_report(
                selected_report,
                selected_analysis_id,
            )
