import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from src.pdf_loader import extract_pdf_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PdfLoaderTest(unittest.TestCase):
    def test_all_project_pdfs_contain_extractable_text(self):
        paths = sorted(
            (PROJECT_ROOT / "data" / "applications_pdf").glob("*.pdf")
        )

        self.assertEqual(len(paths), 7)

        for path in paths:
            with self.subTest(path=path.name):
                text = extract_pdf_text(path)
                self.assertGreater(len(text), 100)

    def test_blank_pdf_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "blank.pdf"

            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)

            with path.open("wb") as file:
                writer.write(file)

            with self.assertRaisesRegex(ValueError, "텍스트"):
                extract_pdf_text(path)

    def test_missing_pdf_is_rejected(self):
        with self.assertRaisesRegex(FileNotFoundError, "PDF"):
            extract_pdf_text(Path("missing.pdf"))

    def test_corrupt_pdf_is_rejected_with_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "corrupt.pdf"
            path.write_bytes(b"not a pdf")

            with self.assertRaisesRegex(ValueError, "corrupt.pdf"):
                extract_pdf_text(path)


if __name__ == "__main__":
    unittest.main()