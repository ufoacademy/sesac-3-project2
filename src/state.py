from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class State(TypedDict):
    # list 대신 BaseMessage 시퀀스로 명시
    messages: Annotated[Sequence[BaseMessage], add_messages]