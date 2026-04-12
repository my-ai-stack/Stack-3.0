# Training Configs

This directory contains pre-configured training recipes and scripts for different hardware configurations.

## 📁 Files

| File | Description |
|------|-------------|
| `recipes.md` | Comprehensive documentation of all training recipes |
| `t4-qlora.yaml` | Optimized QLoRA configuration for T4 GPUs (16GB VRAM) |
| `local-pretrain.sh` | Auto-detecting training script for local hardware |
| `README.md` | This guide |

---

## 🚀 Quick Start

### 1. Auto-Detect & Train (Recommended)

```bash
cd training-configs
chmod +x local-pretrain.sh

# Interactive mode (will ask questions)
./local-pretrain.sh

# Auto mode (uses detected GPU, default 7B model)
./local-pretrain.sh --auto

# Auto mode with specific model
./local-pretrain.sh --auto 1.5B
```

### 2. Manual Configuration

```bash
# Check what GPU you have
nvidia-smi

# Choose the right config based on your GPU:
# - T4 (16GB): Use t4-qlora.yaml
# - A100 (80GB): Use recipes.md Recipe 3
# - Multi-A100: Use recipes.md Recipe 4

# Run training with your chosen config
python train.py --config training-configs/t4-qlora.yaml
```

---

## 📊 Which Config Should I Use?

### By GPU Type

| Your GPU | Recommended Config | Model Size | Quality |
|----------|-------------------|------------|---------|
| **T4** (Colab) | `t4-qlora.yaml` | 7B QLoRA | ⭐⭐⭐ |
| **RTX 3060/3070** | `t4-qlora.yaml` (adjusted) | 3B QLoRA | ⭐⭐ |
| **RTX 3090/4080** | `t4-qlora.yaml` (adjusted) | 7B QLoRA | ⭐⭐⭐ |
| **A100 40GB** | Recipe 3 in `recipes.md` | 7B QLoRA | ⭐⭐⭐⭐ |
| **A100 80GB** | Recipe 3 in `recipes.md` | 7B Full/32B QLoRA | ⭐⭐⭐⭐⭐ |
| **Multi-A100** | Recipe 4 in `recipes.md` | 32B QLoRA | ⭐⭐⭐⭐⭐ |
| **Apple Silicon** | `local-pretrain.sh` (auto) | 1.5B/3B | ⭐⭐⭐ |

### By Use Case

| Use Case | Recommended |
|----------|-------------|
| **Free tier / Budget** | T4 with 1.5B or 7B QLoRA |
| **Experimentation** | T4 with 1.5B model |
| **Best quality per dollar** | A100 80GB with 7B QLoRA |
| **Production training** | A100 80GB with 7B QLoRA |
| **Research** | Multi-A100 with 32B |
| **Quick iteration** | T4 with 1.5B model |

---

## 🔧 Configuration Files

### `t4-qlora.yaml`

Optimized for Google Colab T4 (16GB VRAM). Key settings:

```yaml
max_seq_length: 4096        # Keep context manageable
batch_size: 1               # Small per-device batch
gradient_accumulation: 32   # Compensate with accumulation
load_in_4bit: true          # 4-bit quantization
lora_rank: 64               # Good capacity/memory tradeoff
```

**Expected Runtime on T4:**
- 7B QLoRA: ~4-6 hours per epoch
- 1.5B QLoRA: ~2-3 hours per epoch

### `local-pretrain.sh`

Smart script that:
1. Detects your GPU automatically
2. Analyzes VRAM and capabilities
3. Selects optimal configuration
4. Launches training with appropriate settings

**Usage:**

```bash
# Show GPU info and recommendations
./local-pretrain.sh --gpu-info

# Interactive mode (recommended for first time)
./local-pretrain.sh

# Auto mode with defaults
./local-pretrain.sh --auto

# Auto with specific model
./local-pretrain.sh --auto 7B
./local-pretrain.sh --auto 1.5B
./local-pretrain.sh --auto 32B
```

---

## 📖 Detailed Documentation

For comprehensive information about each recipe, including:
- Exact hyperparameters
- Memory requirements
- Expected training times
- Cloud cost estimates
- Troubleshooting tips

See **[recipes.md](./recipes.md)**.

---

## ⚠️ Common Issues

### OOM (Out of Memory)

1. Reduce `max_seq_length` in the config
2. Enable `gradient_checkpointing: true`
3. Reduce `batch_size` to 1
4. Use smaller model (7B → 1.5B)

### Slow Training

1. Check GPU is being used (not CPU)
2. Reduce `max_seq_length`
3. Verify `gradient_checkpointing` is enabled
4. Consider using a faster model (1.5B for testing)

### Poor Quality Results

1. Increase training epochs (3 → 5)
2. Use larger `lora_alpha` (2x `lora_rank`)
3. Increase `max_seq_length` if data has long contexts
4. Add more diverse training data

---

## 📝 File Format Notes

### YAML Config (`t4-qlora.yaml`)

All configs are in YAML format for readability. You can:

1. **Use directly**: `python train.py --config t4-qlora.yaml`
2. **Copy and modify**: Create your own based on this template
3. **Override on CLI**: `python train.py --config t4-qlora.yaml --learning_rate 2e-4`

### Environment Variables

For T4 training, set these for better memory management:

```bash
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128"
export TRANSFORMERS_NO_ADVISORY_WARNINGS="true"
export TOKENIZERS_PARALLELISM="false"
```

---

## 🔗 Related Documentation

- [Main README](../README.md) - Project overview
- [recipes.md](./recipes.md) - Detailed training recipes
- [Training 7B Guide](../docs/TRAINING_7B.md) - 7B training walkthrough
- [Data Format](../docs/DATA_FORMAT.md) - Dataset requirements
