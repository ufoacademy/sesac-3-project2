import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"
FONT_NAME = "MalgunGothic"
pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

OUTPUT_DIR = os.path.join("data", "applications_pdf")

# 잡코리아 등에서 일반적으로 요구하는 4문항 자기소개서 형식(성장과정 / 성격의 장단점 / 지원동기 / 입사 후 포부)의
# 가상 지원자 10명 샘플 데이터입니다.
APPLICANTS = [
    {
        "id": "c01", "name": "김도전",
        "growth": "대학 시절부터 새로운 것에 도전하는 걸 좋아해 여러 사이드 프로젝트를 짧은 기간에 만들어보며 성장했습니다. 완벽하게 준비되지 않아도 일단 시작해서 부딪히며 배우는 방식이 저에게 잘 맞았습니다.",
        "personality": "장점은 실행력입니다. 문제가 생기면 오래 고민하기보다 바로 시도해보고 결과로 판단합니다. 단점은 가끔 속도를 우선하다 보니 꼼꼼함이 부족할 때가 있는데, 동료의 리뷰를 적극적으로 받아 보완하고 있습니다.",
        "motivation": "빠르게 실험하고 결과로 증명하는 조직 문화에 매력을 느껴 지원했습니다. 완벽한 계획보다 일단 만들어보고 고쳐나가는 방식을 선호합니다.",
        "aspiration": "입사 후에는 작은 기능이라도 빠르게 배포하고 데이터로 검증하며, 팀이 더 빠르게 실행할 수 있는 문화를 함께 만들어가고 싶습니다.",
    },
    {
        "id": "c02", "name": "박안정",
        "growth": "학창 시절부터 계획을 세우고 차근차근 실행하는 것을 좋아했고, 대학에서도 꾸준함으로 좋은 결과를 얻은 경험이 많습니다.",
        "personality": "장점은 꼼꼼함과 책임감입니다. 맡은 일은 끝까지 확인하고 마무리합니다. 단점은 새로운 방식을 받아들이는 데 시간이 걸린다는 점인데, 충분히 검토한 뒤에는 확실하게 적용하려고 노력합니다.",
        "motivation": "체계적인 프로세스와 품질 기준이 명확한 조직에서 안정적으로 전문성을 쌓고 싶어 지원했습니다.",
        "aspiration": "입사 후에는 기존 프로세스를 꼼꼼히 익히고, 작은 실수도 놓치지 않는 담당자로 신뢰를 쌓아가고 싶습니다.",
    },
    {
        "id": "c03", "name": "이워라",
        "growth": "프리랜서로 일하며 스스로 일정을 관리하는 법을 배웠고, 무리한 일정보다 지속 가능한 페이스를 유지하는 것이 결국 더 좋은 결과물로 이어진다는 것을 깨달았습니다.",
        "personality": "장점은 자기관리 능력입니다. 정해진 시간 안에 스스로 우선순위를 정해 일할 수 있습니다. 단점은 명확한 가이드가 없으면 방향을 잡는 데 시간이 걸린다는 점입니다.",
        "motivation": "제 스타일대로 작업하되 저녁 시간은 확실히 보장받을 수 있는 환경을 찾고 있습니다.",
        "aspiration": "입사 후에는 자율적으로 맡은 업무를 책임감 있게 수행하면서도, 지속 가능한 업무 방식을 팀에 제안하고 싶습니다.",
    },
    {
        "id": "c04", "name": "최합의",
        "growth": "여러 사람과 함께하는 활동에서 늘 조율하는 역할을 맡아왔고, 갈등 없이 원만하게 마무리하는 것에 보람을 느꼈습니다.",
        "personality": "장점은 다른 사람의 의견을 잘 듣고 조율하는 능력입니다. 단점은 갈등 상황에서 제 의견을 적극적으로 내세우지 못할 때가 있다는 점인데, 근거를 미리 정리해두는 방식으로 보완하고 있습니다.",
        "motivation": "안정적이고 조화로운 분위기에서 협업하는 조직 문화에 매력을 느꼈습니다.",
        "aspiration": "입사 후에는 여러 부서와 원만하게 협업하며 조직에 무리 없이 녹아드는 구성원이 되고 싶습니다.",
    },
    {
        "id": "c05", "name": "정완벽",
        "growth": "어릴 때부터 작은 것 하나도 정확하게 확인하는 습관이 있었고, R&D 업무를 하면서 그 습관이 큰 강점이 되었습니다.",
        "personality": "장점은 꼼꼼함과 정확성입니다. 작은 결함도 놓치지 않으려 여러 번 검증합니다. 단점은 검토에 시간을 많이 쓰다 보니 속도가 느리다는 평가를 받을 때가 있는데, 우선순위를 정해 검토 범위를 조절하려 노력합니다.",
        "motivation": "품질과 정확성을 최우선으로 여기는 조직에서 제 꼼꼼함을 발휘하고 싶습니다.",
        "aspiration": "입사 후에는 철저한 검증을 통해 품질 사고를 예방하는 데 기여하고 싶습니다.",
    },
    {
        "id": "c06", "name": "한성장",
        "growth": "학창 시절부터 경쟁 속에서 목표를 세우고 달성하는 것에 동기부여를 받았고, 늘 남들보다 한 발 앞서려 노력했습니다.",
        "personality": "장점은 강한 성취 욕구와 추진력입니다. 압박감 속에서도 성과를 냅니다. 단점은 때로 지나치게 경쟁적으로 보일 수 있다는 점인데, 팀의 목표와 제 목표를 함께 맞추려 노력합니다.",
        "motivation": "치열하게 경쟁하며 빠르게 성장하고, 그만큼 확실하게 보상받는 조직을 원합니다.",
        "aspiration": "입사 후에는 여러 프로젝트를 주도적으로 이끌며 빠르게 성장하고 싶습니다.",
    },
    {
        "id": "c07", "name": "오유쾌",
        "growth": "사람들과 어울리며 아이디어를 나누는 것을 좋아했고, 학창 시절부터 여러 행사와 프로젝트를 기획하며 즐겁게 일하는 법을 배웠습니다.",
        "personality": "장점은 유쾌한 분위기를 만드는 능력과 창의성입니다. 단점은 격식이 중요한 자리에서 다소 캐주얼하게 보일 수 있다는 점인데, 상황에 맞게 톤을 조절하려 노력합니다.",
        "motivation": "자유롭게 아이디어를 내고 유쾌하게 일할 수 있는 분위기에 끌려 지원했습니다.",
        "aspiration": "입사 후에는 재미있고 참신한 아이디어로 브랜드에 활력을 더하고 싶습니다.",
    },
    {
        "id": "c08", "name": "윤원칙",
        "growth": "정해진 규칙을 지키는 것에서 안정감을 느꼈고, 학창 시절부터 맡은 역할의 기준을 철저히 지키는 편이었습니다.",
        "personality": "장점은 원칙을 지키는 신뢰성입니다. 단점은 예외 상황에 유연하게 대응하는 데 시간이 걸린다는 점인데, 경험이 쌓이면서 판단 기준을 스스로 정리해가고 있습니다.",
        "motivation": "정해진 기준과 절차가 명확한 조직에서 신뢰받는 업무를 하고 싶습니다.",
        "aspiration": "입사 후에는 체크리스트와 규정을 철저히 준수하며 품질을 지키는 구성원이 되고 싶습니다.",
    },
    {
        "id": "c09", "name": "서독립",
        "growth": "혼자 서비스를 기획부터 배포까지 만들어보며 스스로 판단하고 책임지는 경험을 쌓았고, 그 과정에서 자기주도적으로 일하는 방식이 저에게 맞다는 걸 알게 됐습니다.",
        "personality": "장점은 강한 자기주도성과 문제 해결 능력입니다. 단점은 협업 시 세세한 승인 절차를 답답하게 느낄 때가 있다는 점인데, 팀에서는 소통을 더 자주 하려고 노력합니다.",
        "motivation": "제 방식대로 문제를 해결할 수 있는 자율성이 큰 조직을 원합니다.",
        "aspiration": "입사 후에는 맡은 영역을 주도적으로 책임지며 빠르게 문제를 해결하는 구성원이 되고 싶습니다.",
    },
    {
        "id": "c10", "name": "강번아웃",
        "growth": "이전 직장에서 무리한 성과 압박 속에서 번아웃을 겪은 뒤, 지속 가능한 방식으로 일하는 것의 중요성을 깨달았습니다.",
        "personality": "장점은 스스로의 상태를 잘 파악하고 조절할 줄 안다는 점입니다. 단점은 과도한 목표 앞에서 소극적으로 반응할 때가 있다는 점인데, 이제는 미리 조율을 요청하는 방식으로 대응하고 있습니다.",
        "motivation": "이전 직장에서 번아웃을 겪은 뒤, 지속 가능한 속도로 일할 수 있는 곳을 찾고 있습니다.",
        "aspiration": "입사 후에는 건강한 페이스를 유지하면서도 꾸준히 기여하는 구성원이 되고 싶습니다.",
    },
]

SECTIONS = [
    ("1. 성장과정", "growth"),
    ("2. 성격의 장단점", "personality"),
    ("3. 지원동기", "motivation"),
    ("4. 입사 후 포부", "aspiration"),
]


def build_pdf(applicant: dict) -> str:
    path = os.path.join(OUTPUT_DIR, f"{applicant['id']}_{applicant['name']}.pdf")
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )
    title_style = ParagraphStyle("Title", fontName=FONT_NAME, fontSize=16, leading=22, spaceAfter=12)
    heading_style = ParagraphStyle("Heading", fontName=FONT_NAME, fontSize=12, leading=16, spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle("Body", fontName=FONT_NAME, fontSize=10.5, leading=16)

    story = [Paragraph(f"자기소개서 - {applicant['name']}", title_style), Spacer(1, 6)]
    for heading, key in SECTIONS:
        story.append(Paragraph(heading, heading_style))
        story.append(Paragraph(applicant[key], body_style))
    doc.build(story)
    return path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for applicant in APPLICANTS:
        path = build_pdf(applicant)
        print(f"[생성 완료] {path}")


if __name__ == "__main__":
    main()
