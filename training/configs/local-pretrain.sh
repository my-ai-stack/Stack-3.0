#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Local Training Script with Auto-GPU Detection
# Automatically selects the best configuration for your hardware
# ═══════════════════════════════════════════════════════════════════════════════

set -e  # Exit on error

# ─────────────────────────────────────────────────────────────────────────────
# Color codes for output
# ─────────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ─────────────────────────────────────────────────────────────────────────────
# GPU Detection
# ─────────────────────────────────────────────────────────────────────────────
detect_gpu() {
    info "Detecting GPU..."
    
    # Check for NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null | head -1)
        GPU_NAME=$(echo "$GPU_INFO" | cut -d',' -f1 | sed 's/^ *//')
        GPU_TOTAL_MEM=$(echo "$GPU_INFO" | cut -d',' -f2 | sed 's/^ *//' | grep -oE '[0-9]+')
        GPU_FREE_MEM=$(echo "$GPU_INFO" | cut -d',' -f3 | sed 's/^ *//' | grep -oE '[0-9]+')
        
        info "Found NVIDIA GPU: $GPU_NAME"
        info "Total Memory: ${GPU_TOTAL_MEM}MB, Free: ${GPU_FREE_MEM}MB"
        
        echo "nvidia"
    # Check for macOS Apple Silicon
    elif [[ "$(uname)" == "Darwin" ]] && system_profiler SPDisplaysDataType 2>/dev/null | grep -q "Apple"; then
        GPU_NAME=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chipset Model" | head -1 | awk -F': ' '{print $2}')
        info "Found Apple Silicon GPU: $GPU_NAME"
        
        # Check for unified memory
        if sysctl -n hw.memsize &>/dev/null; then
            TOTAL_MEM=$(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}')
            info "Total System Memory: $TOTAL_MEM"
        fi
        
        echo "apple_silicon"
    # Check for AMD GPU (ROCm)
    elif command -v rocm-smi &> /dev/null; then
        GPU_NAME=$(rocm-smi --showproductname 2>/dev/null | grep "GPU" | head -1)
        info "Found AMD GPU (ROCm): $GPU_NAME"
        echo "amd"
    else
        warn "No GPU detected. Training will be VERY slow on CPU."
        echo "cpu"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# GPU Capability Analysis
# ─────────────────────────────────────────────────────────────────────────────
analyze_gpu_capability() {
    local gpu_type=$1
    
    case $gpu_type in
        "nvidia")
            # Parse GPU VRAM to determine capability
            if [[ $GPU_TOTAL_MEM -ge 70000 ]]; then
                # 80GB+ (A100, H100)
                echo "high_end"
            elif [[ $GPU_TOTAL_MEM -ge 35000 ]]; then
                # 40GB+ (A6000, A4000, RTX 6000)
                echo "mid_high"
            elif [[ $GPU_TOTAL_MEM -ge 15000 ]]; then
                # 16GB+ (RTX 4080, 3090, T4, V100)
                echo "mid_range"
            elif [[ $GPU_TOTAL_MEM -ge 8000 ]]; then
                # 8GB+ (RTX 3070, 2080, etc.)
                echo "low_end"
            else
                # Less than 8GB
                echo "budget"
            fi
            ;;
        "apple_silicon")
            # Apple Silicon unified memory - use system memory as guide
            local sys_mem_gb=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 / 1024 ))
            if [[ $sys_mem_gb -ge 64 ]]; then
                echo "mid_high"  # M3 Ultra, M2 Ultra
            elif [[ $sys_mem_gb -ge 32 ]]; then
                echo "mid_range"  # M3 Max, M2 Max, M1 Max
            elif [[ $sys_mem_gb -ge 16 ]]; then
                echo "low_end"  # M3 Pro, M2 Pro, M1 Pro
            else
                echo "budget"  # M3, M2, M1 base
            fi
            ;;
        "amd")
            # Assume mid-range for AMD
            echo "mid_range"
            ;;
        *)
            echo "cpu"
            ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Select Training Configuration
# ─────────────────────────────────────────────────────────────────────────────
select_config() {
    local capability=$1
    
    case $capability in
        "high_end")
            info "Detected high-end GPU (80GB+)"
            echo "a100"
            ;;
        "mid_high")
            info "Detected mid-high GPU (40GB+)"
            echo "a6000"
            ;;
        "mid_range")
            info "Detected mid-range GPU (16GB)"
            echo "t4"
            ;;
        "low_end")
            info "Detected low-end GPU (8GB)"
            echo "rtx3070"
            ;;
        "budget")
            info "Detected budget GPU or Apple Silicon with limited RAM"
            echo "mps"
            ;;
        "cpu")
            error "CPU-only training is not recommended. Proceeding anyway..."
            echo "cpu"
            ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Print Configuration Summary
# ─────────────────────────────────────────────────────────────────────────────
print_config_summary() {
    local config=$1
    local gpu_type=$2
    
    echo ""
    info "═══════════════════════════════════════════════════════════"
    info "                    TRAINING CONFIGURATION                    "
    info "═══════════════════════════════════════════════════════════"
    info "GPU Type: $GPU_NAME"
    info "GPU Memory: ${GPU_TOTAL_MEM}MB total, ${GPU_FREE_MEM}MB free"
    info "Detected Capability: $config"
    echo ""
    
    case $config in
        "a100")
            echo -e "${GREEN}Recommended for:${NC}"
            echo "  • 7B model with full LoRA (rank 128)"
            echo "  • 32B model with QLoRA"
            echo "  • Full fine-tuning possible"
            echo ""
            echo -e "${CYAN}Expected Performance:${NC}"
            echo "  • 30-45 min per epoch (7B)"
            echo "  • BF16 precision"
            echo ""
            echo -e "${YELLOW}Suggested Config:${NC}"
            echo "  • batch_size: 4"
            echo "  • max_seq_length: 32768"
            echo "  • gradient_accumulation: 8"
            ;;
        "a6000")
            echo -e "${GREEN}Recommended for:${NC}"
            echo "  • 7B model with LoRA (rank 64-128)"
            echo "  • 32B model with aggressive QLoRA"
            echo ""
            echo -e "${CYAN}Expected Performance:${NC}"
            echo "  • 45-60 min per epoch (7B)"
            echo "  • BF16 or FP16"
            echo ""
            echo -e "${YELLOW}Suggested Config:${NC}"
            echo "  • batch_size: 2-4"
            echo "  • max_seq_length: 16384-32768"
            echo "  • gradient_accumulation: 8-16"
            ;;
        "t4")
            echo -e "${GREEN}Recommended for:${NC}"
            echo "  • 7B model with QLoRA (rank 64)"
            echo "  • 1.5B model with larger LoRA"
            echo ""
            echo -e "${CYAN}Expected Performance:${NC}"
            echo "  • 4-6 hours per epoch (7B)"
            echo "  • FP16 precision"
            echo ""
            echo -e "${YELLOW}Suggested Config:${NC}"
            echo "  • batch_size: 1"
            echo "  • max_seq_length: 4096"
            echo "  • gradient_accumulation: 32"
            echo "  • Use training-configs/t4-qlora.yaml"
            ;;
        "rtx3070")
            echo -e "${GREEN}Recommended for:${NC}"
            echo "  • 1.5B model with LoRA"
            echo "  • 3B model with aggressive QLoRA"
            echo ""
            echo -e "${CYAN}Expected Performance:${NC}"
            echo "  • 3-5 hours per epoch (3B)"
            echo "  • FP16 precision"
            echo ""
            echo -e "${YELLOW}Suggested Config:${NC}"
            echo "  • batch_size: 1"
            echo "  • max_seq_length: 2048-4096"
            echo "  • gradient_accumulation: 16-32"
            ;;
        "mps")
            echo -e "${GREEN}Recommended for:${NC}"
            echo "  • 1.5B model with QLoRA"
            echo "  • Very small batches due to memory constraints"
            echo ""
            echo -e "${CYAN}Expected Performance:${NC}"
            echo "  • Slow training on Apple Silicon"
            echo "  • FP16 or mixed"
            echo ""
            echo -e "${YELLOW}Suggested Config:${NC}"
            echo "  • batch_size: 1"
            echo "  • max_seq_length: 2048"
            echo "  • gradient_accumulation: 32+"
            ;;
        "cpu")
            echo -e "${RED}WARNING: CPU Training${NC}"
            echo "  This will be VERY slow."
            echo "  Consider using cloud GPUs instead."
            echo ""
            echo -e "${YELLOW}If you must:${NC}"
            echo "  • Use smallest model (1.5B)"
            echo "  • Use QLoRA"
            echo "  • max_seq_length: 512-1024"
            ;;
    esac
    
    echo ""
    info "═══════════════════════════════════════════════════════════"
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Run Training
# ─────────────────────────────────────────────────────────────────────────────
run_training() {
    local config=$1
    local model_size=${2:-"7B"}
    local dataset=${3:-"./data/final/train_combined.jsonl"}
    
    info "Starting training with $config configuration..."
    
    # Set environment variables
    export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"
    export TRANSFORMERS_NO_ADVISORY_WARNINGS="true"
    export TOKENIZERS_PARALLELISM="false"
    
    # Build training command based on config
    case $config in
        "a100")
            python train.py \
                --model_name "Qwen/Qwen2.5-Coder-${model_size}" \
                --dataset_path "$dataset" \
                --output_dir "./output/${model_size}-a100" \
                --max_seq_length 32768 \
                --batch_size 4 \
                --gradient_accumulation_steps 8 \
                --learning_rate 5e-5 \
                --num_train_epochs 3 \
                --bf16 true \
                --lora_rank 128 \
                --lora_alpha 256 \
                --save_steps 500 \
                --eval_steps 500 \
                --logging_steps 10
            ;;
        "t4")
            python train.py \
                --config "training-configs/t4-qlora.yaml" \
                --model_name "Qwen/Qwen2.5-Coder-${model_size}" \
                --dataset_path "$dataset"
            ;;
        *)
            # Default fallback
            warn "Using default configuration"
            python train.py \
                --model_name "Qwen/Qwen2.5-Coder-1.5B" \
                --dataset_path "$dataset" \
                --output_dir "./output/default" \
                --max_seq_length 8192 \
                --batch_size 1 \
                --gradient_accumulation_steps 16 \
                --load_in_4bit true
            ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Interactive Mode
# ─────────────────────────────────────────────────────────────────────────────
interactive_menu() {
    echo ""
    info "═══════════════════════════════════════════════════════════"
    info "              LOCAL TRAINING SETUP (Interactive)            "
    info "═══════════════════════════════════════════════════════════"
    echo ""
    
    # GPU Detection
    local gpu_type=$(detect_gpu)
    local capability=$(analyze_gpu_capability $gpu_type)
    local config=$(select_config $capability)
    
    print_config_summary $config $gpu_type
    
    # Model Selection
    echo ""
    read -p "Select model size [1.5B/7B/32B] (default: 7B): " model_size
    model_size=${model_size:-7B}
    
    # Dataset Selection
    echo ""
    info "Available datasets:"
    echo "  1. ./data/final/train_combined.jsonl (default)"
    echo "  2. ./data/synthetic/examples.jsonl"
    echo "  3. ./data/humaneval/humaneval.jsonl"
    echo "  4. Custom path"
    read -p "Select dataset [1/2/3/4] (default: 1): " dataset_choice
    dataset_choice=${dataset_choice:-1}
    
    case $dataset_choice in
        1) dataset="./data/final/train_combined.jsonl" ;;
        2) dataset="./data/synthetic/examples.jsonl" ;;
        3) dataset="./data/humaneval/humaneval.jsonl" ;;
        4) 
            read -p "Enter custom dataset path: " dataset
            ;;
        *) dataset="./data/final/train_combined.jsonl" ;;
    esac
    
    # Confirm
    echo ""
    warn "Configuration Summary:"
    echo "  Model: $model_size"
    echo "  Dataset: $dataset"
    echo "  Config: $config"
    echo ""
    
    read -p "Start training? [y/N]: " confirm
    confirm=${confirm:-N}
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        run_training $config $model_size "$dataset"
    else
        info "Training cancelled."
        exit 0
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Auto Mode (No Interaction)
# ─────────────────────────────────────────────────────────────────────────────
auto_mode() {
    info "Running in auto mode..."
    
    local gpu_type=$(detect_gpu)
    local capability=$(analyze_gpu_capability $gpu_type)
    local config=$(select_config $capability)
    
    print_config_summary $config $gpu_type
    
    # Use command line arguments if provided, otherwise use defaults
    local model_size=${1:-"7B"}
    local dataset=${2:-"./data/final/train_combined.jsonl"}
    
    run_training $config $model_size "$dataset"
}

# ─────────────────────────────────────────────────────────────────────────────
# GPU Info Mode
# ─────────────────────────────────────────────────────────────────────────────
show_gpu_info() {
    info "═══════════════════════════════════════════════════════════"
    info "                        GPU INFORMATION                     "
    info "═══════════════════════════════════════════════════════════"
    
    local gpu_type=$(detect_gpu)
    local capability=$(analyze_gpu_capability $gpu_type)
    
    echo ""
    info "GPU Type: $GPU_NAME"
    info "Total Memory: ${GPU_TOTAL_MEM:-N/A} MB"
    info "Free Memory: ${GPU_FREE_MEM:-N/A} MB"
    info "Capability: $capability"
    info "Recommended Config: $(select_config $capability)"
    echo ""
    
    print_config_summary $(select_config $capability) $gpu_type
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────
main() {
    echo ""
    info "═══════════════════════════════════════════════════════════"
    info "     Stack 2.9 Local Training Launcher     "
    info "═══════════════════════════════════════════════════════════"
    
    case "${1:-}" in
        --gpu-info|-i)
            show_gpu_info
            ;;
        --auto|-a)
            auto_mode "${2:-7B}" "${3:-./data/final/train_combined.jsonl}"
            ;;
        --help|-h)
            echo ""
            echo "Usage: $0 [OPTIONS] [MODEL_SIZE] [DATASET]"
            echo ""
            echo "Options:"
            echo "  -i, --gpu-info       Show GPU information and exit"
            echo "  -a, --auto           Run in auto mode (no interaction)"
            echo "  -h, --help           Show this help message"
            echo ""
            echo "Arguments:"
            echo "  MODEL_SIZE           Model size: 1.5B, 7B, 32B (default: 7B)"
            echo "  DATASET              Path to training dataset (default: ./data/final/train_combined.jsonl)"
            echo ""
            echo "Examples:"
            echo "  $0 --gpu-info                    # Show GPU info"
            echo "  $0 -a 7B                         # Auto train 7B model"
            echo "  $0 -a 1.5B ./data/train.jsonl    # Auto train 1.5B with custom dataset"
            echo "  $0                               # Interactive mode"
            echo ""
            ;;
        *)
            if [[ -t 0 ]] && [[ ! "$1" =~ ^- ]]; then
                # Interactive mode if stdin is a terminal and no args
                interactive_menu
            else
                # Auto mode if non-interactive
                auto_mode "${1:-7B}" "${2:-./data/final/train_combined.jsonl}"
            fi
            ;;
    esac
}

# Run main with all arguments
main "$@"
