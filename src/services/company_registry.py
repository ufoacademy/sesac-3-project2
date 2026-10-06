"""Discover company data from the repository instead of hard-coding IDs."""

from pathlib import Path

from src.services.company_loader import load_company_profile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPANY_DIRECTORY = PROJECT_ROOT / "data" / "companies"
SOURCE_DIRECTORY = PROJECT_ROOT / "data" / "sources"


def list_company_ids() -> list[str]:
    """Return company IDs that have a profile JSON file."""

    if not COMPANY_DIRECTORY.exists():
        return []

    return sorted(
        path.stem
        for path in COMPANY_DIRECTORY.glob("*.json")
        if path.is_file()
    )


def company_profile_path(company_id: str) -> Path:
    """Return the profile path for a company ID."""

    return COMPANY_DIRECTORY / f"{company_id}.json"


def get_company_labels() -> dict[str, str]:
    """Build the UI label map from each validated company profile."""

    labels: dict[str, str] = {}
    for company_id in list_company_ids():
        profile = load_company_profile(company_profile_path(company_id))
        labels[company_id] = profile.name
    return labels


def list_source_company_ids() -> list[str]:
    """Return company IDs that have a source-document directory."""

    if not SOURCE_DIRECTORY.exists():
        return []

    return sorted(
        path.name
        for path in SOURCE_DIRECTORY.iterdir()
        if path.is_dir()
    )
