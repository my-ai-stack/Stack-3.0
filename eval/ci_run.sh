#!/bin/bash
# =============================================================================
# CI Wrapper for Stack Evaluation Pipeline
# =============================================================================
# This script wraps the full benchmark suite for CI/CD environments.
# It ensures the environment is set up correctly and handles errors for GH Actions.
# =============================================================================

set -e

# Configuration
MODEL="${CI_MODEL:-stack-3.0}"
OUTPUT_DIR="eval_results"
SAMPLED_SIZE="10" # Default sample size for CI to keep it fast
SKIP_SLOW="1"     # Skip slow benchmarks by default in CI

echo "--- Starting CI Evaluation Pipeline ---"
echo "Model: $MODEL"
echo "Output Directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run the full benchmark suite
# Using absolute path to ensure it runs from root
./eval/run_all_benchmarks.sh \
    --model "$MODEL" \
    --output "$OUTPUT_DIR" \
    --skip-slow \
    --sample-size "$SAMPLED_SIZE" \
    --verbose

echo "--- Evaluation Pipeline Completed ---"
