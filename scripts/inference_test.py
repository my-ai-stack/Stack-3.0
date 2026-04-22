#!/usr/bin/env python3
"""
Stack 3.0 Omni Nexus — Inference Test
Tests code generation quality on diverse prompts.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "my-ai-stack/Stack-3.0-Omni-Nexus"

PROMPTS = [
    # Simple function
    """You are a helpful coding assistant.

Write a Python function to fibonacci number at index n using dynamic programming.

def fib(n):""",

    # Algorithm
    """You are a helpful coding assistant.

Implement a LRU cache with O(1) get and put operations.

class LRUCache:""",

    # Code explanation
    """You are a helpful coding assistant.

Explain what this function does and identify any bugs:

def helper(data, k):
    result = []
    for i in range(len(data)):
        if i % k == 0:
            result.append(data[i])
    return result""",

    # Debugging
    """You are a helpful coding assistant.

Find and fix the bug in this code:

def find_duplicates(nums):
    seen = set()
    duplicates = []
    for num in nums:
        if num in seen:
            duplicates.append(num)
        seen.add(num)
    return duplicates""",

    # Async code
    """You are a helpful coding assistant.

Write an async function that fetches data from multiple URLs concurrently with a timeout.

import asyncio

async def fetch_all(urls, timeout=5):""",
]

def main():
    print(f"Loading model: {MODEL_ID}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    print(f"\n{'='*60}")
    print("INFERENCE TEST — Stack 3.0 Omni Nexus")
    print(f"{'='*60}\n")

    for i, prompt in enumerate(PROMPTS, 1):
        print(f"[{i}/5] Prompt: {prompt[:60].strip()}...")
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.2,
                top_p=0.95,
                do_sample=True,
                repetition_penalty=1.1,
            )

        response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        print(f"Output:\n{response.strip()}")
        print(f"\n{'-'*60}\n")

if __name__ == "__main__":
    main()
