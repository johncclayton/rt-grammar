# Contributing to RealTest Grammar Validator

Thank you for your interest in contributing! This project aims to maintain an accurate Lark grammar for RealTest Script Language.

## 🐛 Reporting Validation Issues

The most valuable contribution you can make is reporting `.rts` files that fail validation but work correctly in RealTest.

### How to Report

1. **Use the Issue Template**: [Report a Validation Error](../../issues/new?assignees=&labels=validation-error%2Cbug&template=validation_error.yml)

2. **Include These Details**:
   - Complete `.rts` file content (or at minimum, the relevant sections)
   - Full error message from running `python validate_rts.py --file your_file.rts`
   - RealTest version where the file works
   - Any additional context about the syntax being used

3. **Example of a Good Report**:

```
Title: [Validation Error]: Strategy with Extern() function fails

RTS File:
---
Strategy: Test
Data
  Bar: Daily
End
Code
  value = Extern("MyIndicator", Close)
End
---

Error Message:
---
[FAIL] at line 5, column 11
Unexpected token: "MyIndicator"
Expected: identifier
---

Additional Context:
This file runs successfully in RealTest 2024.3. The Extern() function
appears to need support for string literals as the first parameter.
```

## ✨ Suggesting Enhancements

Have an idea for improving the grammar or validator?

1. **Check Existing Issues**: Search [existing issues](../../issues) to avoid duplicates
2. **Use the Enhancement Template**: [Suggest a Grammar Enhancement](../../issues/new?assignees=&labels=enhancement%2Cgrammar&template=grammar_improvement.yml)
3. **Provide Examples**: Include sample RealTest syntax you'd like to see supported

## 🔧 Contributing Code

### Grammar Changes

If you'd like to contribute grammar improvements:

1. **Fork the Repository**
2. **Modify `realtest.lark`**: Add or fix grammar rules
3. **Test Your Changes**:
   ```bash
   # Test with example file
   python validate_rts.py --file example_strategy.rts
   
   # Test with your own files
   python validate_rts.py --file path/to/test.rts
   ```
4. **Submit a Pull Request** with:
   - Description of what syntax is now supported
   - Example `.rts` file that demonstrates the fix
   - Reference to the issue it addresses (if applicable)

### Validator Improvements

For improvements to `validate_rts.py`:

1. **Ensure Backward Compatibility**: Don't break existing functionality
2. **Keep Dependencies Minimal**: Only `lark` should be required
3. **Test on Multiple Platforms**: Windows, Linux, and macOS if possible
4. **Update README**: Document any new features or options

## 📋 Pull Request Guidelines

- **One Feature Per PR**: Keep changes focused
- **Clear Description**: Explain what and why
- **Reference Issues**: Link to related issues
- **Test**: Verify your changes work with the example file

## 🤔 Questions?

- **Grammar Questions**: Check the [RealTest documentation](https://www.realtest.com/)
- **Tool Usage**: See the [README](README.md)
- **Other Questions**: Open a [discussion](../../discussions) or issue

## Code of Conduct

- Be respectful and constructive
- Focus on improving the grammar accuracy
- Help others by sharing working examples
- Remember: we're all trying to make this tool better!

## Recognition

Contributors who report validation errors or submit grammar fixes will be acknowledged in the project. Your help in making this grammar more complete is greatly appreciated!

---

**Most Important**: If you have `.rts` files that don't validate, please report them! Each report helps make the grammar more accurate for everyone.

