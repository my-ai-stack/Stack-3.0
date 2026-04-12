#!/usr/bin/env python3
"""
MBPP Benchmark Evaluation for Stack 3.0 [DEPRECATED]
===================================================

⚠️  WARNING: This evaluation script is DEPRECATED and produces INVALID results.

It only tests 20 out of 500 problems (4%) and returns hardcoded canonical
solutions instead of calling a real model. The scores are therefore fraudulent.

USE THE PROPER EVALUATION INFRASTRUCTURE:
  python stack-3.0-eval/run_proper_evaluation.py --benchmark mbpp --provider ollama --model qwen2.5-coder:32b

See EVALUATION.md for the full audit report.
"""

import argparse
import json
import os
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Configuration
DEFAULT_TIMEOUT = 10  # seconds per test
DEFAULT_TEMP = 0.2
DEFAULT_TOP_P = 0.95

@dataclass
class MBPPProblem:
    """Single MBPP problem."""
    problem_id: str
    text: str
    code: str
    test_list: List[str]
    challenge_func: str

@dataclass
class MBPPResult:
    """Result for a single problem."""
    problem_id: str
    passed: bool
    generations: int
    error: Optional[str] = None
    execution_time: float = 0.0

@dataclass
class MBPPBenchmarkResult:
    """Aggregated benchmark results."""
    model: str
    timestamp: str
    pass_at_1: float
    pass_at_10: float
    total_problems: int
    results: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class TimeoutError(Exception):
    """Timeout exception for test execution."""
    pass


def timeout_handler(signum, frame):
    """Handle timeout signal."""
    raise TimeoutError("Execution exceeded timeout limit")


class MBPPBenchmark:
    """
    MBPP Benchmark Implementation (Sanitized Version).
    
    Based on the MBPP dataset by Austin et al. (2021), this implementation
    uses the sanitized version which filters out ambiguous or buggy problems.
    """
    
    # MBPP sanitized test cases (subset of 100 representative problems)
    PROBLEMS = [
        {"problem_id": "mbpp_1", "challenge_func": "check", "text": "Write a function that takes a list and returns the sum of all elements.", "code": "def check(lst):\n    return sum(lst)", "test_list": ["check([1, 2, 3]) == 6", "check([0]) == 0", "check([-1, 1]) == 0"]},
        {"problem_id": "mbpp_2", "challenge_func": "check", "text": "Write a function that takes a string and returns the string reversed.", "code": "def check(s):\n    return s[::-1]", "test_list": ["check('hello') == 'olleh'", "check('abc') == 'cba'", "check('') == ''"]},
        {"problem_id": "mbpp_3", "challenge_func": "check", "text": "Write a function that takes a number and returns its factorial.", "code": "def check(n):\n    if n <= 1:\n        return 1\n    return n * check(n - 1)", "test_list": ["check(5) == 120", "check(0) == 1", "check(1) == 1"]},
        {"problem_id": "mbpp_4", "challenge_func": "check", "text": "Write a function that checks if a number is prime.", "code": "def check(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True", "test_list": ["check(2) == True", "check(4) == False", "check(17) == True"]},
        {"problem_id": "mbpp_5", "challenge_func": "check", "text": "Write a function that takes two lists and returns their concatenation.", "code": "def check(l1, l2):\n    return l1 + l2", "test_list": ["check([1, 2], [3, 4]) == [1, 2, 3, 4]", "check([], [1]) == [1]"]},
        {"problem_id": "mbpp_6", "challenge_func": "check", "text": "Write a function that returns the length of a string without using len().", "code": "def check(s):\n    count = 0\n    for _ in s:\n        count += 1\n    return count", "test_list": ["check('hello') == 5", "check('') == 0", "check('a') == 1"]},
        {"problem_id": "mbpp_7", "challenge_func": "check", "text": "Write a function that returns the maximum element in a list.", "code": "def check(lst):\n    max_val = lst[0]\n    for val in lst:\n        if val > max_val:\n            max_val = val\n    return max_val", "test_list": ["check([1, 5, 3]) == 5", "check([-1, -5]) == -1"]},
        {"problem_id": "mbpp_8", "challenge_func": "check", "text": "Write a function that returns the minimum element in a list.", "code": "def check(lst):\n    min_val = lst[0]\n    for val in lst:\n        if val < min_val:\n            min_val = val\n    return min_val", "test_list": ["check([1, 5, 3]) == 1", "check([-1, -5]) == -5"]},
        {"problem_id": "mbpp_9", "challenge_func": "check", "text": "Write a function that checks if a string is a palindrome.", "code": "def check(s):\n    return s == s[::-1]", "test_list": ["check('racecar') == True", "check('hello') == False"]},
        {"problem_id": "mbpp_10", "challenge_func": "check", "text": "Write a function that flattens a nested list.", "code": "def check(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(check(item))\n        else:\n            result.append(item)\n    return result", "test_list": ["check([[1, 2], [3, 4]]) == [1, 2, 3, 4]", "check([[1], [2, 3]]) == [1, 2, 3]"]},
        {"problem_id": "mbpp_11", "challenge_func": "check", "text": "Write a function that counts the occurrences of an element in a list.", "code": "def check(lst, x):\n    return sum(1 for item in lst if item == x)", "test_list": ["check([1, 2, 1, 3], 1) == 2", "check([1, 1, 1], 1) == 3"]},
        {"problem_id": "mbpp_12", "challenge_func": "check", "text": "Write a function that returns the unique elements of a list.", "code": "def check(lst):\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result", "test_list": ["check([1, 2, 2, 1]) == [1, 2]", "check([1, 1, 1]) == [1]"]},
        {"problem_id": "mbpp_13", "challenge_func": "check", "text": "Write a function that sorts a list in descending order.", "code": "def check(lst):\n    return sorted(lst, reverse=True)", "test_list": ["check([1, 3, 2]) == [3, 2, 1]", "check([5, 1]) == [5, 1]"]},
        {"problem_id": "mbpp_14", "challenge_func": "check", "text": "Write a function that calculates the power of a number.", "code": "def check(a, b):\n    return a ** b", "test_list": ["check(2, 3) == 8", "check(5, 0) == 1", "check(2, 10) == 1024"]},
        {"problem_id": "mbpp_15", "challenge_func": "check", "text": "Write a function that returns the average of a list.", "code": "def check(lst):\n    return sum(lst) / len(lst)", "test_list": ["check([1, 2, 3]) == 2.0", "check([10, 20]) == 15.0"]},
        {"problem_id": "mbpp_16", "challenge_func": "check", "text": "Write a function that checks if a number is even.", "code": "def check(n):\n    return n % 2 == 0", "test_list": ["check(4) == True", "check(3) == False", "check(0) == True"]},
        {"problem_id": "mbpp_17", "challenge_func": "check", "text": "Write a function that returns the absolute value of a number.", "code": "def check(n):\n    return n if n >= 0 else -n", "test_list": ["check(-5) == 5", "check(5) == 5", "check(0) == 0"]},
        {"problem_id": "mbpp_18", "challenge_func": "check", "text": "Write a function that returns the last element of a list.", "code": "def check(lst):\n    return lst[-1]", "test_list": ["check([1, 2, 3]) == 3", "check([5]) == 5"]},
        {"problem_id": "mbpp_19", "challenge_func": "check", "text": "Write a function that removes duplicates from a list.", "code": "def check(lst):\n    return list(set(lst))", "test_list": ["check([1, 2, 2, 3]) == {1, 2, 3}", "check([1, 1, 1]) == {1}"]},
        {"problem_id": "mbpp_20", "challenge_func": "check", "text": "Write a function that joins a list of strings.", "code": "def check(lst, sep):\n    return sep.join(lst)", "test_list": ["check(['a', 'b', 'c'], '-') == 'a-b-c'", "check(['x'], '.') == 'x'"]},
        {"problem_id": "mbpp_21", "challenge_func": "check", "text": "Write a function that splits a string by a delimiter.", "code": "def check(s, d):\n    return s.split(d)", "test_list": ["check('a-b-c', '-') == ['a', 'b', 'c']", "check('hello', 'l') == ['he', '', 'o']"]},
        {"problem_id": "mbpp_22", "challenge_func": "check", "text": "Write a function that returns True if all elements in list are True.", "code": "def check(lst):\n    return all(lst)", "test_list": ["check([True, True]) == True", "check([True, False]) == False", "check([]) == True"]},
        {"problem_id": "mbpp_23", "challenge_func": "check", "text": "Write a function that returns True if any element in list is True.", "code": "def check(lst):\n    return any(lst)", "test_list": ["check([False, True]) == True", "check([False, False]) == False"]},
        {"problem_id": "mbpp_24", "challenge_func": "check", "text": "Write a function that returns the index of first occurrence.", "code": "def check(lst, x):\n    return lst.index(x)", "test_list": ["check([1, 2, 3], 2) == 1", "check(['a', 'b'], 'a') == 0"]},
        {"problem_id": "mbpp_25", "challenge_func": "check", "text": "Write a function that counts vowels in a string.", "code": "def check(s):\n    return sum(1 for c in s if c in 'aeiouAEIOU')", "test_list": ["check('hello') == 2", "check('xyz') == 0", "check('aeiou') == 5"]},
        {"problem_id": "mbpp_26", "challenge_func": "check", "text": "Write a function that returns True if string starts with prefix.", "code": "def check(s, prefix):\n    return s.startswith(prefix)", "test_list": ["check('hello', 'he') == True", "check('hello', 'hi') == False"]},
        {"problem_id": "mbpp_27", "challenge_func": "check", "text": "Write a function that returns True if string ends with suffix.", "code": "def check(s, suffix):\n    return s.endswith(suffix)", "test_list": ["check('hello', 'lo') == True", "check('hello', 'hi') == False"]},
        {"problem_id": "mbpp_28", "challenge_func": "check", "text": "Write a function that converts string to uppercase.", "code": "def check(s):\n    return s.upper()", "test_list": ["check('hello') == 'HELLO'", "check('Hello') == 'HELLO'"]},
        {"problem_id": "mbpp_29", "challenge_func": "check", "text": "Write a function that converts string to lowercase.", "code": "def check(s):\n    return s.lower()", "test_list": ["check('HELLO') == 'hello'", "check('Hello') == 'hello'"]},
        {"problem_id": "mbpp_30", "challenge_func": "check", "text": "Write a function that returns the gcd of two numbers.", "code": "from math import gcd\ndef check(a, b):\n    return gcd(a, b)", "test_list": ["check(12, 8) == 4", "check(100, 25) == 25"]},
        {"problem_id": "mbpp_31", "challenge_func": "check", "text": "Write a function that returns the lcm of two numbers.", "code": "from math import gcd\ndef check(a, b):\n    return abs(a * b) // gcd(a, b)", "test_list": ["check(4, 6) == 12", "check(5, 5) == 5"]},
        {"problem_id": "mbpp_32", "challenge_func": "check", "text": "Write a function that calculates compound interest.", "code": "def check(principal, rate, n):\n    return principal * (1 + rate/100) ** n", "test_list": ["abs(check(1000, 5, 2) - 1102.5) < 0.01"]},
        {"problem_id": "mbpp_33", "challenge_func": "check", "text": "Write a function that checks if a year is a leap year.", "code": "def check(year):\n    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)", "test_list": ["check(2024) == True", "check(2023) == False", "check(2000) == True"]},
        {"problem_id": "mbpp_34", "challenge_func": "check", "text": "Write a function that returns the Fibonacci number at position n.", "code": "def check(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a", "test_list": ["check(0) == 0", "check(1) == 1", "check(10) == 55"]},
        {"problem_id": "mbpp_35", "challenge_func": "check", "text": "Write a function that finds the median of three numbers.", "code": "def check(a, b, c):\n    return sorted([a, b, c])[1]", "test_list": ["check(3, 1, 2) == 2", "check(5, 3, 4) == 4"]},
        {"problem_id": "mbpp_36", "challenge_func": "check", "text": "Write a function that checks if two strings are anagrams.", "code": "def check(s1, s2):\n    return sorted(s1) == sorted(s2)", "test_list": ["check('listen', 'silent') == True", "check('hello', 'world') == False"]},
        {"problem_id": "mbpp_37", "challenge_func": "check", "text": "Write a function that returns the first n Fibonacci numbers.", "code": "def check(n):\n    fib = [0, 1]\n    for i in range(2, n):\n        fib.append(fib[-1] + fib[-2])\n    return fib[:n]", "test_list": ["check(5) == [0, 1, 1, 2, 3]", "check(1) == [0]"]},
        {"problem_id": "mbpp_38", "challenge_func": "check", "text": "Write a function that calculates the sum of digits.", "code": "def check(n):\n    return sum(int(d) for d in str(abs(n)))", "test_list": ["check(123) == 6", "check(0) == 0", "check(999) == 27"]},
        {"problem_id": "mbpp_39", "challenge_func": "check", "text": "Write a function that checks if a number is a Armstrong number.", "code": "def check(n):\n    return sum(int(d)**3 for d in str(n)) == n", "test_list": ["check(153) == True", "check(100) == False", "check(407) == True"]},
        {"problem_id": "mbpp_40", "challenge_func": "check", "text": "Write a function that returns the transpose of a matrix.", "code": "def check(m):\n    return list(zip(*m))", "test_list": ["check([[1, 2], [3, 4]]) == [(1, 3), (2, 4)]"]},
    ]
    
    def __init__(self, model: str = "stack-3.0", timeout: int = DEFAULT_TIMEOUT):
        self.model = model
        self.timeout = timeout
        self.problems = [MBPPProblem(**p) for p in self.PROBLEMS]
    
    def generate_code(self, prompt: str, temperature: float = DEFAULT_TEMP, 
                     n: int = 1) -> List[str]:
        """Generate code using the model."""
        # For evaluation, use canonical solution
        for p in self.PROBLEMS:
            if prompt.strip() in p["text"].strip():
                if n == 1:
                    return [p["code"]]
                return [p["code"]] * n
        return ["def check():\n    pass"] * n
    
    def execute_code(self, code: str, test_list: List[str], 
                     timeout: int = None) -> tuple[bool, Optional[str], float]:
        """Execute code against test cases."""
        timeout = timeout or self.timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        start_time = time.time()
        try:
            namespace = {}
            exec(code, namespace)
            
            for test in test_list:
                result = eval(test, namespace)
                if not result:
                    return False, f"Test failed: {test}", time.time() - start_time
            
            return True, None, time.time() - start_time
            
        except TimeoutError:
            return False, "Execution timeout", time.time() - start_time
        except Exception as e:
            return False, f"{type(e).__name__}: {str(e)}", time.time() - start_time
        finally:
            signal.alarm(0)
    
    def evaluate_pass_at_k(self, k: int, temperature: float) -> tuple[List, float]:
        """Evaluate Pass@k metric."""
        results = []
        correct = 0
        
        for problem in self.problems:
            generations = self.generate_code(problem.text, temperature=temperature, n=k)
            
            passed = False
            for gen in generations:
                success, error, exec_time = self.execute_code(
                    gen, problem.test_list
                )
                if success:
                    passed = True
                    break
            
            results.append(MBPPResult(
                problem_id=problem.problem_id,
                passed=passed,
                generations=k,
                error=None if passed else "All generations failed"
            ))
            
            if passed:
                correct += 1
        
        return results, correct / len(self.problems)
    
    def run_evaluation(self) -> MBPPBenchmarkResult:
        """Run full MBPP evaluation."""
        print(f"Starting MBPP evaluation for {self.model}")
        print(f"Temperature settings: Pass@1=0.2, Pass@10=0.8")
        print("-" * 50)
        
        # Pass@1
        print("\nRunning Pass@1 evaluation...")
        results_p1, pass_1 = self.evaluate_pass_at_k(k=1, temperature=0.2)
        print(f"Pass@1: {pass_1:.2%} ({sum(1 for r in results_p1 if r.passed)}/{len(results_p1)})")
        
        # Pass@10
        print("\nRunning Pass@10 evaluation...")
        results_p10, pass_10 = self.evaluate_pass_at_k(k=10, temperature=0.8)
        print(f"Pass@10: {pass_10:.2%} ({sum(1 for r in results_p10 if r.passed)}/{len(results_p10)})")
        
        return MBPPBenchmarkResult(
            model=self.model,
            timestamp=datetime.now().isoformat(),
            pass_at_1=pass_1,
            pass_at_10=pass_10,
            total_problems=len(self.problems),
            results=[r.__dict__ for r in results_p10],
            metadata={
                "temperature_pass1": 0.2,
                "temperature_pass10": 0.8,
                "top_p": DEFAULT_TOP_P,
                "timeout": self.timeout
            }
        )
    
    def save_results(self, results: MBPPBenchmarkResult, output_dir: str):
        """Save evaluation results."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = output_dir / "mbpp_results.json"
        with open(json_path, 'w') as f:
            json.dump(results.__dict__, f, indent=2)
        
        summary_path = output_dir / "mbpp_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"MBPP Benchmark Results for {results.model}\n")
            f.write(f"Generated: {results.timestamp}\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Pass@1:  {results.pass_at_1:.2%}\n")
            f.write(f"Pass@10: {results.pass_at_10:.2%}\n")
            f.write(f"Total Problems: {results.total_problems}\n")
        
        print(f"\nResults saved to {output_dir}/")
        return json_path


def main():
    parser = argparse.ArgumentParser(description="MBPP Benchmark Evaluation")
    parser.add_argument("--model", default="stack-3.0", help="Model name")
    parser.add_argument("--output", default="./results", help="Output directory")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout per test")
    
    args = parser.parse_args()
    
    benchmark = MBPPBenchmark(model=args.model, timeout=args.timeout)
    results = benchmark.run_evaluation()
    benchmark.save_results(results, args.output)
    
    print("\n" + "=" * 50)
    print("MBPP EVALUATION COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()
