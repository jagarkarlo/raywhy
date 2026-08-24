from __future__ import annotations


def parse_resource_hint(value: str) -> dict[str, float]:
    """Parse `NAME=VALUE,NAME=VALUE` without accepting malformed hints."""
    resources: dict[str, float] = {}
    if not value.strip():
        return resources

    for item in value.split(","):
        name, separator, amount = item.partition("=")
        if not separator or not name.strip() or not amount.strip():
            raise ValueError(f"invalid resource hint item: {item!r}")
        try:
            parsed = float(amount)
        except ValueError as error:
            raise ValueError(f"resource amount must be numeric: {item!r}") from error
        if parsed < 0:
            raise ValueError(f"resource amount must not be negative: {item!r}")
        resources[name.strip()] = parsed
    return resources