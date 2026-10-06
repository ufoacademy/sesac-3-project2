import unittest

from src.services.company_registry import (
    get_company_labels,
    list_company_ids,
    list_source_company_ids,
)


class CompanyRegistryTest(unittest.TestCase):
    def test_company_ids_are_discovered_from_profiles(self):
        company_ids = list_company_ids()
        self.assertGreaterEqual(len(company_ids), 3)
        self.assertEqual(company_ids, sorted(company_ids))

    def test_source_directories_are_discovered(self):
        company_ids = list_source_company_ids()
        self.assertGreaterEqual(len(company_ids), 3)
        self.assertEqual(company_ids, sorted(company_ids))

    def test_company_labels_are_loaded_from_profiles(self):
        labels = get_company_labels()

        self.assertEqual(set(labels), set(list_company_ids()))
        self.assertTrue(all(labels.values()))


if __name__ == "__main__":
    unittest.main()
