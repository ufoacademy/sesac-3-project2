from src.state import State


def route_after_candidate_analysis(
    state: State,
) -> str:
    """지원자 분석 성공 여부에 따라 다음 경로를 결정한다."""

    if state.get("candidate_profile"):
        return "continue"

    retry_count = state.get(
        "retry_count",
        0,
    )

    if retry_count <= 1:
        return "retry"

    error_message = state.get(
        "error"
    ) or "지원자 분석에 두 번 실패했습니다."

    raise ValueError(error_message)