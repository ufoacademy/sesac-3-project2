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

    def test_quote_not_in_source_is_rejected(self):
        profile = make_candidate_profile(
            "원문에 없는 문장"
        )

        with self.assertRaisesRegex(
            ValueError,
            "인용",
        ):
            validate_candidate_quotes(
                profile,
                "실제 자기소개서",
                {
                    "q1": "답변 1",
                    "q2": "답변 2",
                    "q3": "답변 3",
                    "q4": "답변 4",
                    "q5": "답변 5",
                },
            )


if __name__ == "__main__":
    unittest.main()
    