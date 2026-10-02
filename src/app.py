from langgraph.graph import END, START, StateGraph

from src.nodes import (
    analyze_candidate_node,
    calculate_fit_node,
    extract_pdf_node,
    generate_report_node,
    load_company_node,
    retrieve_company_evidence_node,
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

    builder.add_node(
        "retrieve_company_evidence",
        retrieve_company_evidence_node,
    )

    builder.add_node(
        "analyze_candidate",
        analyze_candidate_node,
    )

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

    builder.add_edge(
        "extract_pdf",
        "retrieve_company_evidence",
    )

    builder.add_edge(
        "retrieve_company_evidence",
        "analyze_candidate",
    )

    builder.add_conditional_edges(
        "analyze_candidate",
        route_after_candidate_analysis,
        {
            "retry": "analyze_candidate",
            "continue": "calculate_fit",
        },
    )

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