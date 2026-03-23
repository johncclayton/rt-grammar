# RealTest Script — VS Code syntax highlighting

TextMate grammar for **RealTest** `.rts` files, kept in line with [`../realtest.lark`](../realtest.lark) (sections, comments, literals, keywords).

## Develop in VS Code

1. Open the **`vscode-rts`** folder (or the repo root) in VS Code.
2. Run **Run → Start Debugging** (`F5`) to open an Extension Development Host with this grammar loaded.
3. Open any `.rts` file to check highlighting.

`launch.json` lives under `.vscode/` in this folder.

## Package a VSIX

```bash
cd vscode-rts
npm install
npx vsce package
```

Install the generated `.vsix` in VS Code: **Extensions → … → Install from VSIX…**

## Publish (optional)

Publishing to the Marketplace needs a [publisher](https://code.visualstudio.com/api/working-with-extensions/publishing-extension#create-a-publisher) and `npx vsce publish`. This repo’s CI can build a VSIX on release; see the workflow under `.github/workflows/`.

## Python validator

Grammar validation uses Python + Lark in the parent folder; see [`../QUICKSTART.md`](../QUICKSTART.md).
