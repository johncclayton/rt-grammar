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

The validator checks that your RealTest script:

**Lark (always):**

- ✅ Has valid syntax according to the grammar
- ✅ All sections (Import, Settings, Data, Strategy, etc.) are properly formatted
- ✅ Expressions, identifiers, and operators follow RealTest rules
- ✅ Comments are correctly placed
- ✅ String literals, numbers, and symbols are valid

**RealTest -parse (when `RealTest.exe` is found, unless `--lark-only`):**

- ✅ The installed RealTest parser accepts the script (same as running `RealTest.exe -parse` on the file)
- ℹ️ RealTest signals failure with a **non-zero exit code**; it often prints **nothing** to stdout/stderr (known limitation). The validator treats the exit code as authoritative.

## What It Doesn't Check

Neither Lark nor RealTest -parse checks:
- ❌ Whether variable names conflict with functions (use semantic_validator.py)
- ❌ Whether data files exist
- ❌ Whether strategies make logical sense
- ❌ Whether parameters are in reasonable ranges

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

The included `realtest.lark` grammar defines the complete RealTest Script Language including:

- **Sections**: Import, Settings, Data, Strategy, Parameters, etc.
- **Expressions**: Arithmetic, logical, comparisons, function calls
- **Identifiers**: Variables, symbols ($SPY), watchlists (&MyList), parameters (?pos)
- **Literals**: Numbers, strings, dates
- **Operators**: +, -, *, /, ^, and, or, not, >, <, =, etc.
- **Functions**: MA(), RSI(), ATR(), Extern(), etc.
- **Comments**: // single-line and /* multi-line */

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

