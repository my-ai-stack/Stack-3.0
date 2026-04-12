import json
import sys
import os
from pathlib import Path

def convert_to_markdown(json_path):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        model = data.get('model', 'Unknown')
        date = data.get('evaluation_date', 'Unknown')
        time = data.get('total_time_seconds', 0)

        md = f"# 🚀 Evaluation Results: {model}\n\n"
        md += f"**Date:** {date} | **Total Time:** {time}s\n\n"

        md += "## 💻 Code Generation\n"
        md += "| Benchmark | Pass@1 | Pass@10 |\n"
        md += "|---|---|---|\n"

        he = data.get('humaneval', {})
        mbpp = data.get('mbpp', {})
        md += f"| HumanEval | {he.get('pass_at_1', 'N/A')} | {he.get('pass_at_10', 'N/A')} |\n"
        md += f"| MBPP | {mbpp.get('pass_at_1', 'N/A')} | {mbpp.get('pass_at_10', 'N/A')} |\n\n"

        md += "## 🛠️ Tool Use\n"
        md += "| Metric | Value |\n"
        md += "|---|---|\n"
        tu = data.get('tool_use', {})
        md += f"| Selection Accuracy | {tu.get('tool_selection_accuracy', 'N/A')} |\n"
        md += f"| Parameter Accuracy | {tu.get('parameter_accuracy', 'N/A')} |\n"
        md += f"| Success Rate | {tu.get('execution_success_rate', 'N/A')} |\n\n"

        md += "## 📈 Self-Improvement\n"
        md += "| Metric | Value |\n"
        md += "|---|---|\n"
        si = data.get('self_improvement', {})
        md += f"| Memory Retention | {si.get('memory_retention_rate', 'N/A')} |\n"
        md += f"| Pattern Accuracy | {si.get('pattern_application_accuracy', 'N/A')} |\n"
        md += f"| Improvement Rate | {si.get('improvement_rate', 'N/A')} |\n"

        return md
    except Exception as e:
        return f"Error processing summary: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 summarize_results.py <path_to_benchmark_summary.json>")
        sys.exit(1)

    json_file = sys.argv[1]
    markdown_output = convert_to_markdown(json_file)

    # Write to GitHub Step Summary if GITHUB_STEP_SUMMARY env var exists
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_file:
        with open(summary_file, 'a') as f:
            f.write(markdown_output)
    else:
        print(markdown_output)
