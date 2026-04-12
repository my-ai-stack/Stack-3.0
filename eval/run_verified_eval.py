#!/usr/bin/env python3
"""
Verified Evaluation Pipeline for Stack 3.0 Weight Testing.
Loads the .safetensors model and runs HumanEval and MBPP datasets.
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Set the absolute path to the model weights
MODEL_PATH = "/Users/walidsobhi/stack-3.0/src/tokenizer_model.safetensors"
# Since the .safetensors is in a directory with config files, we use the directory as the model name for AutoModel
MODEL_DIR = Path(MODEL_PATH).parent

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

def load_benchmark_data(benchmark: str, data_dir: str = "./data") -> List[Dict]:
    """Load benchmark problems from downloaded dataset."""
    data_path = Path(data_dir) / benchmark
    dataset_file = data_path / f"{benchmark}.jsonl"

    if not dataset_file.exists():
        # Try checking if the file is just in the data_dir
        dataset_file = Path(data_dir) / f"{benchmark}.jsonl"
        if not dataset_file.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_file}. Ensure data is downloaded.")

    problems = []
    with open(dataset_file, 'r') as f:
        for line in f:
            problems.append(json.loads(line))
    return problems

def format_problem_prompt(problem: Dict, benchmark: str) -> str:
    """
    Format problem into a prompt using the exact Qwen2 chat template.
    <|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n
    <|im_start|>user\n{prompt}<|im_end|>\n
    <|im_start|>assistant\n
    """
    if benchmark == "humaneval":
        prompt = problem["prompt"]
        if "def " in prompt:
            prompt = f"{prompt}\n    # Your code here\n    pass"
    elif benchmark == "mbpp":
        text = problem["text"]
        code = problem.get("code", "")
        prompt = f"{text}\n\nComplete the following code:\n{code}" if code else text
    else:
        prompt = str(problem)

    # Wrap in the exact ChatML format used during training (as seen in chat_template.jinja)
    full_prompt = (
        "<|im_start|>system\n"
        "You are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n{prompt}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    return full_prompt

def execute_test(code: str, problem: Dict, benchmark: str, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """Execute generated code against test cases."""
    signal.signal(signal.signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        if benchmark == "humaneval":
            test_code = problem.get("test", "")
        elif benchmark == "mbpp":
            test_list = problem.get("test_list", [])
            test_code = "\n".join(test_list)
        else:
            return False, "Unknown benchmark"

        full_code = f"{code}\n{test_code}"
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

def compute_pass_at_1(results: List[bool]) -> float:
    """Compute Pass@1 accuracy."""
    if not results:
        return 0.0
    return sum(results) / len(results)

def evaluate_benchmark(
    benchmark: str,
    model,
    tokenizer,
    data_dir: str = "./data",
    output_dir: str = "./results",
    test_sample: bool = False,
) -> Dict[str, Any]:
    """Run evaluation on a specific benchmark."""
    output_path = Path(output_dir) / benchmark
    output_path.mkdir(parents=True, exist_ok=True)

    results_file = output_path / f"verified_results_{benchmark}.json"

    print(f"Loading {benchmark} dataset from {data_dir}...")
    problems = load_benchmark_data(benchmark, data_dir)

    if test_sample:
        problems = problems[:5]
        print(f"Test mode: evaluating 5 problems")
    else:
        print(f"Evaluating {len(problems)} problems")

    all_results = []

    model.eval()
    with torch.no_grad():
        for idx, problem in enumerate(problems):
            problem_id = problem.get("task_id", f"{benchmark}/{idx}")
            prompt = format_problem_prompt(problem, benchmark)

            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

            # Greedy decoding for Pass@1
            output_tokens = model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.0, # Deterministic for Pass@1
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

            # Decode only the generated part
            generated_text = tokenizer.decode(output_tokens[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            code = generated_text.strip()

            # Basic HumanEval cleanup (extract first function)
            if benchmark == "humaneval":
                lines = code.split('\n')
                func_lines = []
                in_func = False
                for line in lines:
                    if line.strip().startswith('def '):
                        in_func = True
                    if in_func:
                        func_lines.append(line)
                        if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                            if len(func_lines) > 1: break
                if func_lines:
                    code = '\n'.join(func_lines)

            passed, error = execute_test(code, problem, benchmark)
            all_results.append({
                "problem_id": problem_id,
                "passed": passed,
                "code": code,
                "error": error
            })

            if (idx + 1) % 10 == 0:
                print(f"Processed {idx+1}/{len(problems)}... Current Pass@1: {compute_pass_at_1([r['passed'] for r in all_results])*100:.2f}%")

    pass_at_1 = compute_pass_at_1([r["passed"] for r in all_results])

    summary = {
        "benchmark": benchmark,
        "pass_at_1": pass_at_1,
        "total_problems": len(problems),
        "passed_problems": sum([r["passed"] for r in all_results]),
        "timestamp": datetime.now().isoformat()
    }

    with open(results_file, 'w') as f:
        json.dump({"summary": summary, "results": all_results}, f, indent=2)

    return summary

def main():
    parser = argparse.ArgumentParser(description="Verified Evaluation for Stack 3.0 Weights")
    parser.add_argument("--data-dir", type=str, default="./data", help="Dataset directory")
    parser.add_argument("--output-dir", type=str, default="./results", help="Output directory")
    parser.add_argument("--test-sample", action="store_true", help="Run on 5 samples only")
    args = parser.parse_args()

    print(f"Loading model from {MODEL_DIR}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR,
        torch_dtype=torch.float16,
        device_map="auto"
    )

    final_scores = {}
    for benchmark in ["humaneval", "mbpp"]:
        try:
            summary = evaluate_benchmark(
                benchmark=benchmark,
                model=model,
                tokenizer=tokenizer,
                data_dir=args.data_dir,
                output_dir=args.output_dir,
                test_sample=args.test_sample
            )
            final_scores[benchmark] = summary
        except Exception as e:
            print(f"Error evaluating {benchmark}: {e}")

    # Output final verified scores for Model Card
    model_card_json = {
        "model": "stack-3.0-verified",
        "evaluation_date": datetime.now().isoformat(),
        "benchmarks": final_scores
    }

    with open(Path(args.output_dir) / "model_card_scores.json", 'w') as f:
        json.dump(model_card_json, f, indent=2)

    print("\n" + "="*30)
    print("FINAL VERIFIED SCORES")
    print("="*30)
    for b, s in final_scores.items():
        print(f"{b}: Pass@1 = {s['pass_at_1']*100:.2f}%")
    print(f"Saved to {args.output_dir}/model_card_scores.json")

if __name__ == "__main__":
    main()
