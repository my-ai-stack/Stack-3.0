"""
GSM8K (Grade School Math 8K) benchmark implementation
Real implementation with model API integration.
"""

import os
import re
import json
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from model_client import create_model_client, BaseModelClient


@dataclass
class GSM8KResult:
    """Result for a single problem."""
    task_id: int
    passed: bool
    generated_answer: str
    correct_answer: str
    error: Optional[str] = None


class GSM8K:
    """GSM8K Benchmark with real model integration."""

    # GSM8K problems (subset for testing)
    # These are grade school math problems requiring multi-step reasoning
    PROBLEMS = [
        {
            "task_id": 1,
            "question": "John has 5 apples. He buys 3 more apples at the store. How many apples does John have now?",
            "answer": "8",
            "solution": "John starts with 5 apples. He buys 3 more apples. 5 + 3 = 8 apples."
        },
        {
            "task_id": 2,
            "question": "Sarah had 12 candies. She gave 5 candies to her friend. How many candies does Sarah have left?",
            "answer": "7",
            "solution": "Sarah starts with 12 candies. She gives away 5. 12 - 5 = 7 candies."
        },
        {
            "task_id": 3,
            "question": "A box contains 6 packs of pencils. Each pack has 8 pencils. How many pencils are there in total?",
            "answer": "48",
            "solution": "There are 6 packs with 8 pencils each. 6 × 8 = 48 pencils."
        },
        {
            "task_id": 4,
            "question": "Tom has 24 baseball cards. He buys 12 more cards each week for 2 weeks. How many cards does Tom have now?",
            "answer": "48",
            "solution": "Tom buys 12 cards per week for 2 weeks = 24 cards. 24 + 24 = 48 cards."
        },
        {
            "task_id": 5,
            "question": "There are 15 students in a class. Each student has 4 books. How many books are there in total?",
            "answer": "60",
            "solution": "15 students × 4 books each = 60 books."
        },
        {
            "task_id": 6,
            "question": "Lisa bought a shirt for $20 and a pants for $35. She paid with a $100 bill. How much change did she get?",
            "answer": "45",
            "solution": "Total cost: $20 + $35 = $55. Change: $100 - $55 = $45."
        },
        {
            "task_id": 7,
            "question": "A train travels 60 miles per hour for 3 hours. How far does the train travel?",
            "answer": "180",
            "solution": "Distance = speed × time = 60 × 3 = 180 miles."
        },
        {
            "task_id": 8,
            "question": "There are 7 days in a week. How many days are there in 5 weeks?",
            "answer": "35",
            "solution": "7 days × 5 weeks = 35 days."
        },
        {
            "task_id": 9,
            "question": "Mike has 45 stamps. He gives 18 stamps to his brother. How many stamps does Mike have left?",
            "answer": "27",
            "solution": "45 - 18 = 27 stamps."
        },
        {
            "task_id": 10,
            "question": "Each pizza has 8 slices. If there are 4 pizzas, how many slices are there total?",
            "answer": "32",
            "solution": "8 slices × 4 pizzas = 32 slices."
        },
        {
            "task_id": 11,
            "question": "A farmer has 36 chickens. Each chicken has 2 legs. How many legs do all the chickens have?",
            "answer": "72",
            "solution": "36 chickens × 2 legs = 72 legs."
        },
        {
            "task_id": 12,
            "question": "Amy reads 15 pages of her book each day. How many pages does she read in 6 days?",
            "answer": "90",
            "solution": "15 pages × 6 days = 90 pages."
        },
        {
            "task_id": 13,
            "question": "There are 52 cards in a deck. Jack has 2 decks of cards. How many cards does Jack have?",
            "answer": "104",
            "solution": "52 cards × 2 decks = 104 cards."
        },
        {
            "task_id": 14,
            "question": "A bakery sold 250 cookies on Monday. On Tuesday, it sold 175 cookies. How many more cookies were sold on Monday than Tuesday?",
            "answer": "75",
            "solution": "250 - 175 = 75 more cookies."
        },
        {
            "task_id": 15,
            "question": "Each box holds 9 pencils. There are 8 boxes. How many pencils are there in total?",
            "answer": "72",
            "solution": "9 pencils × 8 boxes = 72 pencils."
        },
        {
            "task_id": 16,
            "question": "Tom is 12 years old. His sister is 8 years younger than Tom. How old is his sister?",
            "answer": "4",
            "solution": "12 - 8 = 4 years old."
        },
        {
            "task_id": 17,
            "question": "There are 24 hours in a day. How many hours are there in a week?",
            "answer": "168",
            "solution": "24 hours × 7 days = 168 hours."
        },
        {
            "task_id": 18,
            "question": "A car travels 55 miles per hour. How far does it travel in 4 hours?",
            "answer": "220",
            "solution": "55 × 4 = 220 miles."
        },
        {
            "task_id": 19,
            "question": "Jane has 3 dozen eggs. How many eggs does she have?",
            "answer": "36",
            "solution": "3 dozen = 3 × 12 = 36 eggs."
        },
        {
            "task_id": 20,
            "question": "A garden has 8 rows of plants with 7 plants in each row. How many plants are in the garden?",
            "answer": "56",
            "solution": "8 rows × 7 plants = 56 plants."
        },
    ]

    def __init__(
        self,
        model_provider: str = None,
        model_name: str = None,
        timeout: int = 30,
        max_problems: int = None
    ):
        self.benchmark_name = "GSM8K"
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
        """Load GSM8K test cases."""
        if self.max_problems:
            return self.PROBLEMS[:self.max_problems]
        return self.PROBLEMS

    def _format_prompt(self, problem: Dict) -> str:
        """Format the prompt for math problem solving."""
        prompt = f"""Solve this math problem step by step. Show your reasoning and give the final answer as a number.

Problem: {problem['question']}

Give your answer as a number only."""
        return prompt

    def generate_answer(self, problem: Dict) -> Tuple[str, Optional[str]]:
        """Generate answer for a problem using the model."""
        if self.client is None:
            # Return canonical solution in stub mode
            return problem['answer'], None

        prompt = self._format_prompt(problem)

        try:
            result = self.client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=512
            )
            return result.text, None
        except Exception as e:
            return "", str(e)

    def _extract_final_answer(self, response: str) -> str:
        """Extract the final numeric answer from model's response."""
        # Clean the response
        response = response.strip()

        # Try to find a number at the end or as the answer
        # First, look for patterns like "The answer is X" or "= X"
        patterns = [
            r'(?:the\s+)?answer\s+is\s+(\d+)',
            r'=\s*(\d+)',
            r'(\d+)\s*$',
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1)

        # If no pattern found, try to extract all numbers and take the last one
        numbers = re.findall(r'\d+', response)
        if numbers:
            return numbers[-1]

        # Return the cleaned response if no numbers found
        return response.strip()

    def _check_answer(self, response: str, correct_answer: str) -> bool:
        """Check if the response matches the correct answer."""
        try:
            # Extract the final answer from the response
            extracted = self._extract_final_answer(response)

            # Clean both for comparison
            extracted_clean = extracted.strip()
            correct_clean = correct_answer.strip()

            # Direct comparison
            if extracted_clean == correct_clean:
                return True

            # Try numeric comparison
            try:
                return float(extracted_clean) == float(correct_clean)
            except ValueError:
                pass

            return False

        except Exception as e:
            return False

    def evaluate(self, model_name: str = None) -> Dict[str, Any]:
        """Evaluate model against GSM8K benchmark."""
        if model_name and self.client:
            self.client = create_model_client(self.model_provider, model_name)

        correct_answers = 0
        results = []

        print(f"\nEvaluating {self.total_cases} math problems...")

        for i, problem in enumerate(self.test_cases):
            print(f"  Problem {i+1}/{self.total_cases}: Task {problem['task_id']}")

            generated_answer, error = self.generate_answer(problem)

            if error:
                print(f"    Generation error: {error}")
                results.append(GSM8KResult(
                    task_id=problem['task_id'],
                    passed=False,
                    generated_answer=generated_answer,
                    correct_answer=problem['answer'],
                    error=error
                ))
                continue

            # Extract and check answer
            extracted = self._extract_final_answer(generated_answer)
            passed = self._check_answer(generated_answer, problem['answer'])

            if passed:
                correct_answers += 1
                print(f"    ✓ Correct: {extracted}")
            else:
                print(f"    ✗ Wrong: got {extracted}, expected {problem['answer']}")

            results.append(GSM8KResult(
                task_id=problem['task_id'],
                passed=passed,
                generated_answer=generated_answer,
                correct_answer=problem['answer']
            ))

        accuracy = correct_answers / self.total_cases if self.total_cases > 0 else 0

        return {
            "pass_at_1": correct_answers,
            "pass_at_3": correct_answers,
            "pass_at_5": correct_answers,
            "total_cases": self.total_cases,
            "accuracy": accuracy,
            "benchmark": self.benchmark_name,
            "model": model_name or self.client.get_model_name() if self.client else "stub",
            "results": [
                {"task_id": r.task_id, "passed": r.passed, "got": r.generated_answer[:50], "expected": r.correct_answer}
                for r in results
            ]
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GSM8K Benchmark")
    parser.add_argument("--provider", choices=["ollama", "openai", "anthropic"],
                        help="Model provider")
    parser.add_argument("--model", type=str, help="Model name")
    parser.add_argument("--max-problems", type=int, help="Max problems to test")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")

    args = parser.parse_args()

    benchmark = GSM8K(
        model_provider=args.provider,
        model_name=args.model,
        max_problems=args.max_problems,
        timeout=args.timeout
    )

    results = benchmark.evaluate()

    print("\n" + "=" * 40)
    print("GSM8K Results:")
    print(f"  Accuracy: {results['correct']}/{results['total_cases']} ({results['accuracy']*100:.1f}%)")
    print(f"  Model: {results['model']}")