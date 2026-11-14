"""Presentation helpers shared by the recommendation and analytics endpoints."""

FIT_LOW = 35.0
FIT_HIGH = 97.0


def fit_values(values: list[float]) -> list[float]:
    """Map raw similarities to a readable 0-100 scale within the candidate pool.

    The ranking always uses the raw cosine similarity. For the screen we stretch the pool
    onto a 35-97 band so that "82" reads as "strong within this shortlist" instead of the
    unhelpful "0.04" a raw TF-IDF cosine produces. Purely a presentation transform: it is
    monotone, so the order of the list never changes.
    """
    if not values:
        return []
    low, high = min(values), max(values)
    if high - low < 1e-9:
        return [round((FIT_LOW + FIT_HIGH) / 2, 1) for _ in values]
    return [
        round(FIT_LOW + (FIT_HIGH - FIT_LOW) * (value - low) / (high - low), 1) for value in values
    ]


def score_band(fit: float) -> str:
    if fit >= 85:
        return "excellent"
    if fit >= 70:
        return "strong"
    if fit >= 55:
        return "good"
    return "exploratory"
