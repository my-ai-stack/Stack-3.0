#!/bin/bash
# Stack 3.0 Quick HumanEval Evaluation Wrapper
# Usage: ./quick_human_eval.sh [provider] [model] [num_samples]
# Example: ./quick_human_eval.sh ollama qwen2.5-coder:32b 20

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Defaults
PROVIDER="${1:-ollama}"
MODEL="${2:-gemma4:31b-cloud}"
MAX_PROBLEMS="${3:-20}"

echo "========================================"
echo "Stack 3.0 HumanEval Quick Evaluation"
echo "========================================"
echo "Provider: $PROVIDER"
echo "Model: $MODEL"
echo "Problems: $MAX_PROBLEMS"
echo ""

# Check if vllm is available
if command -v vllm &> /dev/null; then
    USE_VLLM="--use-vllm"
    echo "✓ vLLM detected - will use for faster inference"
else
    USE_VLLM=""
    echo "⚠ vLLM not found - using standard inference"
fi

# Check provider availability
case "$PROVIDER" in
    ollama)
        if command -v ollama &> /dev/null; then
            echo "✓ Ollama available"
            # Check if model is loaded
            if curl -s http://localhost:11434/api/tags &> /dev/null; then
                echo "✓ Ollama server running"
            else
                echo "⚠ Ollama server not running - start with: ollama serve"
            fi
        else
            echo "⚠ Ollama not installed - will attempt anyway"
        fi
        ;;
    openai)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "⚠ OPENAI_API_KEY not set"
        else
            echo "✓ OpenAI API key configured"
        fi
        ;;
    anthropic)
        if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo "⚠ ANTHROPIC_API_KEY not set"
        else
            echo "✓ Anthropic API key configured"
        fi
        ;;
esac

echo ""
echo "Running evaluation..."
echo "----------------------------------------"

# Run the evaluation
python3 -m benchmarks.human_eval \
    --provider "$PROVIDER" \
    --model "$MODEL" \
    --max-problems "$MAX_PROBLEMS" \
    --timeout 30 \
    $USE_VLLM

echo ""
echo "========================================"
echo "Evaluation complete!"
echo "========================================"
echo ""
echo "Results saved to: results/humaneval.json"
echo ""
echo "To run full 164-problem benchmark:"
echo "  1. Download full HumanEval dataset"
echo "  2. Use GPU with 80GB VRAM (A100/H100)"
echo "  3. See HUMAN_EVAL_PLAN.md for details"