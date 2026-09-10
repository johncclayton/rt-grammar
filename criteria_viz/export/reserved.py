"""RealTest reserved item names — cannot be used as Results/Scan column labels."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# OHLCV single-letter builtins (not all listed in reserved_names.txt)
_BUILTIN_SHORT = frozenset({"C", "O", "H", "L", "V", "R"})


@lru_cache(maxsize=1)
def load_reserved_names() -> frozenset[str]:
    path = Path(__file__).resolve().parents[2] / "reserved_names.txt"
    names = {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    names |= _BUILTIN_SHORT
    return frozenset(names)


def is_reserved_item_name(name: str) -> bool:
    """True if name cannot be a user-defined Results/Scan item label."""
    reserved = load_reserved_names()
    return name in reserved or name.lower() in {n.lower() for n in reserved}


def safe_item_label(name: str) -> str:
    """LHS label for Results/Scan when the natural name is reserved (RHS unchanged)."""
    if is_reserved_item_name(name):
        return f"X_{name}"
    return name
