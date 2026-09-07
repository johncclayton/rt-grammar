#!/usr/bin/env python3
"""
RealTest Script Validator

Validates each .rts file with (1) the realtest.lark grammar (Lark) and
(2) RealTest.exe -parse when the executable is available. RealTest is silent
on success (exit 0). On failure it returns a non-zero exit code; stdout/stderr
are often empty (known RealTest limitation), so the exit code alone indicates
a problem.

If RealTest.exe is not found, only Lark runs (with a one-time notice), unless
you pass --lark-only to skip the RealTest step explicitly.
"""

import sys
import json
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from lark import Lark
from lark.exceptions import (
    LarkError,
    LexError,
    ParseError,
    UnexpectedCharacters,
    UnexpectedEOF,
    UnexpectedInput,
    UnexpectedToken,
)
import argparse

DEFAULT_REALTEST_EXE = Path(r"C:\RealTest\RealTest.exe")


def load_grammar(grammar_path_str="realtest.lark", *, quiet: bool = False):
    """Load the Lark grammar from the specified path.

    The grammar is LALR(1) and depends on Lark's contextual lexer: RealTest's
    value syntax varies by item keyword, and the contextual lexer is what lets
    a path, an enum word and a formula each have their own terminal without
    colliding. Do not switch this to earley/dynamic -- it both misparses and
    runs some three orders of magnitude slower.
    """
    grammar_path = Path(grammar_path_str)
    if not grammar_path.exists():
        print(f"Error: Grammar file not found at {grammar_path}")
        sys.exit(1)

    try:
        grammar_content = grammar_path.read_text(encoding="utf-8")
        lark_parser = Lark(
            grammar_content,
            start="start",
            parser="lalr",
            lexer="contextual",
            propagate_positions=False,
            maybe_placeholders=False,
            # cache the LALR tables so repeated CLI runs skip the ~0.25s build;
            # Lark keys the cache on the grammar text, so an edit invalidates it
            cache=True,
        )
        if not quiet:
            print(f"[OK] Grammar loaded successfully from {grammar_path}")
        return lark_parser
    except Exception as e:
        print(f"Error loading grammar: {e}")
        sys.exit(1)


def find_rts_files(samples_dir: Path):
    """Find all .rts files in the samples directory, including subfolders."""
    if not samples_dir.exists():
        print(f"Error: Samples directory not found at {samples_dir}")
        sys.exit(1)

    rts_files = list(samples_dir.rglob("*.rts"))
    if not rts_files:
        print(f"No .rts files found in {samples_dir}")
        sys.exit(1)

    return sorted(rts_files, key=lambda p: str(p).lower())


def _source_context(content: str, line, column) -> str:
    """The offending source line with a caret under the column."""
    if not isinstance(line, int):
        return ""
    lines = content.splitlines()
    if not (0 < line <= len(lines)):
        return ""
    text = lines[line - 1].replace("\t", "    ")
    # the caret has to move with the tab expansion above
    col = column if isinstance(column, int) else 1
    prefix = lines[line - 1][: max(col - 1, 0)].replace("\t", "    ")
    return f"  {text}\n  {' ' * len(prefix)}^"


def format_lark_parse_error(path: Path, content: str, exc: Exception) -> str:
    """
    Format a Lark parse/lex error as "path:line:col", the offending source line
    with a caret, and a short description.

    Lark's own message names the terminal it fell back to, which for this
    grammar is usually NOTES_BODY: the contextual lexer re-lexes the failure
    point with the full terminal set to build the error, and that catch-all
    matches nearly anything. The token name is noise, so report the source line
    instead.
    """
    path_s = str(path.resolve()) if path.exists() else str(path)

    if isinstance(exc, UnexpectedToken):
        loc = f"{path_s}:{exc.line}:{exc.column}:"
        ctx = _source_context(content, exc.line, exc.column)
        shown = str(exc.token).strip().splitlines()[0][:40]
        if exc.token.type == "$END":
            detail = "unexpected end of file (unclosed parenthesis or missing value?)"
        elif shown.startswith("#"):
            # RealTest folds an unrecognized #word into the previous item's
            # value instead of flagging it, so a misspelled #endif silently
            # leaves a conditional block open
            detail = (f"{shown.split()[0]!r} is not a preprocessor directive "
                      f"(#define #undef #ifdef #ifndef #else #endif)")
        else:
            detail = f"unexpected input here: {shown!r}"
        return f"{loc}\n{ctx}\n  {detail}" if ctx else f"{loc} {detail}"

    if isinstance(exc, UnexpectedCharacters):
        loc = f"{path_s}:{exc.line}:{exc.column}:"
        ctx = _source_context(content, exc.line, exc.column)
        detail = f"unexpected character {content[exc.pos_in_stream]!r}"
        return f"{loc}\n{ctx}\n  {detail}" if ctx else f"{loc} {detail}"

    if isinstance(exc, UnexpectedEOF):
        lines = content.splitlines()
        footer = str(exc)
        if lines:
            n = len(lines)
            last = lines[-1]
            num_w = len(str(n))
            prefix = f"{n:>{num_w}} | "
            caret_line = " " * len(prefix) + " " * len(last) + "^"
            snippet = f"{prefix}{last}\n{caret_line} (end of input)"
            return f"{path_s}: (unexpected end of input)\n{snippet}\n\n{footer}"
        return f"{path_s}:\n{footer}"

    if isinstance(exc, UnexpectedInput):
        line = getattr(exc, "line", "?")
        col = getattr(exc, "column", "?")
        loc = f"{path_s}:{line}:{col}:"
        pos = getattr(exc, "pos_in_stream", None)
        if isinstance(pos, int) and pos >= 0:
            ctx = exc.get_context(content, span=80).rstrip("\n")
            return f"{loc}\n{ctx}\n\n{exc}"
        return f"{loc}\n{exc}"

    if isinstance(exc, (LexError, ParseError, LarkError)):
        return f"{path_s}: Lark {type(exc).__name__}\n{exc}"

    return f"{path_s}:\n{exc}"


def read_script(file_path: Path) -> str:
    """Read a .rts file.

    utf-8-sig handles the BOM the script editor writes on some files; scripts
    saved by older editors are cp1252, so fall back rather than crash on a
    stray accented character in a comment.
    """
    raw = file_path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# A commented-out "Notes:" at column 1 does not reliably stay a comment in
# RealTest -- it reads the line as an item named "notes" and rejects the file
# ("reserved syntax elements cannot be used as item names", "unrecognized
# setting name", ... depending on the enclosing section). The quirk is specific
# to Notes: //Strategy:, //Data:, //atr: and the rest comment out normally.
# Indenting the comment, or dropping the colon, avoids it.
#
# Whether a given file actually breaks depends on what follows the comment --
# a commented-out block that runs to end of file is tolerated, real items after
# it are not -- and that is not something worth reproducing. So the grammar
# treats a comment as a comment and this is reported as a WARNING: it never
# fails a file on its own, and when RealTest.exe is available its verdict is
# the authoritative one.
_COMMENTED_NOTES = re.compile(r"^//[ \t]*notes[ \t]*:", re.IGNORECASE | re.MULTILINE)


def check_commented_notes(content: str):
    """-> warning message, or None."""
    m = _COMMENTED_NOTES.search(content)
    if not m:
        return None
    line = content.count("\n", 0, m.start()) + 1
    return (f"line {line}: a commented-out \"Notes:\" at column 1 is not always "
            f"treated as a comment by RealTest. Indent it, or drop the colon.")


def validate_file(parser, file_path: Path):
    """Validate a single .rts file with Lark. -> (ok, error_message)"""
    content = ""
    try:
        content = read_script(file_path)
        parser.parse(content)
        return True, None
    except (ParseError, LexError, UnexpectedInput) as e:
        return False, format_lark_parse_error(file_path, content, e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def warn_file(file_path: Path):
    """Non-fatal warnings for a script. -> list of messages."""
    try:
        content = read_script(file_path)
    except OSError:
        return []
    return [w for w in (check_commented_notes(content),) if w]


def realtest_parse(exe: Path, file_path: Path, timeout_sec: float = 300.0):
    """
    Run RealTest.exe -parse on file_path.
    On success: exit code 0, typically no console output.
    On failure: non-zero exit code; stderr/stdout are usually empty because
    RealTest is a GUI app, so the message is read from batchlog.txt beside the
    executable. Returns (ok, error_message).
    """
    if not exe.is_file():
        return False, f"RealTest executable not found or not a file: {exe}"
    try:
        completed = subprocess.run(
            [str(exe), "-parse", str(file_path.resolve())],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        if completed.returncode == 0:
            return True, None
        out = (completed.stderr or "").strip() or (completed.stdout or "").strip()
        if not out:
            # batchlog.txt is rewritten each run and holds "Error in <file>
            # line N col M (context): description"
            batchlog = exe.parent / "batchlog.txt"
            if batchlog.is_file():
                logged = batchlog.read_text(encoding="utf-8", errors="replace").strip()
                if str(file_path.resolve()) in logged or "Error" in logged:
                    out = logged
        detail = out if out else f"exit code {completed.returncode}"
        return False, detail
    except subprocess.TimeoutExpired:
        return False, f"RealTest -parse timed out after {timeout_sec:g}s"
    except OSError as e:
        return False, f"Failed to run RealTest: {e}"


def load_status_data(data_file: Path):
    """Load existing validation status from data.json"""
    if data_file.exists():
        try:
            with open(data_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {data_file}: {e}")
    return {}


def save_status_data(data_file: Path, status_data):
    """Save validation status to data.json"""
    try:
        with open(data_file, 'w') as f:
            json.dump(status_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save {data_file}: {e}")


def _files_word(n: int) -> str:
    return "file" if n == 1 else "files"


def _lark_status_line(total: int, failed: int) -> str:
    if failed == 0:
        return f"Lark: OK ({total} {_files_word(total)})"
    return f"Lark: FAIL ({failed} of {total} {_files_word(total)})"


def _realtest_status_line(total: int, failed: int, *, skipped: Optional[str]) -> str:
    if skipped:
        return f"RealTest -parse: skipped ({skipped})"
    if failed == 0:
        return f"RealTest -parse: OK ({total} {_files_word(total)})"
    return f"RealTest -parse: FAIL ({failed} of {total} {_files_word(total)})"


def main():
    parser = argparse.ArgumentParser(description="RealTest Script Validator")
    
    parser.add_argument(
        "--file",
        type=str,
        help="Validate a specific .rts file instead of all samples"
    )
    
    parser.add_argument(
        "--grammar",
        type=str,
        default="realtest.lark",
        help="Path to the Lark grammar file (default: realtest.lark)"
    )
    
    parser.add_argument(
        "--samples",
        type=str,
        default="samples",
        help="Path to samples directory, searched recursively (default: samples)"
    )

    parser.add_argument(
        "--lark-only",
        action="store_true",
        help="Skip RealTest.exe -parse; validate with Lark grammar only.",
    )

    parser.add_argument(
        "--realtest-exe",
        type=str,
        default=None,
        help=(
            f"Path to RealTest.exe (default: REALTEST_EXE env var, else {DEFAULT_REALTEST_EXE})"
        ),
    )

    args = parser.parse_args()

    realtest_exe = (
        Path(args.realtest_exe)
        if args.realtest_exe
        else Path(os.environ.get("REALTEST_EXE", str(DEFAULT_REALTEST_EXE)))
    )

    run_realtest = (not args.lark_only) and realtest_exe.is_file()
    rt_skip_reason = None
    if args.lark_only:
        rt_skip_reason = "--lark-only"
    elif not realtest_exe.is_file():
        rt_skip_reason = "RealTest.exe not found"

    # Load grammar (no banner on success path)
    lark_parser = load_grammar(args.grammar, quiet=True)

    # Determine what to validate
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        files_to_validate = [file_path]
        samples_dir = file_path.parent
    else:
        samples_dir = Path(args.samples)
        files_to_validate = find_rts_files(samples_dir)

    total = len(files_to_validate)
    results = {}
    lark_failures: List[Tuple[str, str]] = []
    rt_failures: List[Tuple[str, str]] = []
    warnings: List[Tuple[str, str]] = []

    for file_path in files_to_validate:
        lark_ok, lark_err = validate_file(lark_parser, file_path)
        if not lark_ok:
            lark_failures.append((file_path.name, lark_err or ""))
        warnings.extend((file_path.name, w) for w in warn_file(file_path))

        rt_ok, rt_err = (True, None)
        if run_realtest:
            rt_ok, rt_err = realtest_parse(realtest_exe, file_path)
            if not rt_ok:
                rt_failures.append((file_path.name, rt_err or ""))

        success = lark_ok and rt_ok
        results[file_path.name] = "pass" if success else "fail"

    lark_failed_count = len(lark_failures)
    rt_failed_count = len(rt_failures)
    overall_failed = sum(1 for v in results.values() if v == "fail")
    all_ok = overall_failed == 0

    # Save status if validating samples directory (silent)
    if not args.file:
        data_file = samples_dir.parent / "data.json"
        save_status_data(data_file, results)

    def print_warnings():
        # advisory only -- they never change the exit code
        for name, warning in warnings:
            print(f"Warning: {name} {warning}")

    if all_ok:
        print(_lark_status_line(total, 0))
        if run_realtest:
            print(_realtest_status_line(total, 0, skipped=None))
        print_warnings()
        sys.exit(0)

    # Failure: status lines + details
    print(_lark_status_line(total, lark_failed_count))
    if run_realtest:
        print(_realtest_status_line(total, rt_failed_count, skipped=None))
    else:
        print(_realtest_status_line(total, 0, skipped=rt_skip_reason))

    print_warnings()
    print("---")
    for name, err in lark_failures:
        print(f"{name} -- Lark:\n{err}\n")
    for name, err in rt_failures:
        print(f"{name} -- RealTest -parse:\n{err}\n")

    sys.exit(1)


if __name__ == "__main__":
    main()

