#!/usr/bin/env python3
"""Grammar regression suite.

  tests/valid/    every file must PARSE
  tests/invalid/  every file must be REJECTED

Both directories are also checked against realtest.exe when it is available,
so the suite catches the two failure modes that matter: rejecting a script
RealTest accepts, and accepting one it rejects. Pass --lark-only to skip the
RealTest half (for CI runners without it installed).

  python tests/run_tests.py
  python tests/run_tests.py --lark-only
  python tests/run_tests.py --corpus "C:\\RealTest\\Scripts"
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from lark import Lark

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from validate_rts import check_commented_notes, read_script  # noqa: E402
DEFAULT_EXE = Path(os.environ.get("REALTEST_EXE", r"C:\RealTest\realtest.exe"))
BATCHLOG = Path(r"C:\RealTest\batchlog.txt")

# RealTest resolves file references at parse time, so a missing include or data
# file is an error even though the syntax is fine. Those verdicts say nothing
# about the grammar.
FILE_ERRORS = ("unable to access", "unable to open", "unable to read", "not found")


def load_parser(grammar: Path) -> Lark:
    return Lark(grammar.read_text(encoding="utf-8"), start="start", parser="lalr",
                lexer="contextual", propagate_positions=False, maybe_placeholders=False)


def lark_check(parser: Lark, path: Path):
    """-> (accepted, message)"""
    try:
        parser.parse(read_script(path))
        return True, ""
    except Exception as exc:
        line = getattr(exc, "line", None)
        head = (str(exc).splitlines() or [""])[0]
        return False, (f"line {line}: " if line else "") + head[:100]


def realtest_check(exe: Path, path: Path):
    """-> (accepted, message) where a file-access failure counts as accepted,
    since it is not a verdict on syntax."""
    proc = subprocess.run([str(exe), "-parse", str(path)], capture_output=True, text=True)
    msg = ""
    if BATCHLOG.exists():
        msg = BATCHLOG.read_text(encoding="utf-8", errors="replace").strip()
        msg = msg.replace(str(path), path.name)
    if proc.returncode == 0:
        return True, ""
    if any(e in msg.lower() for e in FILE_ERRORS):
        return True, "(file access, not syntax)"
    return False, msg[:120]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grammar", default=str(ROOT / "realtest.lark"))
    ap.add_argument("--lark-only", action="store_true")
    ap.add_argument("--realtest-exe", default=str(DEFAULT_EXE))
    ap.add_argument("--corpus", help="also require every .rts under this tree to parse")
    args = ap.parse_args()

    exe = Path(args.realtest_exe)
    use_rt = not args.lark_only and exe.is_file()

    t0 = time.time()
    parser = load_parser(Path(args.grammar))
    build = time.time() - t0

    failures = []
    counts = {}

    # The commented-out "Notes:" trap is a warning, not a parse verdict: the
    # grammar deliberately treats a comment as a comment, so there is no
    # tests/valid or tests/invalid file for it.
    if not check_commented_notes("Data:\n// notes: prose\n\tx:\tC\n"):
        failures.append("check_commented_notes did not fire on a column-1 '// notes:'")
    if check_commented_notes("Data:\n\t// notes: prose\n\tx:\tC\n"):
        failures.append("check_commented_notes fired on an indented '// notes:'")

    for kind, folder, want in (("valid", HERE / "valid", True),
                               ("invalid", HERE / "invalid", False)):
        files = sorted(folder.glob("*.rts"))
        counts[kind] = len(files)
        for f in files:
            ok, msg = lark_check(parser, f)
            if ok is not want:
                verb = "rejected" if want else "accepted"
                failures.append(f"lark {verb} {kind}/{f.name}: {msg}")
            if use_rt:
                rt_ok, rt_msg = realtest_check(exe, f)
                if rt_ok is not want:
                    verb = "rejected" if want else "accepted"
                    failures.append(f"RealTest {verb} {kind}/{f.name}: {rt_msg}")

    corpus_n = 0
    if args.corpus:
        t = time.time()
        for f in sorted(Path(args.corpus).rglob("*.rts")):
            corpus_n += 1
            ok, msg = lark_check(parser, f)
            if not ok:
                # only a real failure if RealTest itself accepts the file
                if use_rt and not realtest_check(exe, f)[0]:
                    continue
                failures.append(f"lark rejected corpus {f}: {msg}")
        corpus_secs = time.time() - t

    print(f"grammar build:  {build:.2f}s")
    print(f"valid:          {counts['valid']} files (must parse)")
    print(f"invalid:        {counts['invalid']} files (must be rejected)")
    if args.corpus:
        print(f"corpus:         {corpus_n} files in {corpus_secs:.2f}s "
              f"({1000 * corpus_secs / max(corpus_n, 1):.1f} ms/file)")
    print(f"RealTest cross-check: {'on' if use_rt else 'off'}")

    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for line in failures:
            print("  " + line)
        return 1

    cv_code = run_criteria_viz_tests()
    if cv_code != 0:
        return cv_code

    print("\nAll checks passed.")
    return 0


def run_criteria_viz_tests() -> int:
    import unittest

    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_criteria_viz*.py")
    if suite.countTestCases() == 0:
        return 0
    print(f"\ncriteria_viz:   {suite.countTestCases()} tests")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
