from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(path: Path) -> str:
    """PDF 파일에서 모든 페이지의 글자를 추출한다."""

    if not path.exists():
        raise FileNotFoundError(
            f"PDF 파일을 찾을 수 없습니다: {path}"
        )

    try:
        reader = PdfReader(str(path))

        page_texts = [
            page.extract_text() or ""
            for page in reader.pages
        ]

        text = "\n".join(page_texts).strip()

    except Exception as error:
        raise ValueError(
            f"PDF 파일을 읽을 수 없습니다: {path.name}"
        ) from error

    if not text:
        raise ValueError(
            f"PDF에서 텍스트를 추출할 수 없습니다: {path.name}"
        )

    return text