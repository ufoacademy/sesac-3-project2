"""CandidateCultureProfile 구조화 출력 보정 회귀 테스트.

2026-10-06 StructuredOutputValidationError(13 validation errors) 재현:
- 6개 문화축 모두 status, follow_up_question 누락
- collaboration_style score=8 (10점 척도 사용)
"""

import unittest

from pydantic import ValidationError

from src.schemas import CandidateCultureProfile, CandidateDimension


def make_failing_llm_payload() -> dict:
    """실제 장애 때 gpt-4o-mini가 반환한 형태를 재현한다."""

    scores = {
        "pace_preference": 4,
        "autonomy_preference": 4,
        "hierarchy_tolerance": 3,
        "risk_tolerance": 3,
        "collaboration_style": 8,
        "growth_ambition": 4,
    }
    return {
        "summary": "Fast-moving collaborative candidate.",
        "dimensions": [
            {
                "dimension_id": dimension_id,
                "score": score,
                "confidence": 0.8,
                "evidence_quote": "고객 피드백을 매주 수집해 개선했습니다.",
                "evidence_source": "application",
                "reasoning": f"Evidence found to support {dimension_id}.",
            }
            for dimension_id, score in scores.items()
        ],
    }


class CandidateSchemaCoercionTest(unittest.TestCase):
    def test_failing_payload_from_incident_now_parses(self):
        profile = CandidateCultureProfile.model_validate(make_failing_llm_payload())

        self.assertEqual(len(profile.dimensions), 6)
        for dimension in profile.dimensions:
            self.assertEqual(dimension.status, "observed")
            self.assertTrue(dimension.follow_up_question)

    def test_ten_point_score_is_rescaled_to_five_point(self):
        profile = CandidateCultureProfile.model_validate(make_failing_llm_payload())
        collaboration = next(
            d for d in profile.dimensions if d.dimension_id == "collaboration_style"
        )
        self.assertEqual(collaboration.score, 4.0)

    def test_missing_status_without_quote_is_inferred_as_missing(self):
        dimension = CandidateDimension.model_validate(
            {
                "dimension_id": "risk_tolerance",
                "score": 3,
                "confidence": 0.4,
                "reasoning": "근거 부족",
            }
        )
        self.assertEqual(dimension.status, "missing")
        self.assertIsNone(dimension.score)
        self.assertEqual(dimension.evidence_source, "missing")

    def test_observed_without_score_is_downgraded_instead_of_crashing(self):
        dimension = CandidateDimension.model_validate(
            {
                "dimension_id": "pace_preference",
                "score": None,
                "confidence": 0.7,
                "evidence_quote": "빠르게 실행했습니다.",
                "evidence_source": "application",
                "reasoning": "점수 누락",
                "status": "observed",
                "follow_up_question": "질문",
            }
        )
        self.assertEqual(dimension.status, "missing")
        self.assertIsNone(dimension.evidence_quote)

    def test_out_of_range_values_are_clamped(self):
        dimension = CandidateDimension.model_validate(
            {
                "dimension_id": "growth_ambition",
                "score": 42,
                "confidence": 1.7,
                "evidence_quote": "성장하고 싶습니다.",
                "evidence_source": "scenario",
                "reasoning": "범위 밖",
                "status": "observed",
                "follow_up_question": "질문",
            }
        )
        self.assertEqual(dimension.score, 5.0)
        self.assertEqual(dimension.confidence, 1.0)

    def test_missing_summary_is_auto_generated(self):
        payload = make_failing_llm_payload()
        del payload["summary"]

        profile = CandidateCultureProfile.model_validate(payload)
        self.assertTrue(profile.summary)
        self.assertIn("분석 완료", profile.summary)
        self.assertEqual(len(profile.dimensions), 6)

    def test_missing_dimensions_are_auto_supplemented(self):
        payload = make_failing_llm_payload()
        # 6개 중 2개 축 삭제하여 4개 축만 제공
        payload["dimensions"] = payload["dimensions"][:4]

        profile = CandidateCultureProfile.model_validate(payload)
        self.assertEqual(len(profile.dimensions), 6)
        missing_dims = [d for d in profile.dimensions if d.status == "missing"]
        self.assertEqual(len(missing_dims), 2)

    def test_culture_dimensions_alias_key_is_supported(self):
        payload = make_failing_llm_payload()
        payload["culture_dimensions"] = payload.pop("dimensions")

        profile = CandidateCultureProfile.model_validate(payload)
        self.assertEqual(len(profile.dimensions), 6)


if __name__ == "__main__":
    unittest.main()
