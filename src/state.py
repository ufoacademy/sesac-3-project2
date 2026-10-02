from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class State(TypedDict, total=False):
    # LangGraph Studio에서 사용할 수 있는 대화 기록
    messages: Annotated[
        Sequence[BaseMessage],
        add_messages,
    ]

    # 사용자가 입력하는 값
    selected_company: str
    application_path: str
    scenario_answers: dict[str, str]
    db_path: str

    # 각 노드가 처리하면서 만드는 중간 결과
    application_text: str
    company_data: dict[str, Any]
    company_evidence: list[dict[str, str]]
    candidate_profile: dict[str, Any]
    fit_result: dict[str, Any]

    # 사용자에게 보여주고 저장할 최종 결과
    final_report: dict[str, Any]
    analysis_id: int

    # 실행 상태와 오류 처리
    retry_count: int
    status: str
    error: str | None