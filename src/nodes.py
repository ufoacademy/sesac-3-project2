from langchain_openai import ChatOpenAI
from src.state import State

# 사용할 LLM 모델 선언 (.env의 OPENAI_API_KEY 사용)
llm = ChatOpenAI(model="gpt-4o-mini")

def chatbot_node(state: State) -> dict:
    """사용자의 이전 대화 메시지들을 읽고 LLM 답변을 생성하는 노드"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}