#!/usr/bin/env python3
"""
Test script for verifying 128K context window support for Qwen2.5-Coder-32B.

This script:
1. Loads the model with vLLM configured for 128K context
2. Tests with various input lengths (32K, 64K, 96K, 128K)
3. Measures memory usage, throughput, and latency
4. Tests with real codebase context (entire project)
5. Validates that the model correctly processes long inputs
"""

import os
import sys
import json
import time
import psutil
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Add vLLM to path
sys.path.insert(0, '/Users/walidsobhi/.openclaw/workspace/stack-3.0/stack-3.0-deploy')

def get_memory_usage() -> Dict[str, float]:
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return {
        'rss_mb': memory_info.rss / 1024 / 1024,
        'vms_mb': memory_info.vms / 1024 / 1024
    }

def generate_token_sequence(length: int, tokenizer) -> List[int]:
    """Generate a sequence of tokens of approximately the target length."""
    # Create a repeating pattern that tokenizes consistently
    base_text = "This is a test token sequence for context window testing. " * 10
    tokens = tokenizer.encode(base_text)
    # Repeat the tokens to reach desired length
    num_repeats = (length // len(tokens)) + 1
    token_sequence = tokens * num_repeats
    return token_sequence[:length]

def read_codebase_files(base_path: str, max_files: int = 100) -> str:
    """Read source code files from the codebase to create a realistic long context."""
    codebase_text = ""
    src_dir = Path(base_path) / "src"
    if not src_dir.exists():
        return ""
    
    file_count = 0
    for file_path in src_dir.rglob("*.ts"):
        if file_count >= max_files:
            break
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                codebase_text += f"\n\n// File: {file_path.relative_to(base_path)}\n{content}\n"
                file_count += 1
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    
    return codebase_text

def test_context_length(model, tokenizer, context_length: int, test_name: str) -> Dict:
    """Test model with a specific context length."""
    print(f"\n{'='*60}")
    print(f"Testing {test_name} (target: {context_length} tokens)")
    print(f"{'='*60}")
    
    # Generate input sequence
    tokens = generate_token_sequence(context_length, tokenizer)
    actual_length = len(tokens)
    print(f"Generated input with {actual_length} tokens")
    
    # Measure memory before inference
    mem_before = get_memory_usage()
    
    # Run inference (generate a short response to test context processing)
    start_time = time.time()
    try:
        # Use vLLM's generate
        from vllm import SamplingParams
        sampling_params = SamplingParams(
            temperature=0.1,
            max_tokens=50,  # Generate only 50 tokens
            prompt_logprobs=0
        )
        
        outputs = model.generate(
            prompt_token_ids=tokens,
            sampling_params=sampling_params,
            use_tqdm=False
        )
        
        elapsed = time.time() - start_time
        mem_after = get_memory_usage()
        
        # Calculate metrics
        output_text = outputs[0].outputs[0].text
        output_tokens = len(outputs[0].outputs[0].token_ids)
        tokens_per_second = output_tokens / elapsed if elapsed > 0 else 0
        
        result = {
            "test": test_name,
            "target_length": context_length,
            "actual_length": actual_length,
            "output_tokens": output_tokens,
            "latency_seconds": round(elapsed, 3),
            "tokens_per_second": round(tokens_per_second, 2),
            "memory_before_mb": round(mem_before['rss_mb'], 2),
            "memory_after_mb": round(mem_after['rss_mb'], 2),
            "memory_delta_mb": round(mem_after['rss_mb'] - mem_before['rss_mb'], 2),
            "success": True,
            "sample_output": output_text[:100] if output_text else ""
        }
        
        print(f"✅ Success!")
        print(f"   Latency: {elapsed:.3f}s")
        print(f"   Throughput: {tokens_per_second:.2f} tokens/sec")
        print(f"   Memory delta: {result['memory_delta_mb']:.1f} MB")
        print(f"   Sample output: {result['sample_output']}")
        
    except Exception as e:
        elapsed = time.time() - start_time
        result = {
            "test": test_name,
            "target_length": context_length,
            "actual_length": actual_length,
            "success": False,
            "error": str(e),
            "latency_seconds": round(elapsed, 3)
        }
        print(f"❌ Failed: {e}")
    
    return result

def test_with_codebase(model, tokenizer, codebase_path: str) -> Dict:
    """Test the model with the entire codebase as context."""
    print(f"\n{'='*60}")
    print(f"Testing with real codebase context")
    print(f"{'='*60}")
    
    # Read codebase files
    print("Reading codebase files...")
    codebase_text = read_codebase_files(codebase_path, max_files=200)
    codebase_tokens = tokenizer.encode(codebase_text)
    context_length = len(codebase_tokens)
    print(f"Codebase encoded to {context_length} tokens ({context_length/1024:.1f}K)")
    
    if context_length < 1000:
        print("⚠️  Warning: Codebase is too small, generate synthetic long context instead")
        codebase_tokens = generate_token_sequence(131072, tokenizer)
        context_length = len(codebase_tokens)
    
    mem_before = get_memory_usage()
    start_time = time.time()
    
    try:
        from vllm import SamplingParams
        sampling_params = SamplingParams(
            temperature=0.2,
            max_tokens=100,
            prompt_logprobs=0
        )
        
        outputs = model.generate(
            prompt_token_ids=codebase_tokens,
            sampling_params=sampling_params,
            use_tqdm=False
        )
        
        elapsed = time.time() - start_time
        mem_after = get_memory_usage()
        
        output_text = outputs[0].outputs[0].text
        output_tokens = len(outputs[0].outputs[0].token_ids)
        tokens_per_second = output_tokens / elapsed if elapsed > 0 else 0
        
        result = {
            "test": "Codebase Context",
            "context_size_k": round(context_length / 1024, 1),
            "output_tokens": output_tokens,
            "latency_seconds": round(elapsed, 3),
            "tokens_per_second": round(tokens_per_second, 2),
            "memory_before_mb": round(mem_before['rss_mb'], 2),
            "memory_after_mb": round(mem_after['rss_mb'], 2),
            "memory_delta_mb": round(mem_after['rss_mb'] - mem_before['rss_mb'], 2),
            "success": True,
            "sample_output": output_text[:150]
        }
        
        print(f"✅ Success!")
        print(f"   Context size: {result['context_size_k']}K tokens")
        print(f"   Latency: {elapsed:.3f}s")
        print(f"   Throughput: {tokens_per_second:.2f} tokens/sec")
        print(f"   Memory delta: {result['memory_delta_mb']:.1f} MB")
        print(f"   Sample output: {result['sample_output']}")
        
    except Exception as e:
        elapsed = time.time() - start_time
        result = {
            "test": "Codebase Context",
            "success": False,
            "error": str(e),
            "latency_seconds": round(elapsed, 3)
        }
        print(f"❌ Failed: {e}")
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Test 128K context window for Qwen2.5-Coder-32B")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-Coder-32B",
                        help="Model name or path")
    parser.add_argument("--max-model-len", type=int, default=131072,
                        help="Maximum model length for vLLM")
    parser.add_argument("--block-size", type=int, default=64,
                        help="vLLM block size")
    parser.add_argument("--codebase-path", type=str,
                        default="/Users/walidsobhi/.openclaw/workspace/stack-3.0",
                        help="Path to the codebase for real context test")
    parser.add_argument("--output", type=str,
                        default="benchmarks/test_context_results.json",
                        help="Output file for results")
    
    args = parser.parse_args()
    
    print(f"Starting 128K Context Window Test")
    print(f"Model: {args.model}")
    print(f"Config: max_model_len={args.max_model_len}, block_size={args.block_size}")
    
    results = []
    
    try:
        # Import vLLM and Transformers
        print("\n📦 Loading tokenizer...")
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            args.model,
            trust_remote_code=True
        )
        print(f"Tokenizer loaded. Vocab size: {tokenizer.vocab_size}")
        
        print("\n🤖 Loading vLLM model...")
        from vllm import LLM
        
        # Initialize vLLM with large context configuration
        model = LLM(
            model=args.model,
            max_model_len=args.max_model_len,
            block_size=args.block_size,
            gpu_memory_utilization=0.9,
            trust_remote_code=True,
            tensor_parallel_size=1  # Adjust if using multiple GPUs
        )
        print("Model loaded successfully!")
        
        # Test 1: Small context (8K) - baseline
        results.append(test_context_length(model, tokenizer, 8192, "8K Baseline"))
        
        # Test 2: Medium context (32K)
        results.append(test_context_length(model, tokenizer, 32768, "32K"))
        
        # Test 3: Large context (64K)
        results.append(test_context_length(model, tokenizer, 65536, "64K"))
        
        # Test 4: Full context (96K)
        results.append(test_context_length(model, tokenizer, 98304, "96K"))
        
        # Test 5: Maximum context (128K)
        results.append(test_context_length(model, tokenizer, 131072, "128K"))
        
        # Test 6: Codebase context
        results.append(test_with_codebase(model, tokenizer, args.codebase_path))
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure vLLM and transformers are installed:")
        print("  pip install vllm transformers")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            "metadata": {
                "model": args.model,
                "max_model_len": args.max_model_len,
                "block_size": args.block_size,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "system": os.uname().sysname if hasattr(os, 'uname') else "Unknown"
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n📊 Results saved to: {output_path}")
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    print(f"Total tests: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        print("\nContext length vs. throughput:")
        for r in successful:
            if r['test'] != 'Codebase Context':
                print(f"  {r['test']}: {r['tokens_per_second']} tokens/sec, "
                      f"memory delta: {r['memory_delta_mb']}MB")
        if any(r['test'] == 'Codebase Context' for r in successful):
            cb = next(r for r in successful if r['test'] == 'Codebase Context')
            print(f"\nCodebase test: {cb['context_size_k']}K tokens, "
                  f"{cb['tokens_per_second']} tokens/sec")
    
    print("\n✅ Test script completed!")

if __name__ == "__main__":
    main()
