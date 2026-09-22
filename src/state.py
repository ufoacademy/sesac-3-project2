from typing import Annotated, Sequence, Optional, Dict, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class State(TypedDict):
    # 대화 기록 (Studio Chat UI 지원)
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 분석 대상 기업명 (예: toss, hyundai, baemin)
    selected_company: Optional[str]
    
    # 로드된 기업 문화 데이터
    company_data: Optional[Dict[str, Any]]
    
    # 조기 퇴사 위험 및 조직 적합도 분석 결과
    analysis_report: Optional[str]