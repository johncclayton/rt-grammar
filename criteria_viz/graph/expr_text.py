"""Render Lark formula subtrees as RTS source text."""

from __future__ import annotations

from lark import Token, Tree


def expr_to_text(tree: Tree | Token) -> str:
    if isinstance(tree, Token):
        return tree.value.rstrip(":")

    if not isinstance(tree, Tree):
        return str(tree)

    name = tree.data
    children = tree.children

    if name == "logical_not":
        # Tree is (NOT token, expr) — use the expression child, not the operator token.
        expr_child = children[-1]
        return f"not {expr_to_text(expr_child)}"
    if name == "negate":
        return f"-{expr_to_text(children[0])}"
    if name == "unary_plus":
        return f"+{expr_to_text(children[0])}"
    if name == "bitwise_not":
        return f"BITNOT {expr_to_text(children[0])}"

    if name in ("and_expr", "or_expr"):
        op = " and " if name == "and_expr" else " or "
        parts = [expr_to_text(c) for c in children if not (isinstance(c, Token) and c.type in ("AND", "OR"))]
        return op.join(parts)

    if name == "comparison":
        if len(children) == 1:
            return expr_to_text(children[0])
        left = expr_to_text(children[0])
        op = children[1].value if len(children) > 1 else ""
        right = expr_to_text(children[2]) if len(children) > 2 else ""
        return f"{left} {op} {right}"

    if name in ("additive", "multiplicative"):
        if not children:
            return ""
        parts = [expr_to_text(children[0])]
        i = 1
        while i < len(children):
            child = children[i]
            if isinstance(child, Token):
                if i + 1 < len(children):
                    parts.append(f" {child.value} {expr_to_text(children[i + 1])}")
                    i += 2
                else:
                    i += 1
            else:
                parts.append(f" {expr_to_text(child)}")
                i += 1
        return "".join(parts)

    if name == "power":
        if len(children) == 1:
            return expr_to_text(children[0])
        return f"{expr_to_text(children[0])} ^ {expr_to_text(children[1])}"

    if name == "offset":
        base = expr_to_text(children[0])
        if len(children) == 1:
            return base
        return f"{base}[{expr_to_text(children[1])}]"

    if name == "funcall":
        fname = children[0].value
        args = []
        for child in children[1:]:
            if isinstance(child, Tree) and child.data == "argument":
                if child.children:
                    args.append(expr_to_text(child.children[0]))
                else:
                    args.append("")
        return f"{fname}({', '.join(args)})"

    if name == "tagged_value":
        return expr_to_text(children[-1])

    if name in ("atom", "argument") and len(children) == 1:
        return expr_to_text(children[0])

    if len(children) == 1:
        return expr_to_text(children[0])

    if all(isinstance(c, Token) for c in children):
        return " ".join(c.value for c in children)

    return " ".join(expr_to_text(c) for c in children)
