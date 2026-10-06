import json

from langchain_openai import ChatOpenAI

from src.schemas import CandidateCultureProfile


REQUIRED_ANSWER_IDS = {
    "q1",
    "q2",
    "q3",
    "q4",
    "q5",
}


DIMENSION_GUIDE = """
1. pace_preference
   1점: 충분히 검토한 후 신중하게 실행
   5점: 불확실해도 빠르게 실행하고 수정

2. autonomy_preference
   1점: 명확한 지시와 승인 선호
   5점: 스스로 판단하고 결과까지 책임

3. hierarchy_tolerance
   1점: 수평적인 관계와 자유로운 의견 제시 선호
   5점: 위계, 승인 절차, 정해진 보고 체계 수용

4. risk_tolerance
   1점: 안정적이고 검증된 방법 선호
   5점: 실패 가능성이 있어도 새로운 시도 선호

5. collaboration_style
   1점: 조화와 합의를 중시하는 협업 선호
   5점: 직설적인 토론과 강한 피드백 수용

6. growth_ambition
   1점: 안정과 일·생활 균형 중시
   5점: 높은 목표, 성과 압박, 빠른 성장 선호
"""


def build_model():
    """구조화된 지원자 분석 결과를 반환하는 모델을 만든다."""

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    ).with_structured_output(
        CandidateCultureProfile
    )


def analyze_candidate(
    application_text: str,
    answers: dict[str, str],
    model=None,
) -> CandidateCultureProfile:
    """자기소개서와 상황 답변을 여섯 가지 문화축으로 분석한다."""

    if not application_text.strip():
        raise ValueError(
            "분석할 자기소개서 원문이 필요합니다."
        )

    if (
        set(answers) != REQUIRED_ANSWER_IDS
        or any(
            not answer.strip()
            for answer in answers.values()
        )
    ):
        raise ValueError(
            "문제해결 상황 5개에 모두 답변해야 합니다."
        )

    structured_model = model or build_model()

    prompt = f"""
지원자의 자기소개서와 문제해결 상황 답변을
여섯 가지 업무문화 축으로 분석하세요.

회사 정보와 비교하지 말고 지원자 자신의
업무 방식과 행동만 분석하세요.

{DIMENSION_GUIDE}

분석 규칙:
- 각 문화축을 반드시 한 번씩 작성하세요.
- 행동 근거가 있으면 status를 observed로 작성하세요.
- observed인 경우 score는 1점에서 5점 사이로 작성하세요.
- evidence_quote는 입력 원문에서 10~80자의 연속된 구절을 그대로 복사하세요.
- 서로 떨어진 여러 표현을 합치거나 문장을 자연스럽게 고치지 마세요.
- 적절한 원문 구절이 없으면 해당 문화축을 missing으로 처리하세요.
- 자기소개서 근거는 evidence_source를 application으로 작성하세요.
- 상황 답변 근거는 evidence_source를 scenario로 작성하세요.
- 근거가 부족하면 status와 evidence_source를 missing으로 작성하세요.
- 근거가 부족하면 score와 evidence_quote를 비워두세요.
- confidence는 근거의 확실성을 0에서 1 사이로 작성하세요.
- reasoning에는 점수 판단 이유를 작성하세요.
- follow_up_question에는 면접에서 확인할 질문을 작성하세요.

[자기소개서]
{application_text}

[문제해결 상황 답변]
{json.dumps(answers, ensure_ascii=False, indent=2)}
"""

    profile = structured_model.invoke(prompt)

    profile = mark_invalid_quotes_as_missing(
        profile,
        application_text,
        answers,
    )

    validate_candidate_quotes(
        profile,
        application_text,
        answers,
    )

    return profile

def _normalize_for_quote_check(
    text: str,
) -> str:
    """줄바꿈과 연속 공백을 한 칸의 공백으로 통일한다."""

    return " ".join(
        text.split()
    )


def _combine_sources(
    application_text: str,
    answers: dict[str, str],
) -> str:
    """자기소개서와 다섯 답변을 하나의 검증 원문으로 합친다."""

    return (
        application_text
        + "\n"
        + "\n".join(answers.values())
    )


def _extract_char_bigrams(text: str) -> set[str]:
    """공백과 기호를 제외한 연속 2글자(바이그램) 집합을 추출한다."""
    cleaned = "".join(c for c in text if c.isalnum())
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()
    return {cleaned[i : i + 2] for i in range(len(cleaned) - 1)}


def find_best_matching_quote(
    quote: str,
    source_text: str,
    threshold: float = 0.65,
) -> tuple[bool, str, float]:
    """인용구가 원문과 정확히 일치하지 않더라도, 
    한국어 조사·어미 변형이나 축약이 반영된 실제 원문 구절을 찾아 일치 여부를 판별한다.
    
    1. 완전 일치 (Exact Substring): 유사도 1.0으로 즉시 통과
    2. 문장 분할 후 바이그램 유사도 계산: 핵심 어휘가 65% 이상 일치하는 문장이 원문에 존재하면 통과

    Returns:
        (is_valid, matched_sentence, similarity)
    """
    if not quote or not source_text:
        return False, "", 0.0

    normalized_quote = _normalize_for_quote_check(quote)
    normalized_source = _normalize_for_quote_check(source_text)

    # 1단계: 완전 일치 검사
    if normalized_quote in normalized_source:
        return True, quote, 1.0

    # 2단계: 문장 단위 분할 후 최고 유사도 문장 매칭
    import re

    raw_sentences = [
        s.strip()
        for s in re.split(r"(?<=[.?!])\s+|\n+", source_text)
        if s.strip()
    ]
    sentences = [s for s in raw_sentences if len(s) >= 5]
    if not sentences:
        sentences = [source_text.strip()]

    quote_bigrams = _extract_char_bigrams(normalized_quote)
    if not quote_bigrams:
        return False, "", 0.0

    best_sentence = ""
    best_similarity = 0.0

    for sentence in sentences:
        sentence_bigrams = _extract_char_bigrams(sentence)
        if not sentence_bigrams:
            continue
        intersection = quote_bigrams & sentence_bigrams
        similarity = len(intersection) / len(quote_bigrams)

        if similarity > best_similarity:
            best_similarity = similarity
            best_sentence = sentence

    if best_similarity >= threshold:
        return True, best_sentence, best_similarity

    return False, "", best_similarity


def mark_invalid_quotes_as_missing(
    profile: CandidateCultureProfile,
    application_text: str,
    answers: dict[str, str],
) -> CandidateCultureProfile:
    """원문에서 확인되지 않는 인용의 문화축을 정보 부족으로 바꾼다.
    
    사소한 어미/조사 변형(유사도 65% 이상)은 인정하고 원문 문장으로 자동 보정하며,
    명백한 환각(유사도 65% 미만)인 경우에만 점수를 보류 처리한다.
    """

    combined_sources = _combine_sources(
        application_text,
        answers,
    )

    profile_data = profile.model_dump()

    for dimension in profile_data["dimensions"]:
        if dimension["status"] != "observed":
            continue

        evidence_quote = dimension.get(
            "evidence_quote"
        )
        if not evidence_quote:
            dimension["score"] = None
            dimension["confidence"] = 0.0
            dimension["evidence_quote"] = None
            dimension["evidence_source"] = "missing"
            dimension["status"] = "missing"
            dimension["reasoning"] = (
                "인용문이 제시되지 않아 점수를 보류했습니다."
            )
            continue

        is_valid, matched_span, similarity = find_best_matching_quote(
            evidence_quote,
            combined_sources,
            threshold=0.65,
        )

        if is_valid:
            # 원문과 정확히 일치하지는 않지만 문맥이 일치하는 경우 원본 구절로 자동 보정
            if similarity < 1.0 and matched_span:
                dimension["evidence_quote"] = matched_span
            continue

        # 원문에서 전혀 근거를 찾을 수 없는 명백한 환각인 경우 점수 보류
        dimension["score"] = None
        dimension["confidence"] = 0.0
        dimension["evidence_quote"] = None
        dimension["evidence_source"] = "missing"
        dimension["status"] = "missing"
        dimension["reasoning"] = (
            "LLM이 제시한 근거 문장을 입력 원문에서 "
            "확인할 수 없어 점수를 보류했습니다."
        )

    return CandidateCultureProfile.model_validate(
        profile_data
    )


def validate_candidate_quotes(
    profile: CandidateCultureProfile,
    application_text: str,
    answers: dict[str, str],
) -> None:
    """남아 있는 observed 인용이 실제 원문(또는 유사 원문)에 있는지 검사한다."""

    combined_sources = _combine_sources(
        application_text,
        answers,
    )

    for dimension in profile.dimensions:
        if dimension.status != "observed":
            continue

        evidence_quote = (
            dimension.evidence_quote
        )
        if not evidence_quote:
            continue

        is_valid, _, similarity = find_best_matching_quote(
            evidence_quote,
            combined_sources,
            threshold=0.65,
        )

        if not is_valid:
            raise ValueError(
                "지원자 원문에서 인용을 찾을 수 없습니다: "
                f"{dimension.dimension_id} / "
                f"생성된 인용: {evidence_quote!r} (유사도: {similarity:.2f})"
            )