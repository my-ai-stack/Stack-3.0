# Stack 3.0 HumanEval Evaluation Plan

> **Status**: Pending GPU availability | **Last Updated**: 2026-04-01

This document provides complete instructions for running HumanEval benchmark evaluation on Stack 3.0.

## Quick Start (When GPU Available)

```bash
# 1. Navigate to eval directory
cd /Users/walidsobhi/.openclaw/workspace/stack-3.0/stack-3.0-eval

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run quick test (1 sample)
python3 -m benchmarks.human_eval --max-problems 1 --provider ollama

# 4. Run full evaluation (20 problems - current dataset)
python3 -m benchmarks.human_eval --max-problems 20 --provider ollama

# 5. For full 164-problem benchmark, download dataset first
# See "Full HumanEval Dataset" section below
```

## Hardware Requirements

### Recommended
- **GPU**: NVIDIA A100 80GB (or H100 80GB)
- **RAM**: 128GB system memory
- **Storage**: 50GB free space

### Minimum
- **GPU**: NVIDIA RTX 4090 (24GB VRAM) with 4-bit quantization
- **RAM**: 64GB system memory
- **Storage**: 50GB free space

### This Machine (Insufficient)
- **GPU**: Apple Silicon (M-series) - no CUDA support
- **RAM**: 16-24GB unified memory
- **Status**: Cannot run 32B model inference

## Software Setup

### Ubuntu/Debian
```bash
# Install CUDA (if not already installed)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-12-1

# Install Python dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install vllm transformers human-eval openai
```

### macOS (Intel/NVIDIA only)
```bash
# Install Python 3.10+
brew install python@3.11

# Create venv
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies (CPU-only, will be slow)
pip install torch transformers human-eval
# Note: vLLM requires CUDA - not available on macOS
```

## Running the Evaluation

### Option 1: Using Built-in Benchmark (Current)

The repo has a simplified 20-problem dataset built into `benchmarks/human_eval.py`:

```bash
cd /Users/walidsobhi/.openclaw/workspace/stack-3.0/stack-3.0-eval

# With Ollama
python3 -m benchmarks.human_eval \
  --provider ollama \
  --model qwen2.5-coder:32b \
  --max-problems 20

# With OpenAI
export OPENAI_API_KEY=your-key-here
python3 -m benchmarks.human_eval \
  --provider openai \
  --model gpt-4o \
  --max-problems 20

# With Anthropic
export ANTHROPIC_API_KEY=your-key-here
python3 -m benchmarks.human_eval \
  --provider anthropic \
  --model claude-sonnet-4-20250514 \
  --max-problems 20
```

### Option 2: Full HumanEval Dataset (164 Problems)

```bash
# Clone human-eval repository
git clone https://github.com/openai/human-eval.git
cd human-eval

# Install
pip install -e .

# Create evaluation script
cat > eval_full.py << 'EOF'
import human_eval
from human_eval.data import write_jsonl, read_jsonl
from human_eval.evaluator import evaluate

# Load problems
problems = read_jsonl("data/HumanEval.jsonl.gz")

# Generate completions (using your model)
# ... generation code ...

# Evaluate
results = evaluate("examples.jsonl")
print(f"Pass@1: {results['pass_at_1']}")
EOF
```

### Option 3: Using vLLM (Fastest)

```bash
# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --dtype half \
  --tensor-parallel-size 2

# In another terminal, run evaluation
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "def add(x, y):\n    \"\"\"\n    Add two numbers.\n    \"\"\"\n    pass",
    "max_tokens": 256
  }'
```

## Interpreting Results

### Expected Output Format
```json
{
  "pass_at_1": 14,
  "pass_at_3": 17,
  "pass_at_5": 18,
  "total_cases": 20,
  "accuracy": 0.70,
  "benchmark": "HumanEval",
  "model": "qwen2.5-coder:32b",
  "results": [
    {"task_id": 1, "passed": true, "error": null},
    {"task_id": 2, "passed": false, "error": "AssertionError"}
  ]
}
```

### Score Interpretation

| Pass@1 | Rating | Notes |
|--------|--------|-------|
| < 50% | Poor | Model struggles with basic functions |
| 50-70% | Fair | Basic competency, some gaps |
| 70-80% | Good | Solid coding ability |
| 80-90% | Excellent | Strong code generation |
| > 90% | Outstanding | Near-human performance |

### Expected Scores for Stack 3.0

| Model | Pass@1 | Pass@10 | Pass@100 |
|-------|--------|---------|----------|
| Qwen2.5-Coder-32B (baseline) | 76.8% | ~85% | ~93% |
| **Stack 3.0 (estimated)** | **78-82%** | **86-90%** | **93-95%** |

## Troubleshooting

### Out of Memory (OOM)
```
CUDA out of memory: Tried to allocate 40GB
```
**Solutions:**
1. Use quantization: `--quantization awq` or 4-bit
2. Reduce batch size: `--batch-size 1`
3. Use smaller model: Try 7B or 14B variant
4. Enable gradient checkpointing

### vLLM Errors
```
ValueError: Invalid model architecture
```
**Solutions:**
1. Update vLLM: `pip install -U vllm`
2. Check model support: https://docs.vllm.ai/en/latest/models/supported_models.html
3. Use HuggingFace backend instead

### Dataset Download Issues
```
HTTP 404: Not Found
```
**Solutions:**
1. Check URL: https://github.com/openai/human-eval/raw/main/data/HumanEval.jsonl.gz
2. Use mirror: https://huggingface.co/datasets/openai/human-eval

### Slow Inference
```
Tokens/second: < 5
```
**Solutions:**
1. Use A100/H100 GPU (10x faster than consumer cards)
2. Enable FlashAttention: `--enforce-eager` not set
3. Increase batch size for throughput testing

## Success Checklist

Before reporting results, verify:

- [ ] At least 20 problems evaluated
- [ ] Pass@1 calculated correctly (passed/total)
- [ ] Results saved to JSON file
- [ ] Model name documented
- [ ] Temperature and settings recorded
- [ ] Baseline comparison available (Qwen2.5-Coder-32B)

## Output Files

After running, these files should be created:

```
stack-3.0-eval/results/
├── humaneval.json          # Final results
├── humaneval_raw.json      # Raw model outputs
├── humaneval_errors.json   # Failed attempts with errors
└── humaneval_log.txt       # Execution log
```

## Contact

For issues or questions:
- GitHub: https://github.com/my-ai-stack/stack-3.0/issues
- Docs: See `stack-3.0-eval/README.md`

---

**Note**: This machine cannot run the evaluation due to lack of NVIDIA GPU. Estimated results are based on Qwen2.5-Coder-32B published benchmarks.