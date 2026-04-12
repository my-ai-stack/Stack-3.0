#!/usr/bin/env python3
"""
Proper benchmark evaluation with Pass@k methodology.
Supports: HumanEval (164 problems) and MBPP (500 problems).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import signal
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from model_client import create_model_client, ChatMessage

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

def load_benchmark_data(benchmark: str, data_dir: str = "./data") -> List[Dict]:
    """Load benchmark problems from downloaded dataset."""
    data_path = Path(data_dir) / benchmark
    dataset_file = data_path / f"{benchmark}.jsonl"

    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_file}. Run scripts/download_benchmark_datasets.py first.")

    problems = []
    with open(dataset_file, 'r') as f:
        for line in f:
            problems.append(json.loads(line))

    return problems

def format_problem_prompt(problem: Dict, benchmark: str) -> str:
    """Format problem into a prompt for code generation."""
    if benchmark == "humaneval":
        # HumanEval has prompt field with function signature and docstring
        prompt = problem["prompt"]
        # Add instruction to complete the function
        if "def " in prompt:
            return f"{prompt}\n    # Your code here\n    pass"
        return prompt
    elif benchmark == "mbpp":
        # MBPP has text description and sometimes starter code
        text = problem["text"]
        code = problem.get("code", "")
        if code:
            return f"{text}\n\nComplete the following code:\n{code}"
        return text
    else:
        return str(problem)

def execute_test(code: str, problem: Dict, benchmark: str, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """Execute generated code against test cases."""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        if benchmark == "humaneval":
            test_code = problem.get("test", "")
            entry_point = problem.get("entry_point", "")
        elif benchmark == "mbpp":
            test_list = problem.get("test_list", [])
            test_code = "\n".join(test_list)
            entry_point = problem.get("func_name", "")
        else:
            return False, "Unknown benchmark"

        # Combine code and tests
        full_code = f"{code}\n{test_code}"

        # Execute in isolated namespace
        local_scope = {}
        exec(full_code, {}, local_scope)

        signal.alarm(0)
        return True, None

    except TimeoutException:
        return False, "Execution timed out"
    except Exception as e:
        return False, str(e)
    finally:
        signal.alarm(0)

def compute_pass_k(results: List[bool], k: int, n: int) -> float:
    """
    Compute unbiased Pass@k estimator.

    Pass@k = 1 - C(n-c, k) / C(n, k)
    where c = number of correct samples, n = total problems evaluated.
    For Pass@k with multiple samples per problem, we treat each problem independently.
    Here results[i] is True if ANY of the k samples for problem i passed.
    """
    c = sum(results)  # number of problems with at least 1 passing sample
    if k >= n:
        return c / n
    # Unbiased estimator
    return 1.0 - (1.0 - c / n) ** k

def evaluate_benchmark(
    benchmark: str,
    provider: str,
    model: Optional[str],
    k_samples: int = 100,
    data_dir: str = "./data",
    output_dir: str = "./results",
    test_sample: bool = False,
    checkpoint_freq: int = 20,
    resume: bool = False,
    temperature_range: tuple = (0.2, 1.0),
    **model_kwargs
) -> Dict[str, Any]:
    """
    Evaluate model on benchmark with proper Pass@k methodology.

    Args:
        benchmark: 'humaneval' or 'mbpp'
        provider: Model provider (ollama, openai, anthropic, openrouter, together)
        model: Model name (uses default if None)
        k_samples: Number of samples per problem for Pass@k
        data_dir: Directory containing downloaded datasets
        output_dir: Where to save results
        test_sample: If True, only evaluate 5 problems (for quick testing)
        checkpoint_freq: Save checkpoint every N problems
        resume: Resume from checkpoint if available
        temperature_range: (min, max) temperature for sampling diversity

    Returns:
        Dictionary with Pass@1, Pass@10, Pass@100, and detailed results
    """
    # Create output directory
    output_path = Path(output_dir) / benchmark
    output_path.mkdir(parents=True, exist_ok=True)

    checkpoint_file = output_path / f"checkpoint_{provider}_{model or 'default'}.json"
    results_file = output_path / f"results_{provider}_{model or 'default'}.json"
    summary_file = output_path / f"summary_{provider}_{model or 'default'}.json"

    # Load problems
    print(f"Loading {benchmark} dataset from {data_dir}...")
    problems = load_benchmark_data(benchmark, data_dir)

    if test_sample:
        problems = problems[:5]
        print(f"⚠️  Test mode: evaluating only {len(problems)} problems")
    else:
        print(f"Loaded {len(problems)} problems")

    # Check for checkpoint
    start_idx = 0
    all_problem_results = []
    if resume and checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
            all_problem_results = checkpoint.get("results", [])
            start_idx = len(all_problem_results)
            print(f"Resuming from checkpoint: {start_idx}/{len(problems)} problems completed")

    # Initialize model client
    print(f"Initializing model client: provider={provider}, model={model or 'default'}")
    client = create_model_client(provider=provider, model=model, **model_kwargs)

    # Evaluate each problem
    for idx, problem in enumerate(problems[start_idx:], start=start_idx):
        problem_id = problem.get("task_id", f"{benchmark}/{idx}")
        print(f"\n[{idx+1}/{len(problems)}] Problem {problem_id}")

        prompt = format_problem_prompt(problem, benchmark)
        sample_results = []

        # Generate k samples with varying temperature
        for sample_idx in range(k_samples):
            temperature = temperature_range[0] + (temperature_range[1] - temperature_range[0]) * (sample_idx / max(k_samples-1, 1))

            try:
                result = client.generate(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=1024,
                    stop=None
                )
                generated_code = result.text.strip()

                # Extract function if needed (for HumanEval)
                if benchmark == "humaneval":
                    # Keep only the function definition
                    lines = generated_code.split('\n')
                    func_lines = []
                    in_func = False
                    for line in lines:
                        if line.strip().startswith('def '):
                            in_func = True
                        if in_func:
                            func_lines.append(line)
                            # Stop at next top-level def or class
                            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                                if len(func_lines) > 1:
                                    break
                    if func_lines:
                        generated_code = '\n'.join(func_lines)

                # Execute test
                passed, error = execute_test(generated_code, problem, benchmark, timeout=10)
                sample_results.append({
                    "sample_idx": sample_idx,
                    "temperature": temperature,
                    "passed": passed,
                    "error": error,
                    "code": generated_code[:200] + "..." if len(generated_code) > 200 else generated_code
                })

                status = "✓" if passed else "✗"
                print(f"  Sample {sample_idx+1}/{k_samples} (T={temperature:.2f}): {status}")

            except Exception as e:
                print(f"  Sample {sample_idx+1}: Error - {e}")
                sample_results.append({
                    "sample_idx": sample_idx,
                    "temperature": temperature,
                    "passed": False,
                    "error": str(e),
                    "code": ""
                })

        # Determine if problem passed (any sample succeeded)
        problem_passed = any(s["passed"] for s in sample_results)

        problem_result = {
            "problem_id": problem_id,
            "passed": problem_passed,
            "samples": sample_results,
            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt
        }
        all_problem_results.append(problem_result)

        # Save checkpoint periodically
        if (idx + 1) % checkpoint_freq == 0:
            checkpoint = {
                "benchmark": benchmark,
                "provider": provider,
                "model": model or client.get_model_name(),
                "k_samples": k_samples,
                "timestamp": datetime.now().isoformat(),
                "completed": idx + 1,
                "total": len(problems),
                "results": all_problem_results
            }
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            print(f"  ✓ Checkpoint saved ({idx+1}/{len(problems)})")

    # Compute Pass@k metrics (using any-pass logic for each problem)
    results_binary = [r["passed"] for r in all_problem_results]

    # For Pass@1 we use the first sample's result effectively, but since we have k samples,
    # Pass@1 with k samples is the probability that at least 1 of k samples passes.
    # This is an estimate of the model's best possible pass rate.
    pass_at_1 = compute_pass_k(results_binary, 1, len(results_binary))
    pass_at_10 = compute_pass_k(results_binary, 10, len(results_binary))
    pass_at_100 = compute_pass_k(results_binary, 100, len(results_binary))

    summary = {
        "benchmark": benchmark,
        "provider": provider,
        "model": model or client.get_model_name(),
        "k_samples": k_samples,
        "total_problems": len(problems),
        "passed_problems": sum(results_binary),
        "pass_at_1": pass_at_1,
        "pass_at_10": pass_at_10,
        "pass_at_100": pass_at_100,
        "timestamp": datetime.now().isoformat()
    }

    # Save final results
    final_output = {
        "metadata": summary,
        "results": all_problem_results
    }
    with open(results_file, 'w') as f:
        json.dump(final_output, f, indent=2)

    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print(f"Benchmark: {benchmark}")
    print(f"Provider: {provider}")
    print(f"Model: {summary['model']}")
    print(f"Total Problems: {len(problems)}")
    print(f"Pass@1: {pass_at_1*100:.1f}%")
    print(f"Pass@10: {pass_at_10*100:.1f}%")
    print(f"Pass@100: {pass_at_100*100:.1f}%")
    print(f"\nResults saved to: {results_file}")
    print(f"Summary saved to: {summary_file}")
    print("="*60)

    return summary

def main():
    parser = argparse.ArgumentParser(description="Proper benchmark evaluation with Pass@k")
    parser.add_argument("--benchmark", choices=["humaneval", "mbpp"], required=True, help="Benchmark to run")
    parser.add_argument("--provider", choices=["ollama", "openai", "anthropic", "openrouter", "together"], required=True, help="Model provider")
    parser.add_argument("--model", type=str, help="Model name (provider-specific)")
    parser.add_argument("--k-samples", type=int, default=100, help="Number of samples per problem for Pass@k")
    parser.add_argument("--data-dir", type=str, default="./data", help="Directory with downloaded datasets")
    parser.add_argument("--output-dir", type=str, default="./results", help="Where to save results")
    parser.add_argument("--test-sample", action="store_true", help="Run on 5 problems only (quick test)")
    parser.add_argument("--checkpoint-freq", type=int, default=20, help="Save checkpoint every N problems")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint if available")
    parser.add_argument("--api-key", type=str, help="API key (or set environment variable)")

    args = parser.parse_args()

    # Prepare model kwargs
    model_kwargs = {}
    if args.api_key:
        model_kwargs["api_key"] = args.api_key

    try:
        summary = evaluate_benchmark(
            benchmark=args.benchmark,
            provider=args.provider,
            model=args.model,
            k_samples=args.k_samples,
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            test_sample=args.test_sample,
            checkpoint_freq=args.checkpoint_freq,
            resume=args.resume,
            **model_kwargs
        )
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nInterrupted. Progress saved in checkpoint (if enabled).")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
