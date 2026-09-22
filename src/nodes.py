import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from src.state import State

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

def analyze_culture_node(state: State) -> dict:
    """사용자가 질문한 기업(토스/현대차/배민)의 문화 데이터를 로드하고 분석하는 노드"""
    messages = state.get("messages", [])
    last_user_msg = messages[-1].content if messages else ""
    
    # 1. 기업 자동 감지
    company_key = "toss"
    if "현대" in last_user_msg:
        company_key = "hyundai"
    elif "배민" in last_user_msg or "우아한" in last_user_msg:
        company_key = "baemin"
    elif "토스" in last_user_msg:
        company_key = "toss"
        
    # 2. JSON 데이터 파일 읽기
    file_path = os.path.join("data", "companies", f"{company_key}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            company_info = json.load(f)
    except Exception as e:
        company_info = {"error": f"데이터 로드 실패: {str(e)}"}
    
    # 3. LLM 프롬프트 구성 (기업 문화 요약 및 조기 퇴사 유발 유형 분석)
    system_prompt = f"""
    당신은 기업 문화 및 인사 조직 적합도(Culture-Fit) 전문 컨설턴트입니다.
    아래 제공된 기업의 공식 문화 데이터를 바탕으로 사용자의 질문에 전문적으로 답변하세요.

    [기업 데이터]
    {json.dumps(company_info, ensure_ascii=False, indent=2)}

    [답변 가이드]
    1. 기업의 핵심 일하는 방식과 인재상을 명확히 설명하세요.
    2. 특히 **'어떤 성향의 지원자가 입사 시 조기 퇴사 위험이 높은지'** 구체적인 이유와 함께 분석해 주세요.
    """
    
    ai_response = llm.invoke([
        {"role": "system", "content": system_prompt},
        *messages
    ])
    
    return {
        "messages": [ai_response],
        "selected_company": company_key,
        "company_data": company_info,
        "analysis_report": ai_response.content
    }