from langgraph.graph import StateGraph, START, END
from src.state import State
from src.nodes import analyze_culture_node

# 그래프 빌더 초기화
builder = StateGraph(State)

# 노드 등록
builder.add_node("analyze_culture", analyze_culture_node)

# 엣지 연결 (START -> analyze_culture -> END)
builder.add_edge(START, "analyze_culture")
builder.add_edge("analyze_culture", END)

# 컴파일
graph = builder.compile()