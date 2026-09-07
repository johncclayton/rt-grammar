"""Walk a Lark parse tree and extract Data: items and Strategy: formulas."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from lark import Token, Tree
from lark.exceptions import LarkError

from criteria_viz.errors import ParseError
from validate_rts import load_grammar, read_script

ENTRY_ROOT = "EntrySetup"
EXIT_ROOT = "ExitRule"
FORMULA_ROOTS = frozenset({ENTRY_ROOT, EXIT_ROOT})


def _label_name(token: Token) -> str:
    return token.value.rstrip(":").strip()


def _keyword_name(token: Token) -> str:
    return token.value.rstrip(":").strip()


def parse_rts_file(path: Path, *, grammar_path: Path | None = None) -> Tree:
    grammar = str(grammar_path or Path("realtest.lark"))
    parser = load_grammar(grammar, quiet=True)
    try:
        return parser.parse(read_script(path))
    except LarkError as exc:
        raise ParseError(f"Failed to parse {path}: {exc}") from exc


def extract_script(tree: Tree) -> tuple[Mapping[str, Tree], Mapping[str, Mapping[str, Tree]]]:
    """Return (data_items, strategies) where strategies[name][EntrySetup] = expr tree."""
    data_items: dict[str, Tree] = {}
    strategies: dict[str, dict[str, Tree]] = {}

    for section in tree.children:
        if not isinstance(section, Tree):
            continue
        if section.data == "data_section":
            for decl in section.children:
                if isinstance(decl, Tree) and decl.data == "data_item_decl":
                    name = _label_name(decl.children[0])
                    value = _expr_from_tagged(decl.children[-1])
                    if value is not None:
                        data_items[name] = value
        elif section.data == "strategy_section":
            strategy_name = None
            for child in section.children:
                if isinstance(child, Token) and child.type == "NAME":
                    strategy_name = child.value
                    break
            if not strategy_name:
                continue
            bucket = strategies.setdefault(strategy_name, {})
            for decl in section.children:
                if not isinstance(decl, Tree) or decl.data != "str_formula_decl":
                    continue
                key = _keyword_name(decl.children[0])
                if key not in FORMULA_ROOTS:
                    continue
                expr = decl.children[-1]
                if isinstance(expr, Tree):
                    bucket[key] = expr

    if not strategies:
        raise ParseError("No Strategy: sections with EntrySetup/ExitRule found")

    return data_items, strategies


def _expr_from_tagged(node: Tree | Token) -> Tree | None:
    if isinstance(node, Token):
        return None
    if node.data == "tagged_value":
        for child in node.children:
            if isinstance(child, Tree) and child.data not in ("hash_tag",):
                return child
        return None
    if isinstance(node, Tree):
        return node
    return None
