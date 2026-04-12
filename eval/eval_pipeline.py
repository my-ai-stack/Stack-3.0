"""
Main evaluation pipeline for Stack 3.0
Runs standard benchmarks and compares with base Qwen2.5-Coder-32B
"""

import os
import json
import argparse
import numpy as np
from datetime import datetime
from pathlib import Path

# Add benchmarks directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent / "benchmarks"))

# Standard benchmarks
from human_eval import HumanEval
from mbpp import MBPP
from gsm8k import GSM8K
from bigbench import BIGBenchHard

class Stack29Evaluator:
    def __init__(self, model_name, base_model_name="qwen2.5-coder-32b", output_dir="results"):
        self.model_name = model_name
        self.base_model_name = base_model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize benchmarks
        self.benchmarks = {
            "HumanEval": HumanEval(),
            "MBPP": MBPP(),
            "GSM8K": GSM8K(),
            "BIG-Bench Hard": BIGBenchHard()
        }
        
        self.results = {}
        
    def run_all_benchmarks(self):
        """Run all standard benchmarks"""
        print(f"Running benchmarks for {self.model_name}...")
        
        for name, benchmark in self.benchmarks.items():
            print(f"\nRunning {name}...")
            self.results[name] = self._run_benchmark(benchmark)
            
        return self.results
    
    def _run_benchmark(self, benchmark):
        """Run a single benchmark and return results"""
        results = benchmark.evaluate(self.model_name)
        return {
            "pass_at_1": results.get("pass_at_1", 0),
            "pass_at_3": results.get("pass_at_3", 0),
            "pass_at_5": results.get("pass_at_5", 0),
            "total_cases": results.get("total_cases", 0),
            "accuracy": results.get("accuracy", 0)
        }
    
    def compare_with_base(self):
        """Compare results with base model"""
        base_results = {}
        
        # Run base model benchmarks
        base_evaluator = Stack29Evaluator(self.base_model_name, output_dir=self.output_dir)
        base_results = base_evaluator.run_all_benchmarks()
        
        comparison = {}
        
        for benchmark_name in self.results:
            current = self.results[benchmark_name]
            base = base_results[benchmark_name]
            
            comparison[benchmark_name] = {
                "current": current,
                "base": base,
                "improvement": {
                    "pass_at_1": self._calculate_improvement(current["pass_at_1"], base["pass_at_1"]),
                    "pass_at_3": self._calculate_improvement(current["pass_at_3"], base["pass_at_3"]),
                    "pass_at_5": self._calculate_improvement(current["pass_at_5"], base["pass_at_5"]),
                    "accuracy": self._calculate_improvement(current["accuracy"], base["accuracy"])
                }
            }
        
        return comparison
    
    def _calculate_improvement(self, current, base):
        """Calculate percentage improvement"""
        if base == 0:
            return float('inf') if current > 0 else 0
        return ((current - base) / base) * 100
    
    def save_results(self):
        """Save all results to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw results
        results_path = self.output_dir / f"results_{timestamp}.json"
        with open(results_path, 'w') as f:
            json.dump({
                "model": self.model_name,
                "timestamp": timestamp,
                "results": self.results
            }, f, indent=2)
        
        # Save comparison
        comparison_path = self.output_dir / f"comparison_{timestamp}.json"
        with open(comparison_path, 'w') as f:
            json.dump({
                "model": self.model_name,
                "base_model": self.base_model_name,
                "timestamp": timestamp,
                "comparison": self.compare_with_base()
            }, f, indent=2)
        
        print(f"Results saved to {results_path}")
        print(f"Comparison saved to {comparison_path}")
        
        return results_path, comparison_path
    
    def generate_summary(self):
        """Generate markdown summary of results"""
        summary = f"""# Stack 3.0 Evaluation Results - {self.model_name}

## Summary
Evaluation results for Stack 3.0 compared with base {self.base_model_name}.

## Benchmarks

"""
        
        for name, result in self.results.items():
            summary += f"""### {name}

- Pass@1: {result['pass_at_1']}/{result['total_cases']} ({result['accuracy']*100:.2f}%)
- Pass@3: {result.get('pass_at_3', 0)}/{result['total_cases']}
- Pass@5: {result.get('pass_at_5', 0)}/{result['total_cases']}

"""
        
        return summary


def main():
    parser = argparse.ArgumentParser(description='Evaluate Stack 3.0')
    parser.add_argument('--model', required=True, help='Model name to evaluate')
    parser.add_argument('--base-model', default='qwen2.5-coder-32b', help='Base model name for comparison')
    parser.add_argument('--output', default='results', help='Output directory')
    
    args = parser.parse_args()
    
    evaluator = Stack29Evaluator(args.model, args.base_model, args.output)
    evaluator.run_all_benchmarks()
    evaluator.save_results()
    
    print(evaluator.generate_summary())


if __name__ == "__main__":
    main()