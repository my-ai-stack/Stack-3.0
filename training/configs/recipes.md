# Training Recipes

This document describes the recommended training configurations for different hardware setups and model sizes.

---

## Recipe 1: 1.5B on T4 (Current Setup)

**Use Case:** Free-tier / budget training, experimentation  
**Hardware:** Google Colab T4 (16GB VRAM) or equivalent  
**Training Type:** QLoRA (4-bit quantization + LoRA adapters)

### Specifications

| Parameter | Value |
|-----------|-------|
| Base Model | Qwen/Qwen2.5-Coder-1.5B |
| Quantization | 4-bit (NF4) |
| LoRA Rank (r) | 32 |
| LoRA Alpha | 64 |
| Target Modules | q_proj, k_proj, v_proj, o_proj |
| Max Sequence Length | 8,192 |
| Batch Size | 1 |
| Gradient Accumulation Steps | 16 |
| Learning Rate | 2e-4 |
| Warmup Steps | 100 |
| Epochs | 3 |
| Precision | FP16 (T4 no BF16) |

### Expected Runtime
- ~2-3 hours per epoch on T4
- Total: ~6-9 hours for 3 epochs

### Memory Requirements
- VRAM: ~12-14GB
- RAM: ~10GB
- Disk: ~5GB for model + data

### Tips for T4
- Enable `gradient_checkpointing=True` to save memory
- Use `optim="paged_adamw_32bit"` if available
- Keep `max_seq_length` at 8192 to avoid OOM
- Monitor GPU memory with `nvidia-smi`

---

## Recipe 2: 7B QLoRA on T4 (Cost-Effective)

**Use Case:** Better quality than 1.5B, still budget-friendly  
**Hardware:** Google Colab T4 (16GB VRAM)  
**Training Type:** QLoRA with aggressive memory optimization

### Specifications

| Parameter | Value |
|-----------|-------|
| Base Model | Qwen/Qwen2.5-Coder-7B |
| Quantization | 4-bit (NF4) |
| LoRA Rank (r) | 64 |
| LoRA Alpha | 128 |
| Target Modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Max Sequence Length | 4,096 |
| Batch Size | 1 |
| Gradient Accumulation Steps | 32 |
| Learning Rate | 1e-4 |
| Warmup Steps | 100 |
| Epochs | 3 |
| Precision | FP16 |

### Expected Runtime
- ~4-6 hours per epoch on T4
- Total: ~12-18 hours for 3 epochs

### Memory Requirements
- VRAM: ~14-15GB (nearly maxed)
- RAM: ~12GB
- Disk: ~10GB for model + data

### Critical Optimizations for 7B on T4
```yaml
# Enable these settings in your config:
gradient_checkpointing: true
use_gradient_checkpointing: true
gradient_checkpointing_kwargs:
  use_reentrant: false

# Use optimized attention
torch_dtype: float16
attn_implementation: "flash_attention_2"  # if supported

# Optimizer settings
optim: "paged_adamw_32bit"
lr_scheduler_type: "cosine"
```

### Tips
- This is the **sweet spot** for Colab training
- Consider using gradient accumulation with smaller batch size
- Save checkpoints frequently (T4 can be unstable)
- Use `push_to_hub` incrementally to backup progress

---

## Recipe 3: 7B on A100 (Recommended for Production)

**Use Case:** Production training, best quality per dollar  
**Hardware:** A100 80GB (AWS g5.xlarge, Lambda Labs, etc.)  
**Training Type:** QLoRA or Full Fine-tune (depending on resources)

### Specifications

| Parameter | Value |
|-----------|-------|
| Base Model | Qwen/Qwen2.5-Coder-7B |
| Quantization | 8-bit or None (FP16/BF16) |
| LoRA Rank (r) | 128 |
| LoRA Alpha | 256 |
| Target Modules | All linear layers |
| Max Sequence Length | 32,768 |
| Batch Size | 4 |
| Gradient Accumulation Steps | 8 |
| Learning Rate | 5e-5 |
| Warmup Steps | 500 |
| Epochs | 3 |
| Precision | BF16 |
| Optimizer | AdamW 8-bit (paged) |

### Expected Runtime
- ~30-45 minutes per epoch on A100
- Total: ~1.5-2.5 hours for 3 epochs

### Memory Requirements
- VRAM: ~40-60GB (with QLoRA)
- RAM: ~20GB
- Disk: ~20GB for model + data

### Full Fine-tune Option (A100 80GB)
If you have the full 80GB and want maximum quality:
```yaml
quantization: none
bf16: true
batch_size: 8
max_seq_length: 32768
lora_rank: 0  # Full fine-tune
```

### Cloud Cost Estimates (A100)
- Lambda Labs: ~$0.80/hr
- AWS g5.xlarge: ~$1.50/hr
- RunPod: ~$0.70/hr
- **Total estimated cost:** $2-5 for full training

---

## Recipe 4: 32B on Multi-A100 (Research-Grade)

**Use Case:** Research, maximum model quality, large-scale experiments  
**Hardware:** Multi-node A100 cluster or single A100 80GB with heavy optimization  
**Training Type:** QLoRA (4-bit) or 8-bit with multi-GPU

### Specifications

| Parameter | Value (Single A100) | Value (Multi-A100) |
|-----------|--------------------|--------------------|
| Base Model | Qwen/Qwen2.5-Coder-32B | Qwen/Qwen2.5-Coder-32B |
| Quantization | 4-bit (QLoRA) | 4-bit or 8-bit |
| LoRA Rank (r) | 128 | 256 |
| LoRA Alpha | 256 | 512 |
| Target Modules | All linear layers | All linear layers |
| Max Sequence Length | 16,384 | 32,768 |
| Batch Size | 1 | 4 per GPU |
| Gradient Accumulation Steps | 64 | 16 |
| Learning Rate | 5e-5 | 2e-4 |
| Warmup Steps | 500 | 200 |
| Epochs | 3 | 3 |
| Precision | BF16 | BF16 |
| GPUs Required | 1 (80GB) | 4x A100 80GB |

### Expected Runtime
- **Single A100 80GB:** ~3-4 hours per epoch (very slow due to swaps)
- **4x A100:** ~45-60 minutes per epoch
- Total: ~2.5-12 hours depending on setup

### Memory Optimization for 32B on Single A100
```yaml
# Extreme memory saving measures
gradient_checkpointing: true
use_reentrant: false
optim: "paged_adamw_32bit"

# Sequence packing for efficiency
group_by_length: false
max_packed_sequence_length: 16384

# Lower sequence length to fit in memory
max_seq_length: 8192  # Minimum for 32B on single A100
```

### Multi-GPU Setup (Recommended for 32B)
```yaml
# For 4x A100 80GB cluster
deepspeed_config:
  stage: 3
  offload_optimizer: false
  offload_param: false
  nvme_offload_params:
    offload_param_size: 500GB
    offload_optimizer_size: 100GB
    nvme_path: "/tmp"
  
# Or use FSDP
fsdp_config:
  backward_prefetch: "backward_pre"
  auto_wrap_policy: "transformer_auto_wrap_policy"
  mixed_precision: true
```

### Cloud Cost Estimates (32B)
- **Single A100 80GB:** ~$3/hr (impractical due to slow training)
- **4x A100 80GB:** ~$12/hr
- **Total estimated cost:** $50-150 for full training

### When to Use 32B
- ✅ Research with publishable results
- ✅ Need maximum code completion quality
- ✅ Budget allows for multi-GPU training
- ❌ NOT for: experimentation, quick iterations, budget training

---

## Quick Reference Table

| Recipe | Model | GPU | VRAM | Time/Epoch | Total Time | Quality |
|--------|-------|-----|------|------------|------------|---------|
| 1 | 1.5B QLoRA | T4 | 16GB | 2-3h | 6-9h | Good |
| 2 | 7B QLoRA | T4 | 16GB | 4-6h | 12-18h | Better |
| 3 | 7B QLoRA | A100 | 80GB | 30-45m | 1.5-2.5h | Best |
| 4 | 32B QLoRA | 4xA100 | 320GB | 45-60m | 2.5-4h | Research |

---

## Choosing the Right Recipe

### Start Here:
1. **New to training?** → Recipe 1 (1.5B on T4)
2. **Need better quality?** → Recipe 2 (7B QLoRA on T4)
3. **Production needs?** → Recipe 3 (7B on A100)
4. **Research project?** → Recipe 4 (32B on multi-A100)

### Questions to Ask:
- What's your budget?
- How much time do you have?
- What quality level do you need?
- Are you experimenting or doing final training?

### My Recommendation:
For most use cases, **Recipe 3 (7B on A100)** offers the best balance of quality, cost, and training time. If budget is tight, **Recipe 2 (7B QLoRA on T4)** is the next best option.

---

## Troubleshooting

### OOM Errors (Out of Memory)
- Reduce `max_seq_length` by half
- Enable `gradient_checkpointing`
- Reduce `batch_size` to 1
- Disable `flash_attention_2`

### Slow Training
- Check if using GPU (not CPU)
- Reduce `max_seq_length`
- Enable `gradient_checkpointing` (tradeoff: slower but can use larger batch)
- Use `torch.compile()` if available

### Loss Not Decreasing
- Check learning rate (try 10x smaller)
- Verify data format is correct
- Increase `warmup_steps`
- Check for data leakage

### Poor Quality Results
- Increase training epochs (but watch for overfitting)
- Use a larger `lora_alpha` relative to `lora_r`
- Increase `max_seq_length` if data has long contexts
- Add more diverse training data
