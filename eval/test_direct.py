#!/usr/bin/env python3
"""Test runner using direct script execution"""
import subprocess
import sys

script = "/Users/walidsobhi/.openclaw/workspace/stack-3.0/stack-3.0-eval/human_eval.py"

print("="*50)
print("Running HumanEval directly")
print("="*50)

# Run with limited problems for quick test
result = subprocess.run(
    [sys.executable, script, "--model", "test-run", "--timeout", "5"],
    capture_output=True,
    text=True,
    timeout=60
)

print("STDOUT:", result.stdout[:2000] if result.stdout else "(empty)")
print("STDERR:", result.stderr[:500] if result.stderr else "(empty)")
print("Return code:", result.returncode)
print("="*50)