# RealTest Script Validator - Standalone Package

Validate RealTest `.rts` script files using the RealTest Lark grammar.

## What's Included

- `validate_rts.py` - Standalone validator script
- `realtest.lark` - Complete RealTest language grammar
- `example_strategy.rts` - Sample RealTest script for testing
- `README.md` - This file

## Requirements

**Python 3.7+** with Lark (see [`requirements.txt`](requirements.txt)).

Setup steps (**uv** recommended; **venv + pip** as alternative) are in **[`QUICKSTART.md`](QUICKSTART.md)**.

```bash
uv run --with lark python validate_rts.py --file example_strategy.rts
```

## Quick Start

### Validate Single File

```bash
python validate_rts.py --file example_strategy.rts
```

### Validate Directory of Scripts

```bash
python validate_rts.py --samples path/to/scripts/
```

### Custom Grammar Path

```bash
python validate_rts.py --file script.rts --grammar path/to/realtest.lark
```

## Usage

```
python validate_rts.py [OPTIONS]

Options:
  --file FILE          Validate specific .rts file
  --grammar GRAMMAR    Path to grammar file (default: realtest.lark)
  --samples SAMPLES    Path to samples directory (default: samples)
  --lark-only          Skip RealTest.exe -parse (Lark grammar only)
  --realtest-exe PATH  Path to RealTest.exe (else REALTEST_EXE or default)
```

By default, each file is checked with **Lark** and, when `RealTest.exe` is available, **RealTest -parse**. If the executable is missing, only Lark runs. Use `--lark-only` to force grammar-only validation. On **success**, output is two lines when both checks run (`Lark: OK …` and `RealTest -parse: OK …`), or one line if only Lark runs.

`Warning:` lines may also appear. They flag script patterns RealTest handles surprisingly (see **Known divergences** below) and never change the exit code.

### Examples

**Validate single script:**
```bash
python validate_rts.py --file my_strategy.rts

# Output (when RealTest.exe is available):
# Lark: OK (1 file)
# RealTest -parse: OK (1 file)
```

**Validate directory:**
```bash
python validate_rts.py --samples my_strategies/

# Output when all pass (with RealTest.exe):
# Lark: OK (25 files)
# RealTest -parse: OK (25 files)
#
# On failure, the same two status lines include FAIL counts, then "---" and per-file errors.
```

**With custom grammar:**
```bash
python validate_rts.py \
  --file script.rts \
  --grammar /path/to/my_realtest.lark
```

## What It Validates

**Lark (always):**

- ✅ Every section type, and which items are legal in each one
- ✅ Item keyword names — an unknown `Settings:` keyword or `Strategy:` element is an error, as it is in RealTest
- ✅ Enum values — `Side: Sideways`, `QtyType: Contracts` and `BarSize: Hourly` are all rejected
- ✅ Reserved item names — `atr: ATR(10)` and `EndOfQuarter: ...` are errors, the same way RealTest answers "reserved syntax elements cannot be used as item names" (the 500-name list is in `reserved_names.txt`)
- ✅ Value shapes per keyword: a path, a date, a boolean, a number, a name list or a formula
- ✅ The full formula language: operators, offsets, function calls, symbol / strategy / industry-index / bar-size references, breadth operators and their grouping modifiers
- ✅ `Parameters:` value forms, `WalkForward:` sections, output format specs
- ✅ Preprocessor directives, all three comment styles, continuation lines

**RealTest -parse (when `RealTest.exe` is found, unless `--lark-only`):**

- ✅ The installed RealTest parser accepts the script (same as running `RealTest.exe -parse` on the file)
- ℹ️ RealTest signals failure with a **non-zero exit code**; it often prints **nothing** to stdout/stderr (known limitation). The validator treats the exit code as authoritative, and `batchlog.txt` in the RealTest folder holds the message.

## What It Doesn't Check

The grammar is a syntax check. It does not know about:
- ❌ Whether a referenced file exists (data file, `Include:` target, trade list, holiday list)
- ❌ Whether an item is defined before it is referenced within its section
- ❌ Whether a symbol, watchlist or `In<XXX>` index-membership variable exists in your data
- ❌ Count and range rules — e.g. a `WalkForward:` parameter row needs one value per interval (dates − 1)
- ❌ Whether a date is real, which also depends on the `DateInput` / Date Display setting: `10/18/23` is valid under MDY and invalid under DMY
- ❌ Whether the strategy makes sense

Run `RealTest.exe -parse` (the validator does this for you when it can) to catch that second class.

## Exit Codes

- `0` - All files validated successfully
- `1` - One or more files failed validation or error occurred

## Integration

Use in CI/CD pipelines:

```bash
# Validate before commit
python validate_rts.py --file strategies/my_strategy.rts || exit 1

# Validate all strategies
python validate_rts.py --samples strategies/ || exit 1
```

On runners without RealTest installed, add **`--lark-only`** so the job does not depend on `RealTest.exe`.

## Grammar Details

`realtest.lark` is an **LALR(1)** grammar parsed with Lark's **contextual lexer**:

```python
Lark(grammar, start="start", parser="lalr", lexer="contextual",
     propagate_positions=False, maybe_placeholders=False)
```

The contextual lexer is load-bearing, not a speed knob. RealTest's value syntax
depends on the keyword that introduces it — `SaveTradesAs:` takes a raw path,
`Side:` one of three words, `Quantity:` a formula — and because Lark picks each
state's terminal set from the parser state, all three can have their own
terminal without colliding. The same mechanism makes `{...}` a format spec
directly after an item label and an ordinary inline comment everywhere else.
Two rules follow from it and are documented at the top of the grammar file:
no two terminals may share a pattern, and every word-like terminal above
priority 0 needs a boundary assertion.

What the grammar covers:

- **Sections**: `Notes`, `Settings` / `TestSettings` / `ScanSettings` / `OrderSettings` / `OptimizeSettings`, `Import`, `Parameters`, `Data`, `TestData`, `StratData`, `Library`, `Template`, `Strategy`, `Benchmark`, `StatsGroup`, `Combined`, `Scan`, `TestScan`, `Charts`, `Graphs`, `Results`, `Trades`, `WalkForward`, `Include` / `ScanInclude` / `TestInclude` / `OrdersInclude`, `Namespace`
- **Item keywords**, grouped by the value shape each takes, with the enum value sets spelled out
- **Formulas**: arithmetic, comparison, logical (`and` / `or` / `||` / `not` / `!`), `MOD` / `%`, the `BIT*` word operators, `^`, bar offsets `expr[N]`, function calls
- **References**: `$SPY`, `$$SPX`, `$%3MTCM`, `$&ES`, `@strategy`, `&cii` / `&99` / `&-1`, `~Weekly`, `?Symbol`
- **Breadth operators** and their grouping / calculation modifiers: `#Rank #ByEcon expr`, `#OnePerDate`, `#SlowCalc`, `#DataValueFile #DVFAlign #Fill`
- **Output format specs**: the legacy glyph form (`{#2}`, `{%}`, `{$-2}`, `{^2}`, `{|}`) and the named-attribute form (`{color: red, line: dashed}`)
- **Preprocessor**: `#define` / `#undef` / `#ifdef` / `#ifndef` / `#else` / `#endif` — every branch is validated, which is stricter than a run, where only the selected branch is parsed
- **Comments**: `//`, `/* ... */`, and `{ ... }` (which may span lines)

Keyword lists and enum value sets were verified against `realtest.exe -parse`.
Where the language reference and the executable disagree, the executable wins:
`&&` is documented but rejected, `OrderInclude:` does not exist (`OrdersInclude:`
does), and `LegacyMode:` is gone.

### Performance

The grammar parses the ~180 scripts shipped with RealTest in **about a second**
(~5 ms per file), so it is fast enough for editor-time validation. Cost is
linear in script size; the LALR table build (~0.25 s) is cached between runs.

### Known divergences from RealTest

Checked by differential testing — running both the grammar and
`realtest.exe -parse` over every script in `<SCRIPT_PATH>` (**0 disagreements
on syntax**) and over a second corpus of ~200 working strategies. What is left:

- **Conditional blocks.** The grammar validates *every* `#ifdef` / `#else`
  branch; a run parses only the selected one. A branch that is never taken can
  therefore hold a syntax error RealTest never reports.
- **A misspelled directive.** RealTest folds an unrecognized `#word` into the
  previous item's value rather than flagging it, so `#endi` can silently leave
  an `#ifdef` block unclosed. The grammar rejects it and names the six valid
  directives.
- **A commented-out `Notes:` header.** `//Notes: ...` at column 1 is not
  reliably treated as a comment by RealTest — it reads the line as an item
  named `notes` and usually rejects the file. The quirk is specific to `Notes`
  (`//Strategy:`, `//Data:`, `//atr:` all comment out normally) and to column 1
  (indent it and it behaves), and whether a given file actually breaks depends
  on what follows. Reproducing that is not worth it, so the grammar treats a
  comment as a comment and `validate_rts.py` emits a **warning** instead —
  advisory only, never changing the exit code.
- **Semantics.** Everything under "What It Doesn't Check" above — file
  existence, definition order, list-length rules, real calendar dates.

## Tests

`tests/` is a regression suite with two halves: `tests/valid/` must parse, and
`tests/invalid/` must be rejected. Both halves are also run through
`realtest.exe` when it is available, so the suite catches the two failures that
matter — rejecting a script RealTest accepts, and accepting one it rejects.

```bash
python tests/run_tests.py
python tests/run_tests.py --lark-only                    # no RealTest.exe needed
python tests/run_tests.py --corpus "C:\RealTest\Scripts" # also parse the shipped examples
```

## Reporting Issues

### 🐛 Found a Validation Error?

If you have a `.rts` file that **works correctly in RealTest** but **fails validation** with this tool, please help us improve the grammar!

**[Report a Validation Error →](../../issues/new?assignees=&labels=validation-error%2Cbug&template=validation_error.yml)**

When reporting, please include:
- ✅ Your complete `.rts` file (or relevant sections)
- ✅ The full error message from the validator
- ✅ Confirmation that it works in RealTest (and which version)

**Quick Tip:** You can run the validator with `--file` to get detailed error output for a single file:

```bash
python validate_rts.py --file your_strategy.rts
```

### ✨ Have a Suggestion?

Want to suggest a grammar improvement or report another type of issue?

**[Browse Issue Templates →](../../issues/new/choose)**

## Troubleshooting

### "Grammar file not found"

Ensure `realtest.lark` is in the same directory as `validate_rts.py`, or use:

```bash
python validate_rts.py --grammar path/to/realtest.lark
```

### "No module named 'lark'"

Install Lark:

```bash
pip install lark
```

### Parse Errors

If validation fails, the error message shows:
- Line and column number
- What was expected vs what was found
- Context around the error

Example:
```
Error: Unexpected token Token('NEWLINE', '\n') at line 23, column 5
Expected one of: COLON
```

Fix the syntax error at the indicated line and re-run.

**If you believe the error is incorrect** (i.e., your file works in RealTest), please [report it as a validation error](../../issues/new?assignees=&labels=validation-error%2Cbug&template=validation_error.yml)!

## Advanced Usage

### Embedding in Your Own Tools

```python
from validate_rts import load_grammar, validate_file
from pathlib import Path

# Load grammar once
parser = load_grammar('realtest.lark')

# Validate files
script = Path('my_strategy.rts')
success, error = validate_file(parser, script)

if success:
    print("Valid!")
else:
    print(f"Invalid: {error}")
```

### Batch Validation

```python
from pathlib import Path
from validate_rts import load_grammar, validate_file

parser = load_grammar('realtest.lark')

for script in Path('strategies').glob('*.rts'):
    success, error = validate_file(parser, script)
    if not success:
        print(f"FAIL: {script.name} - {error}")
```

## About RealTest

RealTest is a portfolio-level backtesting system for trading strategies. Learn more at the RealTest forum and documentation.

## License

This validator is provided as-is for use with RealTest scripts. The grammar represents the RealTest Script Language syntax.

## Version

Compatible with RealTest 2024+ syntax.

Last updated: November 2025

