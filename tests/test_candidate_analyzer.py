import unittest
from unittest.mock import Mock

from src.agents.candidate_analyzer import (
    analyze_candidate,
    validate_candidate_quotes,
)
from src.schemas import CandidateCultureProfile


DIMENSION_IDS = (
    "pace_preference",
    "autonomy_preference",
    "hierarchy_tolerance",
    "risk_tolerance",
    "collaboration_style",
    "growth_ambition",
)


def make_candidate_profile(
    evidence_quote: str,
) -> CandidateCultureProfile:
    """테스트에서 사용할 가상 지원자 분석 결과를 만든다."""

    return CandidateCultureProfile.model_validate(
        {
            "summary": "빠르게 실험하고 공유하는 지원자",
            "dimensions": [
                {
                    "dimension_id": dimension_id,
                    "score": 4,
                    "confidence": 0.8,
                    "evidence_quote": evidence_quote,
                    "evidence_source": "application",
                    "reasoning": "행동 근거가 있습니다.",
                    "status": "observed",
                    "follow_up_question": (
                        "다른 상황에서도 같은 방식으로 행동했나요?"
                    ),
                }
                for dimension_id in DIMENSION_IDS
            ],
        }
    )


class CandidateAnalyzerTest(unittest.TestCase):
    def test_five_answers_are_required_before_model_call(self):
        model = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "5개",
        ):
            analyze_candidate(
                "자기소개서",
                {"q1": "답변"},
                model=model,
            )

        model.invoke.assert_not_called()

    def test_structured_profile_is_returned(self):
        profile = make_candidate_profile(
            "먼저 실행했습니다."
        )

        model = Mock()
        model.invoke.return_value = profile

        result = analyze_candidate(
            "먼저 실행했습니다.",
            {
                "q1": "답변 1",
                "q2": "답변 2",
                "q3": "답변 3",
                "q4": "답변 4",
                "q5": "답변 5",
            },
            model=model,
        )

        self.assertEqual(
            len(result.dimensions),
            6,
        )

    def test_fuzzy_quote_with_slight_rephrasing_is_accepted_and_aligned(self):
        source = (
            "저는 스타트업에서 빠르게 MVP를 제작해 배포하고 사용자 피드백을 주 단위로 수집하여 서비스를 개선했습니다."
        )
        rephrased_quote = (
            "빠르게 MVP를 제작하여 배포하고 사용자 피드백을 주단위로 수집해 서비스 개선"
        )
        profile = make_candidate_profile(rephrased_quote)

        from src.agents.candidate_analyzer import mark_invalid_quotes_as_missing
        cleaned_profile = mark_invalid_quotes_as_missing(
            profile,
            source,
            {f"q{i}": f"답변 {i}" for i in range(1, 6)},
        )

        first_dim = cleaned_profile.dimensions[0]
        # 유사도가 높아 탈락되지 않고 점수(4점)가 온전히 유지되어야 함
        self.assertEqual(first_dim.status, "observed")
        self.assertEqual(first_dim.score, 4)
        # 원본 문장으로 자동 보정(Auto-alignment)되었는지 확인
        self.assertEqual(first_dim.evidence_quote, source)

    def test_completely_hallucinated_quote_is_marked_as_missing(self):
        source = "스타트업에서 프론트엔드 리액트 개발을 담당했습니다."
        hallucinated_quote = (
            "대규모 분산 트래픽 처리를 위해 카프카와 레디스를 도입하여 최적화했습니다."
        )
        profile = make_candidate_profile(hallucinated_quote)

        from src.agents.candidate_analyzer import mark_invalid_quotes_as_missing
        cleaned_profile = mark_invalid_quotes_as_missing(
            profile,
            source,
            {f"q{i}": f"답변 {i}" for i in range(1, 6)},
        )

        first_dim = cleaned_profile.dimensions[0]
        # 원문에 없는 명백한 환각이므로 점수가 보류되어야 함
        self.assertEqual(first_dim.status, "missing")
        self.assertIsNone(first_dim.score)
        self.assertEqual(first_dim.confidence, 0.0)

    def test_validate_candidate_quotes_allows_fuzzy_match(self):
        source = "사용자 피드백을 주 단위로 수집하여 서비스를 개선했습니다."
        rephrased_quote = "사용자 피드백 주단위 수집 후 서비스 개선"
        profile = make_candidate_profile(rephrased_quote)

        # 예외가 발생하지 않고 통과해야 함
        validate_candidate_quotes(
            profile,
            source,
            {f"q{i}": f"답변 {i}" for i in range(1, 6)},
        )

    def test_validate_candidate_quotes_rejects_hallucination(self):
        source = "스타트업에서 개발했습니다."
        fake_quote = "인공지능 대규모 클러스터를 직접 구축했습니다."
        profile = make_candidate_profile(fake_quote)

        with self.assertRaises(ValueError):
            validate_candidate_quotes(
                profile,
                source,
                {f"q{i}": f"답변 {i}" for i in range(1, 6)},
            )


if __name__ == "__main__":
    unittest.main()
    