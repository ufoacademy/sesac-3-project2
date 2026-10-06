import unittest

from src.agent_schemas import CompanyEvidenceItem, CompanyEvidenceResult


class AgentSchemasTest(unittest.TestCase):
    def test_evidence_item_coerces_dict_source_to_string(self):
        raw_item = {
            "source": {"title": "Official Values Document", "type": "local"},
            "text": "자율과 책임을 중시합니다.",
            "relevance": "자율성 관련 근거",
            "source_type": "local",
        }
        item = CompanyEvidenceItem.model_validate(raw_item)
        self.assertEqual(item.source, "Official Values Document")
        self.assertEqual(item.source_type, "local")

    def test_evidence_result_validates_with_dict_sources(self):
        payload = {
            "summary": "기업 문화 요약",
            "evidence": [
                {
                    "source": {"title": "Job Posting Excerpt", "type": "local"},
                    "text": "도전적인 성장을 추구합니다.",
                },
                {
                    "source": "Plain String Source",
                    "text": "직접 소통을 선호합니다.",
                },
            ],
        }
        result = CompanyEvidenceResult.model_validate(payload)
        self.assertEqual(len(result.evidence), 2)
        self.assertEqual(result.evidence[0].source, "Job Posting Excerpt")
        self.assertEqual(result.evidence[1].source, "Plain String Source")


if __name__ == "__main__":
    unittest.main()
