#!/usr/bin/env python3
"""
Test all scripts for syntax errors before running
"""

import py_compile
import os
import sys

def test_script(filepath):
    """Test a Python script for syntax errors"""
    try:
        py_compile.compile(filepath, doraise=True)
        return True, "OK"
    except py_compile.PyCompileError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    """Test all provisioning scripts"""
    print("=" * 60)
    print("Testing Scripts for Syntax Errors")
    print("=" * 60)

    scripts_dir = os.path.dirname(os.path.abspath(__file__))

    # Scripts to test
    scripts = [
        "provision_deployment_vm.py",
        "validate_vm.py",
        "cleanup_vm.py"
    ]

    all_ok = True

    for script in scripts:
        filepath = os.path.join(scripts_dir, script)
        if os.path.exists(filepath):
            print(f"\nTesting: {script}")
            success, message = test_script(filepath)

            if success:
                print(f"  [OK] Syntax is valid")
            else:
                print(f"  [ERROR] Syntax error found:")
                print(f"  {message}")
                all_ok = False
        else:
            print(f"\nSkipping: {script} (not found)")

    print("\n" + "=" * 60)
    if all_ok:
        print("SUCCESS: All scripts passed syntax check")
        print("Safe to run provisioning scripts")
    else:
        print("FAILED: Some scripts have syntax errors")
        print("Fix the errors before running")
    print("=" * 60)

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())