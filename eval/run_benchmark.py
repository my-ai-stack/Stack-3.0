#!/usr/bin/env python3
"""
Run HumanEval benchmark - fixed path version
"""

import sys
import os

# Add the eval directory to path
eval_dir = "/Users/walidsobhi/.openclaw/workspace/stack-3.0/stack-3.0-eval"
sys.path.insert(0, eval_dir)
os.chdir(eval_dir)

# Now import and run
from benchmarks.human_eval import HumanEval

print("=" * 50)
print("Running HumanEval Benchmark (Stub Mode)")
print("=" * 50)

# Run with 5 problems in stub mode
benchmark = HumanEval(max_problems=5)
results = benchmark.evaluate()

print("\n" + "=" * 50)
print("RESULTS:")
print("=" * 50)
print(f"Total: {results['total_cases']}")
print(f"Passed: {results['pass_at_1']}")
print(f"Accuracy: {results['accuracy']*100:.1f}%")
print(f"Model: {results['model']}")
print("=" * 50)