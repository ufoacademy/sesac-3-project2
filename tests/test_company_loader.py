import json
import tempfile
import unittest
from pathlib import Path

from src.services.company_loader import load_company_profile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPANY_DIR = PROJECT_ROOT / "data" / "companies"


class CompanyLoaderTest(unittest.TestCase):
    def test_all_existing_company_profiles_load(self):
        paths = sorted(COMPANY_DIR.glob("*.json"))

        self.assertGreater(len(paths), 0)

        for path in paths:
            with self.subTest(path=path.name):
                profile = load_company_profile(path)

                self.assertTrue(profile.name)
                self.assertGreaterEqual(
                    profile.traits.pace_preference,
                    1,
                )
                self.assertLessEqual(
                    profile.traits.pace_preference,
                    5,
                )

    def test_toss_profile_contains_expected_values(self):
        profile = load_company_profile(
            COMPANY_DIR / "toss.json"
        )

        self.assertEqual(profile.name, "Toss")
        self.assertEqual(
            profile.traits.pace_preference,
            5,
        )
        self.assertEqual(
            profile.traits.autonomy_preference,
            5,
        )

    def test_missing_company_file_is_rejected(self):
        with self.assertRaisesRegex(
            FileNotFoundError,
            "회사",
        ):
            load_company_profile(
                COMPANY_DIR / "missing.json"
            )

    def test_out_of_range_trait_score_is_rejected(self):
        invalid_data = {
            "name": "테스트 회사",
            "one_line": "테스트용 조직문화",
            "core_values": ["자율", "협업", "성장"],
            "work_style": "자율적으로 협업합니다.",
            "decision_making": "구성원 토론으로 결정합니다.",
            "traits": {
                "pace_preference": 6,
                "autonomy_preference": 3,
                "hierarchy_tolerance": 3,
                "risk_tolerance": 3,
                "collaboration_style": 3,
                "growth_ambition": 3,
            },
            "who_thrives": [
                "자율적으로 일하는 사람",
                "협업을 선호하는 사람",
                "성장을 원하는 사람",
            ],
            "who_leaves_early": [
                "명확한 지시만 원하는 사람",
                "변화를 싫어하는 사람",
                "협업을 피하는 사람",
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid_company.json"

            path.write_text(
                json.dumps(
                    invalid_data,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "조직문화",
            ):
                load_company_profile(path)


if __name__ == "__main__":
    unittest.main()
