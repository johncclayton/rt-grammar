# RealTest Script Validator - Standalone Package

Validate RealTest `.rts` script files using the RealTest Lark grammar.

## What's Included

- `validate_rts.py` - Standalone validator script
- `realtest.lark` - Complete RealTest language grammar
- `example_strategy.rts` - Sample RealTest script for testing
- `README.md` - This file

## Requirements

**Python 3.7+** with one package:

```bash
pip install lark
```

That's it! No other dependencies.

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
```

### Examples

**Validate single script:**
```bash
python validate_rts.py --file my_strategy.rts

# Output:
# [OK] Grammar loaded successfully
# Found 1 file to validate: my_strategy.rts
# [  1/1] my_strategy.rts                          [PASS]
# [SUCCESS] All files parsed successfully!
```

**Validate directory:**
```bash
python validate_rts.py --samples my_strategies/

# Output:
# [OK] Grammar loaded successfully
# Found 25 files to validate
# [  1/25] strategy1.rts                          [PASS]
# [  2/25] strategy2.rts                          [PASS]
# ...
# Total: 25, Successful: 23 (92.0%), Failed: 2 (8.0%)
```

**With custom grammar:**
```bash
python validate_rts.py \
  --file script.rts \
  --grammar /path/to/my_realtest.lark
```

## What It Validates

The validator checks that your RealTest script:
- ✅ Has valid syntax according to the grammar
- ✅ All sections (Import, Settings, Data, Strategy, etc.) are properly formatted
- ✅ Expressions, identifiers, and operators follow RealTest rules
- ✅ Comments are correctly placed
- ✅ String literals, numbers, and symbols are valid

## What It Doesn't Check

This is **grammar validation only**. It doesn't check:
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

## Grammar Details

The included `realtest.lark` grammar defines the complete RealTest Script Language including:

- **Sections**: Import, Settings, Data, Strategy, Parameters, etc.
- **Expressions**: Arithmetic, logical, comparisons, function calls
- **Identifiers**: Variables, symbols ($SPY), watchlists (&MyList), parameters (?pos)
- **Literals**: Numbers, strings, dates
- **Operators**: +, -, *, /, ^, and, or, not, >, <, =, etc.
- **Functions**: MA(), RSI(), ATR(), Extern(), etc.
- **Comments**: // single-line and /* multi-line */

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

