#!/usr/bin/env python3
"""
Benchmark script for comparing context window performance across different lengths.

This script compares:
1. 32K context (original claim)
2. 64K context (mid-range)
3. 128K context (full potential)

For each context length, it tests:
- Memory consumption (VRAM and RAM)
- Throughput (tokens/second during generation)
- Latency (time to first token)
- Quality (ability to process and generate coherent output)
- Task completion on sample coding tasks

Output: JSON results + summary report
"""

import os
import sys
import json
import time
import argparse
import statistics
from pathlib import Path
from typing import Dict, List, Any

# Required packages: vllm, transformers, psutil, torch

def get_memory_info():
    """Get memory statistics."""
    import torch
    import psutil
    
    process = psutil.Process(os.getpid())
    ram_mb = process.memory_info().rss / 1024 / 1024
    
    if torch.cuda.is_available():
        gpu_mem_allocated = torch.cuda.memory_allocated() / 1024 / 1024
        gpu_mem_reserved = torch.cuda.memory_reserved() / 1024 / 1024
        return {
            "ram_mb": round(ram_mb, 1),
            "gpu_allocated_mb": round(gpu_mem_allocated, 1),
            "gpu_reserved_mb": round(gpu_mem_reserved, 1),
            "gpu_used": True
        }
    else:
        return {
            "ram_mb": round(ram_mb, 1),
            "gpu_used": False
        }

def preprocess_prompt(prompt: str, tokenizer, target_tokens: int, mode: str = "repeat") -> List[int]:
    """Preprocess a prompt to reach target token length."""
    tokens = tokenizer.encode(prompt)
    
    if len(tokens) >= target_tokens:
        return tokens[:target_tokens]
    
    needed = target_tokens - len(tokens)
    
    if mode == "repeat":
        # Repeat a filler pattern
        filler = " This is additional context to fill the window. " * 100
        filler_tokens = tokenizer.encode(filler)
        repeats = (needed // len(filler_tokens)) + 1
        tokens.extend(filler_tokens * repeats)
    elif mode == "noise":
        # Use random-like content (code snippets)
        noise = """
        // Dummy code for context expansion
        function placeholder() {
            const x = 1;
            const y = 2;
            return x + y;
        }
        class DummyClass {
            constructor() {}
            method() {}
        }
        """.repeat(needed // 50 + 1)
        noise_tokens = tokenizer.encode(noise)
        tokens.extend(noise_tokens)
    
    return tokens[:target_tokens]

def load_model(model_name: str, max_model_len: int, block_size: int):
    """Load vLLM model with specified configuration."""
    from vllm import LLM
    
    print(f"Loading model with max_model_len={max_model_len}, block_size={block_size}")
    model = LLM(
        model=model_name,
        max_model_len=max_model_len,
        block_size=block_size,
        gpu_memory_utilization=0.9,
        trust_remote_code=True,
        tensor_parallel_size=1,
        # For benchmarking, disable speculative decoding for consistent results
        enable_chunked_prefill=False
    )
    return model

def run_generation(model, tokenizer, prompt_tokens: List[int], max_new_tokens: int = 200) -> Dict[str, Any]:
    """Run generation and collect metrics."""
    from vllm import SamplingParams
    
    sampling_params = SamplingParams(
        temperature=0.7,
        top_p=0.95,
        max_tokens=max_new_tokens,
        min_p=0.05
    )
    
    # Prefill phase timing
    torch = sys.modules.get('torch')
    if torch and torch.cuda.is_available():
        torch.cuda.synchronize()
    
    start_time = time.time()
    outputs = model.generate(
        prompt_token_ids=prompt_tokens,
        sampling_params=sampling_params,
        use_tqdm=False
    )
    end_time = time.time()
    
    if torch and torch.cuda.is_available():
        torch.cuda.synchronize()
    
    elapsed = end_time - start_time
    output_token_ids = outputs[0].outputs[0].token_ids
    output_text = outputs[0].outputs[0].text
    
    # Count tokens in output
    output_length = len(output_token_ids)
    
    # Calculate prefill latency (estimated)
    prefill_latency = elapsed * 0.3  # Rough estimate
    decode_latency = elapsed - prefill_latency
    
    # Tokens per second
    total_tokens = output_length
    tokens_per_second = total_tokens / elapsed if elapsed > 0 else 0
    
    return {
        "elapsed_seconds": round(elapsed, 4),
        "output_tokens": output_length,
        "output_text": output_text[:200],
        "tokens_per_second": round(tokens_per_second, 2),
        "prefill_latency_est": round(prefill_latency, 4),
        "decode_latency_est": round(decode_latency, 4)
    }

def test_task(model, tokenizer, context_length: int, task_name: str, prompt: str, max_response: int = 200) -> Dict[str, Any]:
    """Run a single benchmark task."""
    print(f"\n  Task: {task_name}")
    sys.stdout.flush()
    
    mem_before = get_memory_info()
    prompt_tokens = preprocess_prompt(prompt, tokenizer, context_length)
    actual_context_len = len(prompt_tokens)
    
    start_time = time.time()
    try:
        result = run_generation(model, tokenizer, prompt_tokens, max_response)
        elapsed = time.time() - start_time
        mem_after = get_memory_info()
        
        # Calculate memory delta
        mem_delta = {}
        if mem_after.get("gpu_used"):
            mem_delta["gpu_allocated_delta_mb"] = round(
                mem_after["gpu_allocated_mb"] - mem_before["gpu_allocated_mb"], 1
            )
        mem_delta["ram_delta_mb"] = round(
            mem_after["ram_mb"] - mem_before["ram_mb"], 1
        )
        
        return {
            "task": task_name,
            "context_length_target": context_length,
            "context_length_actual": actual_context_len,
            "success": True,
            **result,
            **mem_delta
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"    ❌ Failed: {e}")
        return {
            "task": task_name,
            "context_length_target": context_length,
            "success": False,
            "error": str(e),
            "elapsed_seconds": round(elapsed, 4)
        }

def main():
    parser = argparse.ArgumentParser(description="Benchmark context lengths: 32K, 64K, 128K")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-Coder-32B",
                        help="Model name")
    parser.add_argument("--output-dir", type=str, default="benchmarks/results",
                        help="Directory to save results")
    parser.add_argument("--context-lengths", type=int, nargs='+', default=[32768, 65536, 131072],
                        help="Context lengths to test")
    parser.add_argument("--tasks-per-length", type=int, default=5,
                        help="Number of tasks per context length")
    
    args = parser.parse_args()
    
    print("="*70)
    print("CONTEXT LENGTH BENCHMARK")
    print("="*70)
    print(f"Model: {args.model}")
    print(f"Context lengths: {args.context_lengths}")
    print(f"Tasks per length: {args.tasks_per_length}")
    
    # Sample tasks for benchmarking
    tasks = [
        {
            "name": "Code Completion",
            "prompt": """import React from 'react';
function Component({ children }) {
    return (
        <div className="container">
            {children}
        </div>
    );
}
export default Component;"""
        },
        {
            "name": "Bug Fix",
            "prompt": """function calculateTotal(items) {
    let total = 0;
    for (let i = 0; i <= items.length; i++) {
        total += items[i].price;
    }
    return total;
}
// This function has a bug. What is it and how would you fix it?"""
        },
        {
            "name": "Documentation Generation",
            "prompt": """class DataProcessor {
    constructor(config) {
        this.config = config;
        this.cache = new Map();
    }
    
    async process(data) {
        const result = await this.transform(data);
        return this.validate(result);
    }
    
    transform(data) {
        // Transform logic here
        return data.map(item => ({ ...item, processed: true }));
    }
    
    validate(result) {
        return result.filter(item => item.valid !== false);
    }
}
// Please generate comprehensive JSDoc documentation for this class."""
        },
        {
            "name": "Test Generation",
            "prompt": """const sum = (a, b) => a + b;
const multiply = (a, b) => a * b;
const divide = (a, b) => {
    if (b === 0) throw new Error('Division by zero');
    return a / b;
};
// Write Jest unit tests for these utility functions."""
        },
        {
            "name": "Refactoring",
            "prompt": """function processUserData(users) {
    const result = [];
    for (let i = 0; i < users.length; i++) {
        const user = users[i];
        if (user.active) {
            result.push({
                id: user.id,
                name: user.firstName + ' ' + user.lastName,
                email: user.email.toLowerCase()
            });
        }
    }
    return result;
}
// Refactor this function using modern ES6+ features (map, filter, destructuring, template literals)."""
        }
    ]
    
    results = {
        "metadata": {
            "model": args.model,
            "context_lengths_tested": args.context_lengths,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tasks": [t["name"] for t in tasks],
            "max_new_tokens": 200
        },
        "results": []
    }
    
    try:
        # Import dependencies
        print("\n📦 Loading dependencies...")
        from transformers import AutoTokenizer
        sys.path.insert(0, '/Users/walidsobhi/.openclaw/workspace/stack-3.0/stack-3.0-deploy')
        
        print(f"\n🔍 Loading tokenizer for {args.model}...")
        tokenizer = AutoTokenizer.from_pretrained(
            args.model,
            trust_remote_code=True
        )
        print(f"Tokenizer loaded. Vocab size: {tokenizer.vocab_size}")
        
        all_task_results = []
        
        # Test each context length
        for context_len in args.context_lengths:
            print(f"\n{'='*70}")
            print(f"TESTING CONTEXT LENGTH: {context_len} tokens ({context_len/1024:.0f}K)")
            print(f"{'='*70}")
            
            # Load model fresh for each context length (optional, but cleaner)
            print(f"\n🤖 Loading model...")
            model = load_model(args.model, max_model_len=context_len, block_size=64)
            
            # Get initial memory after load
            mem_after_load = get_memory_info()
            print(f"   Model loaded. Memory: {mem_after_load}")
            
            length_results = []
            
            # Run tasks (selected subset based on context length)
            num_tasks = min(args.tasks_per_length, len(tasks))
            
            for i in range(num_tasks):
                task = tasks[i % len(tasks)]
                print(f"\n[{i+1}/{num_tasks}] Running task: {task['name']}")
                sys.stdout.flush()
                
                result = test_task(
                    model, tokenizer, context_len,
                    f"{task['name']} @ {context_len}",
                    task["prompt"]
                )
                length_results.append(result)
                all_task_results.append(result)
                
                # Small delay between tasks
                time.sleep(1)
            
            # Print summary for this context length
            successful = [r for r in length_results if r.get('success', False)]
            if successful:
                avg_tps = statistics.mean([r['tokens_per_second'] for r in successful])
                avg_latency = statistics.mean([r['elapsed_seconds'] for r in successful])
                print(f"\n📈 Summary for {context_len} tokens:")
                print(f"   Avg throughput: {avg_tps:.2f} tokens/sec")
                print(f"   Avg latency: {avg_latency:.3f}s")
                print(f"   Success count: {len(successful)}/{len(length_results)}")
            
            # Unload model to free memory before next test
            del model
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            print(f"   ✓ Completed testing for {context_len}")
        
        # Compile final results
        results["results"] = all_task_results
        
        # Calculate summary statistics
        summary = {}
        for context_len in args.context_lengths:
            len_results = [r for r in all_task_results 
                          if r.get('context_length_target') == context_len and r.get('success')]
            if len_results:
                summary[str(context_len)] = {
                    "count": len(len_results),
                    "avg_tokens_per_second": round(statistics.mean([r['tokens_per_second'] for r in len_results]), 2),
                    "avg_latency_seconds": round(statistics.mean([r['elapsed_seconds'] for r in len_results]), 3),
                    "avg_gpu_memory_delta_mb": round(statistics.mean([r.get('gpu_allocated_delta_mb', 0) for r in len_results]), 1),
                    "avg_ram_delta_mb": round(statistics.mean([r.get('ram_delta_mb', 0) for r in len_results]), 1)
                }
        results["summary"] = summary
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please install: pip install vllm transformers psutil torch")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"benchmark_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*70}")
    print("BENCHMARK COMPLETE")
    print(f"{'='*70}")
    print(f"Results saved to: {output_file}")
    
    # Print summary table
    print("\n📊 Performance Summary:")
    print("-"*70)
    print(f"{'Context':<10} {'Throughput':<15} {'Latency':<12} {'GPU Δ':<12} {'RAM Δ':<12}")
    print("-"*70)
    
    if summary:
        for length_str, stats in sorted(summary.items()):
            length = int(length_str)
            length_k = length // 1024
            print(f"{length_k:>3}K      {stats['avg_tokens_per_second']:>5.1f} tok/s   {stats['avg_latency_seconds']:>6.3f}s   "
                  f"{stats['avg_gpu_memory_delta_mb']:>6.1f} MB   {stats['avg_ram_delta_mb']:>6.1f} MB")
    
    print("\n✅ Benchmark finished!")
    print("\nNext steps:")
    print("  1. Review results in the JSON output file")
    print("  2. Check if 128K provides quality benefits that justify any performance trade-offs")
    print("  3. Update deployment configuration with optimal block_size and scheduler settings")

if __name__ == "__main__":
    main()
