from langgraph.graph import END, START, StateGraph

from src.nodes import (
    analysis_branch_complete_node,
    analyze_company_node,
    analyze_candidate_node,
    calculate_fit_node,
    extract_pdf_node,
    generate_report_node,
    load_company_node,
    join_subagents_node,
    save_result_node,
    validate_input_node,
    validate_result_node,
)
from src.routers import route_after_candidate_analysis
from src.state import State


def build_graph():
    """조직문화 적합도 분석 LangGraph를 만든다."""

    builder = StateGraph(State)

    builder.add_node(
        "validate_input",
        validate_input_node,
    )

    builder.add_node(
        "load_company",
        load_company_node,
    )

    builder.add_node(
        "extract_pdf",
        extract_pdf_node,
    )

    builder.add_node("company_subagent", analyze_company_node)
    builder.add_node("candidate_subagent", analyze_candidate_node)
    builder.add_node(
        "company_subagent_done",
        analysis_branch_complete_node,
    )
    builder.add_node(
        "candidate_subagent_done",
        analysis_branch_complete_node,
    )
    builder.add_node("join_subagents", join_subagents_node)

    builder.add_node(
        "calculate_fit",
        calculate_fit_node,
    )

    builder.add_node(
        "generate_report",
        generate_report_node,
    )

    builder.add_node(
        "validate_result",
        validate_result_node,
    )

    builder.add_node(
        "save_result",
        save_result_node,
    )

    builder.add_edge(
        START,
        "validate_input",
    )

    builder.add_edge(
        "validate_input",
        "load_company",
    )

    builder.add_edge(
        "load_company",
        "extract_pdf",
    )

    builder.add_edge("extract_pdf", "company_subagent")
    builder.add_edge("extract_pdf", "candidate_subagent")
    builder.add_edge("company_subagent", "company_subagent_done")

    builder.add_conditional_edges(
        "candidate_subagent",
        route_after_candidate_analysis,
        {
            "retry": "candidate_subagent",
            "continue": "candidate_subagent_done",
        },
    )

    builder.add_edge(
        ["company_subagent_done", "candidate_subagent_done"],
        "join_subagents",
    )

    builder.add_edge("join_subagents", "calculate_fit")

    builder.add_edge(
        "calculate_fit",
        "generate_report",
    )

    builder.add_edge(
        "generate_report",
        "validate_result",
    )

    builder.add_edge(
        "validate_result",
        "save_result",
    )

    builder.add_edge(
        "save_result",
        END,
    )

    return builder.compile()


graph = build_graph()
