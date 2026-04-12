#!/usr/bin/env python3
"""
Test HumanEval benchmark in stub mode (no model required)
Tests that the evaluation pipeline works correctly.
"""

import sys
sys.path.insert(0, '/Users/walidsobhi/.openclaw/workspace/stack-3.0/stack-3.0-eval')

from benchmarks.human_eval import HumanEval

def test_humaneval_stub():
    """Test HumanEval with stub mode (canonical solutions)."""
    print("=" * 50)
    print("Testing HumanEval Pipeline (Stub Mode)")
    print("=" * 50)
    
    # Create benchmark - will use stub mode since no model configured
    benchmark = HumanEval(max_problems=5)
    
    # Run evaluation (will use canonical solutions in stub mode)
    results = benchmark.evaluate()
    
    print("\n" + "=" * 50)
    print("RESULTS:")
    print("=" * 50)
    print(f"Total problems: {results['total_cases']}")
    print(f"Passed: {results['pass_at_1']}")
    print(f"Pass rate: {results['accuracy']*100:.1f}%")
    print(f"Model: {results['model']}")
    print("=" * 50)
    
    return results

if __name__ == "__main__":
    try:
        results = test_humaneval_stub()
        print("\n✅ Pipeline test completed successfully!")
    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)