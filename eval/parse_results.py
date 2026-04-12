import json
import os

def parse_results():
    results = {}
    files = ['results_humaneval.json', 'results_mbpp.json']

    for file in files:
        path = os.path.join('eval', file)
        if os.path.exists(path):
            with open(path, 'r') as f:
                results[file] = json.load(f)

    with open('eval/summary.md', 'w') as f:
        f.write("# Model Evaluation Summary\n\n")
        f.write("| Benchmark | Pass@1 | Status |\n")
        f.write("| --- | --- | --- |\n")
        for benchmark, data in results.items():
            name = benchmark.replace('results_', '').replace('.json', '').upper()
            f.write(f"| {name} | {data.get('pass@1', 'N/A')} | {data.get('status', 'N/A')} |\n")

if __name__ == "__main__":
    parse_results()
