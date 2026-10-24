"""Conservative offline token estimate for budgets (design §5, D-10)."""


def estimate_tokens(text: str) -> int:
    """ceil(chars / 3.5), in integer arithmetic so it is exact."""
    return (len(text) * 2 + 6) // 7
