import tempfile
import unittest
from pathlib import Path

from src.database import (
    list_analyses,
    load_analysis,
    save_analysis,
)


PAYLOAD = {
    "company_id": "toss",
    "applicant_id": "sample",
    "source_file": "sample.pdf",
    "source_hash": "abc123",
    "extracted_text": "지원자 자기소개서 원문",
    "scenario_answers": {
        "q1": "답변 1",
        "q2": "답변 2",
        "q3": "답변 3",
        "q4": "답변 4",
        "q5": "답변 5",
    },
    "overall_fit": 82.5,
    "coverage": 1.0,
    "dimensions": {
        "pace_preference": {
            "company_score": 5,
            "candidate_score": 4,
            "fit_score": 75.0,
            "confidence": 0.9,
            "evidence_quote": "빠르게 실행했습니다.",
        }
    },
}


class DatabaseTest(unittest.TestCase):
    def test_analysis_is_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "culture_fit.db"

            analysis_id = save_analysis(
                db_path,
                PAYLOAD,
            )

            loaded = load_analysis(
                db_path,
                analysis_id,
            )

        self.assertEqual(
            loaded["company_id"],
            "toss",
        )
        self.assertEqual(
            loaded["overall_fit"],
            82.5,
        )

    def test_repeated_analysis_gets_new_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "culture_fit.db"

            first_id = save_analysis(
                db_path,
                PAYLOAD,
            )
            second_id = save_analysis(
                db_path,
                PAYLOAD,
            )

            rows = list_analyses(db_path)

        self.assertNotEqual(
            first_id,
            second_id,
        )
        self.assertEqual(
            len(rows),
            2,
        )

    def test_unknown_analysis_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "culture_fit.db"

            with self.assertRaisesRegex(
                KeyError,
                "찾을 수 없습니다",
            ):
                load_analysis(
                    db_path,
                    999,
                )


if __name__ == "__main__":
    unittest.main()