import unittest

from src.scoring import calculate_fit, dimension_fit


class ScoringTest(unittest.TestCase):
    def test_same_score_is_100(self):
        self.assertEqual(dimension_fit(4, 4), 100.0)

    def test_one_point_difference_is_75(self):
        self.assertEqual(dimension_fit(4, 3), 75.0)

    def test_four_point_difference_is_zero(self):
        self.assertEqual(dimension_fit(5, 1), 0.0)

    def test_missing_axis_is_excluded_and_reduces_coverage(self):
        result = calculate_fit(
            {
                "pace_preference": 4,
                "autonomy_preference": 3,
            },
            {
                "pace_preference": 3,
                "autonomy_preference": None,
            },
        )

        self.assertEqual(result["overall_fit"], 75.0)
        self.assertEqual(result["coverage"], 0.5)
        self.assertIsNone(
            result["dimensions"]["autonomy_preference"]["fit_score"]
        )

    def test_out_of_range_score_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "1에서 5"):
            dimension_fit(6, 3)


if __name__ == "__main__":
    unittest.main()