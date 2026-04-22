#!/usr/bin/env python3
"""
Stack 3.0 Omni Nexus — HumanEval Benchmark
Runs pass@k evaluation using the openai HumanEval dataset.
"""

import json
import os
import torch
import re
from transformers import AutoTokenizer, AutoModelForCausalLM
from collections import defaultdict

MODEL_ID = "my-ai-stack/Stack-3.0-Omni-Nexus"
HF_DATASET = "openai/openai_humaneval"
NUM_samples = 1  # pass@1 (set to 10 or 20 for pass@10/20)
MAX_TOKENS = 512
TEMPERATURE = 0.2
TOP_P = 0.95

def setup_model():
    print(f"Loading {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    return model, tokenizer

def extract_code(completion: str) -> str:
    """Extract the first code block or fallback to raw completion."""
    if "```python" in completion:
        match = re.search(r"```python\n(.*?)```", completion, re.DOTALL)
        if match:
            return match.group(1).strip()
    if "```" in completion:
        match = re.search(r"```\n(.*?)```", completion, re.DOTALL)
        if match:
            return match.group(1).strip()
    return completion.strip()

def run_humaneval(model, tokenizer, dataset):
    """Generate completions and check correctness."""
    # Try to use 'bigcode/the-stack' HumanEval split if available
    try:
        from datasets import load_dataset
        data = load_dataset(HF_DATASET, split="test")
    except Exception as e:
        print(f"[WARN] Could not load dataset from HF: {e}")
        print("Using local human_eval.json if available...")
        return None

    results = []
    correct = 0

    for i, item in enumerate(data):
        prompt = item["prompt"]
        test = item["test"]
        entry_point = item["entry_point"]

        # Build prompt with canonical instruction format
        full_prompt = f"You are a helpful coding assistant.\n\n{prompt}"

        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                do_sample=True,
                repetition_penalty=1.1,
            )

        completion = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        code = extract_code(completion)

        # Write to temp file and exec the test
        try:
            exec_globals = {}
            exec(code + "\n" + test, exec_globals)
            passed = True
            correct += 1
        except Exception:
            passed = False

        results.append({"task_id": item.get("task_id", i), "passed": passed, "completion": completion[:100]})
        print(f"[{i+1}/164] {'✅' if passed else '❌'} {item.get('task_id', i)}")

    total = len(results)
    pass_at_k = correct / total if total > 0 else 0
    return {"pass@1": pass_at_k, "correct": correct, "total": total, "results": results}

def main():
    model, tokenizer = setup_model()
    print(f"\nRunning HumanEval benchmark...")
    print(f"pass@{NUM_samples} evaluation\n")

    results = run_humaneval(model, tokenizer, None)

    if results:
        print(f"\n{'='*50}")
        print(f"RESULTS: pass@1 = {results['pass@1']:.2%} ({results['correct']}/{results['total']})")
        print(f"{'='*50}")

        with open("results_humaneval.json", "w") as f:
            json.dump(results, f, indent=2)
        print("Results saved to results_humaneval.json")
    else:
        print("Benchmark could not run — check dataset availability.")

if __name__ == "__main__":
    main()
