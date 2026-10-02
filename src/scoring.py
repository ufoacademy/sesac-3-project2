def _validate_score(score: float | None) -> None:
    """점수가 1점에서 5점 사이인지 검사한다."""

    if score is not None and not 1 <= score <= 5:
        raise ValueError("점수는 1에서 5 사이여야 합니다.")


def dimension_fit(
    company_score: float,
    candidate_score: float | None,
) -> float | None:
    """한 가지 문화 차원의 적합도를 계산한다."""

    _validate_score(company_score)
    _validate_score(candidate_score)

    if candidate_score is None:
        return None

    fit_score = 100 * (
        1 - abs(company_score - candidate_score) / 4
    )

    return round(fit_score, 1)


def calculate_fit(
    company_scores: dict[str, float],
    candidate_scores: dict[str, float | None],
) -> dict:
    """여러 문화 차원의 종합 적합도와 분석 범위를 계산한다."""

    if not company_scores:
        raise ValueError("회사 점수가 한 개 이상 필요합니다.")

    dimensions = {}
    observed_fit_scores = []

    for dimension_id, company_score in company_scores.items():
        candidate_score = candidate_scores.get(dimension_id)

        fit_score = dimension_fit(
            company_score,
            candidate_score,
        )

        dimensions[dimension_id] = {
            "company_score": company_score,
            "candidate_score": candidate_score,
            "fit_score": fit_score,
        }

        if fit_score is not None:
            observed_fit_scores.append(fit_score)

    if observed_fit_scores:
        overall_fit = round(
            sum(observed_fit_scores)
            / len(observed_fit_scores),
            1,
        )
    else:
        overall_fit = None

    coverage = round(
        len(observed_fit_scores) / len(company_scores),
        2,
    )

    return {
        "overall_fit": overall_fit,
        "coverage": coverage,
        "dimensions": dimensions,
    }