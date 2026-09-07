# Quick start: Python environment

This repo’s **Python** surface is the `.rts` validator (`validate_rts.py`) and the grammar regression suite (`tests/run_tests.py`), both of which need **Python 3.7+** and **Lark**.

The VS Code extension under `vscode-rts/` uses **Node.js** separately; see [`vscode-rts/README.md`](vscode-rts/README.md) if you work on that.

**Recommended:** use [**uv**](https://docs.astral.sh/uv/) for installs and runs. **Alternative:** standard library `venv` + `pip` is below if you prefer not to install uv.

## 1. Install Python

- **Windows:** Install from [python.org](https://www.python.org/downloads/) or the Microsoft Store. Enable “Add Python to PATH” in the installer.
- **macOS / Linux:** Use your distro or `pyenv` / `asdf` so `python3` and `pip` are available.

Check:

```bash
python --version
```

or, on some systems:

```bash
python3 --version
```

Use the same command (`python` vs `python3`) in the **Alternative: venv + pip** section below. With **uv**, `uv run` will use a compatible interpreter.

## 2. Install uv (recommended)

See the [official install guide](https://docs.astral.sh/uv/getting-started/installation/). Examples:

- **Windows (PowerShell):** `irm https://astral.sh/uv/install.ps1 | iex`
- **macOS / Linux:** the `curl` one-liner on that page
- Or: `pip install uv` if you already have Python

## 3. Environment and dependencies (uv)

From the **repository root** (`rt-grammar/`).

### Persistent `.venv` (activate, then use `python`)

**Windows (PowerShell):**

```powershell
cd C:\path\to\rt-grammar
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

**macOS / Linux:**

```bash
cd /path/to/rt-grammar
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

You should see `(.venv)` in your shell prompt when the environment is active. This installs **Lark** (see [`requirements.txt`](requirements.txt)).

### One-off run (no activate)

This repo only needs **Lark**. You can run the validator without creating or activating a venv:

```bash
cd /path/to/rt-grammar
uv run --with lark python validate_rts.py --file example_strategy.rts
```

Use the same `uv run --with lark python validate_rts.py ...` prefix for other flags (`--samples`, `--grammar`, `--lark-only`, etc.).

By default the validator runs **Lark** and **RealTest.exe -parse** when `RealTest.exe` is found (see `REALTEST_EXE` / `--realtest-exe` in `validate_rts.py --help`). Without RealTest installed, it runs **Lark only** (one-line success output). Use **`--lark-only`** to skip RealTest even when it is installed.

**RealTest `-parse`:** a non-zero exit code means the script failed validation; RealTest often prints nothing to the console (known limitation), so rely on the exit code, not stderr/stdout.

## 4. Run the validator

At the repo root, with `realtest.lark` and `example_strategy.rts` present.

**If you use `uv run` (no venv activate):**

```bash
uv run --with lark python validate_rts.py --file example_strategy.rts
```

**If your uv-backed `.venv` is activated:**

```bash
python validate_rts.py --file example_strategy.rts
```

Expected when `RealTest.exe` is available: two lines, `Lark: OK (1 file)` and `RealTest -parse: OK (1 file)`. With `--lark-only` or no RealTest install: `Lark: OK (1 file)` only.

To validate a folder of `.rts` files:

```bash
python validate_rts.py --samples path\to\your\scripts
```

(or prefix with `uv run --with lark` if you are not using an activated venv.)

Use `--grammar` if your grammar file is not the default `realtest.lark`:

```bash
python validate_rts.py --file my.rts --grammar path\to\realtest.lark
```

## 5. Deactivate (only if you activated a venv)

```bash
deactivate
```

## Alternative: venv + pip (no uv)

From the **repository root**, create a venv so dependencies stay isolated:

**Windows (PowerShell):**

```powershell
cd C:\path\to\rt-grammar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
cd /path/to/rt-grammar
python3 -m venv .venv
source .venv/bin/activate
```

With the venv **activated**, install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Then run the validator as in **§4** using `python validate_rts.py ...`. When finished, `deactivate`.

## 5. Run the grammar tests

`tests/valid/` must parse and `tests/invalid/` must be rejected; both halves are
also cross-checked against `RealTest.exe` when it is installed.

```bash
python tests/run_tests.py
python tests/run_tests.py --lark-only
python tests/run_tests.py --corpus "C:\RealTest\Scripts"
```

## Troubleshooting

| Issue | What to try |
|--------|----------------|
| **uv:** `lark` missing with `uv run` | Use `uv run --with lark ...` or run `uv pip install -r requirements.txt` inside an activated `uv venv`. |
| `lark` import error (venv) | Confirm the venv is activated, then `pip install -r requirements.txt` again. |
| `pip` not found | Use `python -m pip install -r requirements.txt`. |
| Grammar file not found | Run commands from the repo root, or pass an absolute `--grammar` path. |
| Want grammar only (no RealTest) | Use `--lark-only`, or omit `RealTest.exe` (validator runs Lark only). |
| RealTest -parse fails but Lark passes | RealTest is stricter or differs from the grammar; fix the script or report a grammar issue. |

For full options and behavior, see [`README.md`](README.md).
