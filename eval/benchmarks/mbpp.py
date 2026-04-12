"""
MBPP (Mostly Basic Python Problems) benchmark implementation
Real implementation with model API integration.
"""

import os
import re
import json
import signal
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from model_client import create_model_client, BaseModelClient, ChatMessage


@dataclass
class MBPPProblem:
    """MBPP problem structure."""
    task_id: int
    description: str
    prompt: str
    code: str  # Canonical solution
    test: str  # Test code
    test_import: List[str]


@dataclass
class MBPPResult:
    """Result for a single problem."""
    task_id: int
    passed: bool
    generated_code: str
    error: Optional[str] = None
    execution_time: float = 0.0


class TimeoutException(Exception):
    """Timeout during code execution."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutException("Code execution timed out")


class MBPP:
    """MBPP Benchmark with real model integration."""

    # MBPP dataset (first 40 problems for quick testing)
    # In production, load full dataset from file
    PROBLEMS = [
        {
            "task_id": 1,
            "description": "Return sum of a list",
            "prompt": "Write a python function sum_list(lst) that returns the sum of all elements in a list.",
            "canonical": "def sum_list(lst):\n    return sum(lst)",
            "test": "assert sum_list([1, 2, 3]) == 6\nassert sum_list([]) == 0",
            "imports": []
        },
        {
            "task_id": 2,
            "description": "Return maximum element",
            "prompt": "Write a python function max_element(lst) that returns the maximum element in a list.",
            "canonical": "def max_element(lst):\n    return max(lst) if lst else None",
            "test": "assert max_element([1, 5, 3]) == 5\nassert max_element([0]) == 0",
            "imports": []
        },
        {
            "task_id": 3,
            "description": "Return reverse of string",
            "prompt": "Write a python function reverse_string(s) that returns the reverse of a string.",
            "canonical": "def reverse_string(s):\n    return s[::-1]",
            "test": "assert reverse_string('hello') == 'olleh'\nassert reverse_string('') == ''",
            "imports": []
        },
        {
            "task_id": 4,
            "description": "Check if string is palindrome",
            "prompt": "Write a python function is_palindrome(s) that returns True if a string is a palindrome, False otherwise.",
            "canonical": "def is_palindrome(s):\n    return s == s[::-1]",
            "test": "assert is_palindrome('racecar') == True\nassert is_palindrome('hello') == False",
            "imports": []
        },
        {
            "task_id": 5,
            "description": "Return factorial",
            "prompt": "Write a python function factorial(n) that returns the factorial of n.",
            "canonical": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
            "test": "assert factorial(5) == 120\nassert factorial(0) == 1",
            "imports": []
        },
        {
            "task_id": 6,
            "description": "Return Fibonacci number",
            "prompt": "Write a python function fibonacci(n) that returns the nth Fibonacci number.",
            "canonical": "def fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(n-1):\n        a, b = b, a + b\n    return b",
            "test": "assert fibonacci(10) == 55\nassert fibonacci(0) == 0\nassert fibonacci(1) == 1",
            "imports": []
        },
        {
            "task_id": 7,
            "description": "Count vowels in string",
            "prompt": "Write a python function count_vowels(s) that returns the count of vowels in a string.",
            "canonical": "def count_vowels(s):\n    return sum(1 for c in s.lower() if c in 'aeiou')",
            "test": "assert count_vowels('hello') == 2\nassert count_vowels('xyz') == 0",
            "imports": []
        },
        {
            "task_id": 8,
            "description": "Return list of primes up to n",
            "prompt": "Write a python function primes_up_to(n) that returns a list of all primes up to n.",
            "canonical": "def primes_up_to(n):\n    if n < 2:\n        return []\n    sieve = [True] * (n + 1)\n    sieve[0] = sieve[1] = False\n    for i in range(2, int(n**0.5) + 1):\n        if sieve[i]:\n            for j in range(i*i, n+1, i):\n                sieve[j] = False\n    return [i for i in range(2, n+1) if sieve[i]]",
            "test": "assert primes_up_to(10) == [2,3,5,7]\nassert primes_up_to(2) == [2]",
            "imports": []
        },
        {
            "task_id": 9,
            "description": "Check if number is prime",
            "prompt": "Write a python function is_prime(n) that returns True if n is prime, False otherwise.",
            "canonical": "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
            "test": "assert is_prime(7) == True\nassert is_prime(4) == False\nassert is_prime(1) == False",
            "imports": []
        },
        {
            "task_id": 10,
            "description": "Return length of last word",
            "prompt": "Write a python function length_last_word(s) that returns the length of the last word in a string.",
            "canonical": "def length_last_word(s):\n    words = s.split()\n    return len(words[-1]) if words else 0",
            "test": "assert length_last_word('hello world') == 5\nassert length_last_word('') == 0",
            "imports": []
        },
        {
            "task_id": 11,
            "description": "Remove duplicates from list",
            "prompt": "Write a python function remove_duplicates(lst) that returns a list with duplicates removed.",
            "canonical": "def remove_duplicates(lst):\n    return list(dict.fromkeys(lst))",
            "test": "assert remove_duplicates([1,2,2,3]) == [1,2,3]\nassert remove_duplicates([]) == []",
            "imports": []
        },
        {
            "task_id": 12,
            "description": "Return common elements",
            "prompt": "Write a python function common_elements(lst1, lst2) that returns common elements between two lists.",
            "canonical": "def common_elements(lst1, lst2):\n    return list(set(lst1) & set(lst2))",
            "test": "assert common_elements([1,2,3], [2,3,4]) == [2,3]\nassert common_elements([], [1]) == []",
            "imports": []
        },
        {
            "task_id": 13,
            "description": "Calculate power",
            "prompt": "Write a python function power(base, exp) that returns base raised to exp power.",
            "canonical": "def power(base, exp):\n    return base ** exp",
            "test": "assert power(2, 3) == 8\nassert power(5, 0) == 1",
            "imports": []
        },
        {
            "task_id": 14,
            "description": "Return sorted list",
            "prompt": "Write a python function sort_list(lst) that returns a sorted list in ascending order.",
            "canonical": "def sort_list(lst):\n    return sorted(lst)",
            "test": "assert sort_list([3,1,2]) == [1,2,3]\nassert sort_list([]) == []",
            "imports": []
        },
        {
            "task_id": 15,
            "description": "Check even number",
            "prompt": "Write a python function is_even(n) that returns True if n is even, False otherwise.",
            "canonical": "def is_even(n):\n    return n % 2 == 0",
            "test": "assert is_even(4) == True\nassert is_even(3) == False",
            "imports": []
        },
        {
            "task_id": 16,
            "description": "Return absolute value",
            "prompt": "Write a python function absolute(n) that returns the absolute value of n.",
            "canonical": "def absolute(n):\n    return abs(n)",
            "test": "assert absolute(-5) == 5\nassert absolute(5) == 5\nassert absolute(0) == 0",
            "imports": []
        },
        {
            "task_id": 17,
            "description": "Return string length",
            "prompt": "Write a python function string_length(s) that returns the length of a string.",
            "canonical": "def string_length(s):\n    return len(s)",
            "test": "assert string_length('hello') == 5\nassert string_length('') == 0",
            "imports": []
        },
        {
            "task_id": 18,
            "description": "Return uppercase string",
            "prompt": "Write a python function uppercase(s) that returns the uppercase version of a string.",
            "canonical": "def uppercase(s):\n    return s.upper()",
            "test": "assert uppercase('hello') == 'HELLO'\nassert uppercase('') == ''",
            "imports": []
        },
        {
            "task_id": 19,
            "description": "Return lowercase string",
            "prompt": "Write a python function lowercase(s) that returns the lowercase version of a string.",
            "canonical": "def lowercase(s):\n    return s.lower()",
            "test": "assert lowercase('HELLO') == 'hello'\nassert lowercase('') == ''",
            "imports": []
        },
        {
            "task_id": 20,
            "description": "Check substring",
            "prompt": "Write a python function contains_substring(s, sub) that returns True if sub is in s, False otherwise.",
            "canonical": "def contains_substring(s, sub):\n    return sub in s",
            "test": "assert contains_substring('hello', 'ell') == True\nassert contains_substring('hello', 'xyz') == False",
            "imports": []
        },
    ]

    def __init__(
        self,
        model_provider: str = None,
        model_name: str = None,
        timeout: int = 10,
        max_problems: int = None
    ):
        self.benchmark_name = "MBPP"
        self.timeout = timeout
        self.max_problems = max_problems or len(self.PROBLEMS)

        # Get provider from environment or parameter
        self.model_provider = model_provider or os.environ.get("MODEL_PROVIDER", "ollama")
        self.model_name = model_name or os.environ.get("MODEL_NAME", "")

        # Load model client
        try:
            self.client = create_model_client(self.model_provider, self.model_name)
            print(f"Using model: {self.client.get_model_name()} (provider: {self.model_provider})")
        except Exception as e:
            print(f"Warning: Could not create model client: {e}")
            print("Using stub mode - results will be from canonical solutions")
            self.client = None

        # Load test cases
        self.test_cases = self._load_test_cases()
        self.total_cases = len(self.test_cases)

    def _load_test_cases(self) -> List[Dict]:
        """Load MBPP test cases."""
        if self.max_problems:
            return self.PROBLEMS[:self.max_problems]
        return self.PROBLEMS

    def _format_prompt(self, problem: Dict) -> str:
        """Format the prompt for code generation."""
        prompt = f"""Write a Python function to solve this problem:

{problem['description']}

{problem['prompt']}

Write only the function definition, without any additional explanation or test code."""
        return prompt

    def generate_code(self, problem: Dict) -> Tuple[str, Optional[str]]:
        """Generate code for a problem using the model."""
        if self.client is None:
            # Return canonical solution in stub mode
            return problem['canonical'], None

        prompt = self._format_prompt(problem)

        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=1024
            )
            return result.text, None
        except Exception as e:
            return "", str(e)

    def _extract_function(self, code: str, problem: Dict) -> str:
        """Extract the function definition from generated code."""
        # Try to find function definition
        # Look for "def function_name" pattern
        lines = code.split('\n')

        # Find first function definition
        func_lines = []
        in_function = False

        for line in lines:
            if re.match(r'^def\s+\w+\s*\(', line):
                in_function = True
                func_lines = [line]
            elif in_function:
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    # End of function
                    break
                func_lines.append(line)

        if func_lines:
            return '\n'.join(func_lines)

        # Fallback: return entire code if no clear function found
        return code

    def _test_code(self, code: str, problem: Dict) -> Tuple[bool, Optional[str]]:
        """Test generated code against test cases."""
        # Set up timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.timeout)

        try:
            # Prepare code for execution
            imports = '\n'.join(problem.get('imports', []))
            test_code = problem.get('test', '')

            full_code = f"{imports}\n{code}\n{test_code}"

            # Execute in isolated scope
            local_scope = {}
            exec(full_code, {}, local_scope)

            # If we get here, tests passed
            signal.alarm(0)  # Cancel alarm
            return True, None

        except TimeoutException:
            return False, "Execution timed out"
        except Exception as e:
            return False, str(e)

    def evaluate(self, model_name: str = None) -> Dict[str, Any]:
        """Evaluate model against MBPP benchmark."""
        if model_name and self.client:
            # Update client if model changed
            self.client = create_model_client(self.model_provider, model_name)

        pass_at_1 = 0
        results = []

        print(f"\nEvaluating {self.total_cases} problems...")

        for i, problem in enumerate(self.test_cases):
            print(f"  Problem {i+1}/{self.total_cases}: Task {problem['task_id']}")

            # Generate code
            generated_code, error = self.generate_code(problem)

            if error:
                print(f"    Generation error: {error}")
                results.append(MBPPResult(
                    task_id=problem['task_id'],
                    passed=False,
                    generated_code=generated_code,
                    error=error
                ))
                continue

            # Extract function
            extracted = self._extract_function(generated_code, problem)

            # Test code
            passed, test_error = self._test_code(extracted, problem)

            if passed:
                pass_at_1 += 1
                print(f"    ✓ Passed")
            else:
                print(f"    ✗ Failed: {test_error}")

            results.append(MBPPResult(
                task_id=problem['task_id'],
                passed=passed,
                generated_code=generated_code,
                error=test_error
            ))

        accuracy = pass_at_1 / self.total_cases if self.total_cases > 0 else 0

        return {
            "pass_at_1": pass_at_1,
            "pass_at_3": pass_at_1,  # Simplified - would need multiple generations
            "pass_at_5": pass_at_1,
            "total_cases": self.total_cases,
            "accuracy": accuracy,
            "benchmark": self.benchmark_name,
            "model": model_name or self.client.get_model_name() if self.client else "stub",
            "results": [
                {"task_id": r.task_id, "passed": r.passed, "error": r.error}
                for r in results
            ]
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MBPP Benchmark")
    parser.add_argument("--provider", choices=["ollama", "openai", "anthropic"],
                        help="Model provider")
    parser.add_argument("--model", type=str, help="Model name")
    parser.add_argument("--max-problems", type=int, help="Max problems to test")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds")

    args = parser.parse_args()

    benchmark = MBPP(
        model_provider=args.provider,
        model_name=args.model,
        max_problems=args.max_problems,
        timeout=args.timeout
    )

    results = benchmark.evaluate()

    print("\n" + "=" * 40)
    print("MBPP Results:")
    print(f"  Pass@1: {results['pass_at_1']}/{results['total_cases']} ({results['accuracy']*100:.1f}%)")
    print(f"  Model: {results['model']}")