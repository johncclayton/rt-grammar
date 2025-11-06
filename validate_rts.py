#!/usr/bin/env python3
"""
RealTest Script Validator

This script validates all .rts files in the samples/ directory using the realtest.lark grammar.
It will report parsing errors to help iteratively refine the grammar.
"""

import sys
import json
from pathlib import Path
from lark import Lark
from lark.exceptions import ParseError, LexError, UnexpectedInput
import argparse


def load_grammar(grammar_path_str="lark/realtest.lark"):
    """Load the Lark grammar from the specified path"""
    grammar_path = Path(grammar_path_str)
    if not grammar_path.exists():
        print(f"Error: Grammar file not found at {grammar_path}")
        sys.exit(1)
    
    try:
        with open(grammar_path, 'r', encoding='utf-8') as f:
            grammar_content = f.read()
        
        parser = Lark(
            grammar_content,
            start='start',
            parser='earley',
            lexer='dynamic',
        )
        print(f"[OK] Grammar loaded successfully from {grammar_path}")
        return parser
    except Exception as e:
        print(f"Error loading grammar: {e}")
        sys.exit(1)


def find_rts_files(samples_dir: Path):
    """Find all .rts files in the provided samples directory"""
    if not samples_dir.exists():
        print(f"Error: Samples directory not found at {samples_dir}")
        sys.exit(1)

    rts_files = list(samples_dir.glob("*.rts"))
    if not rts_files:
        print(f"No .rts files found in {samples_dir}")
        sys.exit(1)

    return sorted(rts_files, key=lambda p: p.name.lower())


def validate_file(parser, file_path: Path):
    """Validate a single .rts file"""
    try:
        content = file_path.read_text(encoding='utf-8')
        parser.parse(content)
        return True, None
    except (ParseError, LexError, UnexpectedInput) as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


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
        help="Path to samples directory (default: samples)"
    )
    
    args = parser.parse_args()
    
    # Header
    print("RealTest Script Validator")
    print("=" * 50)
    
    # Load grammar
    lark_parser = load_grammar(args.grammar)
    
    # Determine what to validate
    if args.file:
        # Single file mode
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        
        print(f"Found 1 file to validate: {file_path.name}")
        files_to_validate = [file_path]
        samples_dir = file_path.parent
    else:
        # Multi-file mode (all samples)
        samples_dir = Path(args.samples)
        files_to_validate = find_rts_files(samples_dir)
        print(f"Found {len(files_to_validate)} file(s) to validate")
    
    # Validate files
    print("\nValidating files...")
    print("-" * 50)
    
    results = {}
    for i, file_path in enumerate(files_to_validate, 1):
        success, error = validate_file(lark_parser, file_path)
        
        status = "[PASS]" if success else "[FAIL]"
        print(f"[{i:3d}/{len(files_to_validate)}] {file_path.name:40s} {status}")
        
        if not success and args.file:
            # Show error details for single file
            print(f"\nError details:\n{error}\n")
        
        results[file_path.name] = "pass" if success else "fail"
    
    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v == "pass")
    failed = total - passed
    
    print(f"Total files: {total}")
    print(f"Successful: {passed} ({100.0 * passed / total:.1f}%)")
    print(f"Failed: {failed} ({100.0 * failed / total:.1f}%)")
    
    # Save status if validating samples directory
    if not args.file:
        data_file = samples_dir.parent / 'data.json'
        save_status_data(data_file, results)
        print(f"\nUpdated status written to {data_file.name}")
    
    # Exit code
    if failed == 0:
        print("\n[SUCCESS] All files parsed successfully!")
        sys.exit(0)
    else:
        print(f"\n[FAIL] {failed} file(s) failed validation")
        sys.exit(1)


if __name__ == "__main__":
    main()

