import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from dotenv import load_dotenv
load_dotenv()

import json
import os
import glob
import argparse
from src.schemas import CompanyCultureProfile
from langchain_openai import ChatOpenAI
from src.services.company_registry import PROJECT_ROOT, list_source_company_ids

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
structured_llm = llm.with_structured_output(CompanyCultureProfile)

def _load_source_text(company_id: str) -> str:
    folder = PROJECT_ROOT / "data" / "sources" / company_id
    blocks = []
    for path in sorted(folder.glob("*.txt")):
        with open(path, "r", encoding="utf-8") as f:
            blocks.append(f"### {os.path.basename(path)}\n{f.read()}")
    return "\n\n".join(blocks)

def build_profile(company_id: str) -> dict:
    source_text = _load_source_text(company_id)
    prompt = f"""당신은 조직문화 분석가입니다. 아래는 "{company_id}" 기업에 대한 여러 원본 문서(공식 인재상, 언론 보도 요약, 재직자 리뷰 요약, 채용공고 발췌)입니다.
이 문서들을 종합해 조직문화를 구조화된 형태로 요약하세요.

traits의 6개 축은 각각 1~5점으로 평가하세요:
- pace_preference: 신중함(1) ~ 초고속 실행(5)
- autonomy_preference: 명확한 지시 선호(1) ~ 완전 자율·책임(5)
- hierarchy_tolerance: 완전 수평 선호(1) ~ 위계·프로세스 수용(5)
- risk_tolerance: 안정 추구(1) ~ 과감한 도전(5)
- collaboration_style: 조화·합의 선호(1) ~ 직설적 토론·피드백 선호(5)
- growth_ambition: 워라밸·안정 선호(1) ~ 고성과·고압박 성장 선호(5)

who_leaves_early(조기 퇴사 위험이 높은 성향)와 who_thrives(잘 적응하는 성향)는 문서 내용에 직접 근거해 구체적으로 작성하세요.

[원본 문서]
{source_text}
"""
    profile = structured_llm.invoke(prompt)
    data = profile.model_dump()
    return {
        "id": company_id,
        **data,
        "generated_from": sorted(
            path.name
            for path in (PROJECT_ROOT / "data" / "sources" / company_id).glob("*.txt")
        ),
        "generation_method": "RAG 소스 문서 + LLM 구조화 추출",
    }

def main(company_ids: list[str] | None = None):
    output_directory = PROJECT_ROOT / "data" / "companies"
    output_directory.mkdir(parents=True, exist_ok=True)
    company_ids = company_ids or list_source_company_ids()
    if not company_ids:
        raise SystemExit("data/sources 아래에 회사별 원본 문서 폴더가 없습니다.")

    for company_id in company_ids:
        profile = build_profile(company_id)
        path = output_directory / f"{company_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        print(f"[생성 완료] {path} (traits: {profile['traits']})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "company_ids",
        nargs="*",
        help="생성할 회사 ID. 생략하면 data/sources 아래의 모든 회사 처리",
    )
    args = parser.parse_args()
    main(args.company_ids)
