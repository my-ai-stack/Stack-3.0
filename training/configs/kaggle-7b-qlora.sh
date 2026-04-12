#!/bin/bash
# Kaggle QLoRA Training Script for Stack 2.9 on Qwen2.5-Coder-7B
# 
# Hardware: Kaggle P100 GPU (16GB VRAM)
# Expected runtime: 2-4 hours depending on dataset size
# Memory: ~6GB VRAM with QLoRA + gradient checkpointing
#
# Usage:
#   chmod +x kaggle-7b-qlora.sh
#   ./kaggle-7b-qlora.sh

set -e

# === Configuration ===
MODEL_NAME="Qwen/Qwen2.5-Coder-7B"
OUTPUT_DIR="/kaggle/working/stack-2.9-output/lora-7b-qlora"
DATA_DIR="/kaggle/working/stack-2.9/data"

# === Hyperparameters ===
# LoRA config (r=16, alpha=32)
LORA_R=16
LORA_ALPHA=32
LORA_DROPOUT=0.05

# Training config
EPOCHS=2
BATCH_SIZE=1
GRAD_ACCUM=8  # Effective = 8
LR=1e-4
MAX_LENGTH=4096  # Reduced for Kaggle memory

# === Environment Setup ===
echo "=== Setting up environment ==="
cd /kaggle/working/stack-2.9

# Install dependencies if needed
pip install -q transformers datasets peft bitsandbytes accelerate torch

# === Training Command ===
echo "=== Starting QLoRA training ==="
echo "Model: $MODEL_NAME"
echo "Output: $OUTPUT_DIR"
echo "Epochs: $EPOCHS"

python -m trl.sft \
    --model_name "$MODEL_NAME" \
    --train_files "$DATA_DIR/train.jsonl" \
    --validation_files "$DATA_DIR/val.jsonl" \
    --output_dir "$OUTPUT_DIR" \
    --per_device_train_batch_size $BATCH_SIZE \
    --gradient_accumulation_steps $GRAD_ACCUM \
    --num_train_epochs $EPOCHS \
    --learning_rate $LR \
    --max_seq_length $MAX_LENGTH \
    --logging_steps 10 \
    --save_steps 500 \
    --save_total_limit 2 \
    --bf16 true \
    --gradient_checkpointing true \
    --lora_r $LORA_R \
    --lora_alpha $LORA_ALPHA \
    --lora_dropout $LORA_DROPOUT \
    --target_modules q_proj k_proj v_proj o_proj gate_proj up_proj down_proj \
    --load_in_4bit true \
    --bnb_4bit_compute_dtype "bfloat16" \
    --bnb_4bit_quant_type "nf4" \
    --bnb_4bit_use_double_quant true

echo "=== Training complete ==="
echo "LoRA adapters saved to: $OUTPUT_DIR"

# Optional: Merge and save merged model
echo "=== Merging adapter ==="
python merge_simple.py \
    --base_model "$MODEL_NAME" \
    --lora_adapter "$OUTPUT_DIR" \
    --output_dir "$OUTPUT_DIR/merged"

echo "=== Done ==="