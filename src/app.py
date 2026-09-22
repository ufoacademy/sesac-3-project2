from langgraph.graph import StateGraph, START, END
from src.state import State
from src.nodes import chatbot_node

# 1. 커스텀 State 기반으로 그래프 빌더 생성
builder = StateGraph(State)

# 2. 노드 등록 ('chatbot'이라는 이름으로 등록)
builder.add_node("chatbot", chatbot_node)

# 3. 엣지 연결 (START -> chatbot -> END)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

# 4. 그래프 컴파일
graph = builder.compile()