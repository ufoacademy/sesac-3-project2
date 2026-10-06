import json
from pathlib import Path

from pydantic import ValidationError

from src.schemas import CompanyCultureProfile


def load_company_profile(
    path: Path,
) -> CompanyCultureProfile:
    """회사 조직문화 JSON 파일을 읽고 형식을 검사한다."""

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"회사 조직문화 파일을 찾을 수 없습니다: {path}"
        )

    try:
        json_text = path.read_text(encoding="utf-8")
        data = json.loads(json_text)

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise ValueError(
            f"회사 조직문화 파일을 읽을 수 없습니다: {path.name}"
        ) from error

    try:
        profile = CompanyCultureProfile.model_validate(data)

    except ValidationError as error:
        raise ValueError(
            f"회사 조직문화 데이터가 올바르지 않습니다: {path.name}"
        ) from error

    return profile
