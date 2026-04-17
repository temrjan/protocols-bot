"""Canonical list of product names used across handlers."""

PRODUCT_NAMES: tuple[str, ...] = (
    "DERMACOMPLEX",
    "OPHTALMOCOMPLEX",
    "NEUROCOMPLEX KIDS",
    "IMMUNOCOMPLEX",
    "IMMUNOCOMPLEX KIDS",
    "CALCIY TRIACTIVE D3",
    "BIFOLAK ZINCUM+C+D3",
    "BIFOLAK ZINCUM",
    "BIFOLAK MAGNIY / CAPSULA",
    "BIFOLAK MAGNIY / STICK",
    "BIFOLAK ACTIVE / CAPSULA",
    "BIFOLAK ACTIVE / STICK",
    "BIFOLAK NEO",
)


def get_predefined_products() -> list[str]:
    """Return a clean list of non-empty product names."""
    return [name.strip() for name in PRODUCT_NAMES if name.strip()]


__all__ = ["PRODUCT_NAMES", "get_predefined_products"]
