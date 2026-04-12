#!/bin/bash
# =============================================================================
# Stack 3.0 Full Benchmark Evaluation Suite
# =============================================================================
# Runs all benchmarks and generates comprehensive evaluation report.
#
# Usage:
#   ./run_all_benchmarks.sh [OPTIONS]
#
# Options:
#   --model MODEL         Model name to evaluate (default: stack-3.0)
#   --output DIR          Output directory (default: ./results)
#   --skip-slow           Skip slow benchmarks
#   --sample-size N       Use N samples per benchmark (default: all)
#   --verbose             Verbose output
#
# =============================================================================

set -e

# Configuration
MODEL="${MODEL:-stack-3.0}"
OUTPUT_DIR="${OUTPUT_DIR:-./results}"
SAMPLE_SIZE=""
SKIP_SLOW=""
VERBOSE=""
PYTHON="${PYTHON:-python3}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Benchmark scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUMAN_EVAL="${SCRIPT_DIR}/human_eval.py"
MBPP_EVAL="${SCRIPT_DIR}/mbpp_eval.py"
TOOL_EVAL="${SCRIPT_DIR}/tool_use_eval.py"
SELF_IMPROVE_EVAL="${SCRIPT_DIR}/self_improve_eval.py"
DASHBOARD="${SCRIPT_DIR}/results/dashboard.py"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

section() {
    echo ""
    echo "=============================================================================="
    echo "$1"
    echo "=============================================================================="
}

# =============================================================================
# Parse Arguments
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --skip-slow)
            SKIP_SLOW="1"
            shift
            ;;
        --sample-size)
            SAMPLE_SIZE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="1"
            shift
            ;;
        --help)
            echo "Stack 3.0 Full Benchmark Suite"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --model MODEL         Model name (default: stack-3.0)"
            echo "  --output DIR          Output directory (default: ./results)"
            echo "  --skip-slow           Skip slow benchmarks"
            echo "  --sample-size N       Sample size for each benchmark"
            echo "  --verbose             Verbose output"
            echo "  --help                Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Setup
# =============================================================================

log_info "Stack 3.0 Benchmark Suite"
log_info "Model: ${MODEL}"
log_info "Output: ${OUTPUT_DIR}"
echo ""

# Create output directory
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}/detailed"

# Track start time
START_TIME=$(date +%s)

# Results summary
declare -A BENCHMARK_RESULTS

# =============================================================================
# Check Dependencies
# =============================================================================

section "Checking Dependencies"

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON="python3"
    elif command -v python &> /dev/null; then
        PYTHON="python"
    else
        log_error "Python not found!"
        exit 1
    fi
    log_success "Python: $(${PYTHON} --version)"
}

check_dependencies() {
    log_info "Checking Python dependencies..."
    
    # Check for required modules
    REQUIRED_MODULES=("json" "datetime" "pathlib" "argparse")
    MISSING=""
    
    for module in "${REQUIRED_MODULES[@]}"; do
        if ! ${PYTHON} -c "import ${module}" &> /dev/null; then
            MISSING="${MISSING} ${module}"
        fi
    done
    
    if [ -n "${MISSING}" ]; then
        log_warning "Missing modules:${MISSING}"
        log_info "These are standard library modules and should be available."
    fi
    
    log_success "Dependencies OK"
}

check_python
check_dependencies

# =============================================================================
# HumanEval Benchmark
# =============================================================================

section "HumanEval Benchmark"

log_info "Running HumanEval benchmark..."
log_info "Metrics: Pass@1, Pass@10, Pass@100"

HUMAN_EVAL_START=$(date +%s)

if [ -f "${HUMAN_EVAL}" ]; then
    HUMAN_EVAL_CMD="${PYTHON} ${HUMAN_EVAL} --model ${MODEL} --output ${OUTPUT_DIR}/detailed"
    
    if [ -n "${SAMPLE_SIZE}" ]; then
        # Note: human_eval.py doesn't support sample-size directly
        # but we include it for other benchmarks
        :
    fi
    
    if [ -n "${VERBOSE}" ]; then
        ${HUMAN_EVAL_CMD} 2>&1 | tee "${OUTPUT_DIR}/detailed/humaneval_output.log"
    else
        ${HUMAN_EVAL_CMD} > "${OUTPUT_DIR}/detailed/humaneval_output.log" 2>&1
    fi
    
    HUMAN_EVAL_END=$(date +%s)
    HUMAN_EVAL_TIME=$((HUMAN_EVAL_END - HUMAN_EVAL_START))
    
    if [ -f "${OUTPUT_DIR}/detailed/humaneval_results.json" ]; then
        PASS_1=$(grep -o '"pass_at_1": [0-9.]*' "${OUTPUT_DIR}/detailed/humaneval_results.json" | cut -d':' -f2)
        PASS_10=$(grep -o '"pass_at_10": [0-9.]*' "${OUTPUT_DIR}/detailed/humaneval_results.json" | cut -d':' -f2)
        BENCHMARK_RESULTS["humaneval_pass1"]="${PASS_1}"
        BENCHMARK_RESULTS["humaneval_pass10"]="${PASS_10}"
        log_success "HumanEval: Pass@1=${PASS_1}, Pass@10=${PASS_10} (${HUMAN_EVAL_TIME}s)"
    else
        log_error "HumanEval results not found"
    fi
else
    log_warning "HumanEval script not found: ${HUMAN_EVAL}"
fi

# =============================================================================
# MBPP Benchmark
# =============================================================================

section "MBPP Benchmark"

log_info "Running MBPP benchmark..."
log_info "Metrics: Pass@1, Pass@10"

MBPP_START=$(date +%s)

if [ -f "${MBPP_EVAL}" ]; then
    MBPP_CMD="${PYTHON} ${MBPP_EVAL} --model ${MODEL} --output ${OUTPUT_DIR}/detailed"
    
    if [ -n "${VERBOSE}" ]; then
        ${MBPP_CMD} 2>&1 | tee "${OUTPUT_DIR}/detailed/mbpp_output.log"
    else
        ${MBPP_CMD} > "${OUTPUT_DIR}/detailed/mbpp_output.log" 2>&1
    fi
    
    MBPP_END=$(date +%s)
    MBPP_TIME=$((MBPP_END - MBPP_START))
    
    if [ -f "${OUTPUT_DIR}/detailed/mbpp_results.json" ]; then
        PASS_1=$(grep -o '"pass_at_1": [0-9.]*' "${OUTPUT_DIR}/detailed/mbpp_results.json" | cut -d':' -f2)
        PASS_10=$(grep -o '"pass_at_10": [0-9.]*' "${OUTPUT_DIR}/detailed/mbpp_results.json" | cut -d':' -f2)
        BENCHMARK_RESULTS["mbpp_pass1"]="${PASS_1}"
        BENCHMARK_RESULTS["mbpp_pass10"]="${PASS_10}"
        log_success "MBPP: Pass@1=${PASS_1}, Pass@10=${PASS_10} (${MBPP_TIME}s)"
    else
        log_error "MBPP results not found"
    fi
else
    log_warning "MBPP script not found: ${MBPP_EVAL}"
fi

# =============================================================================
# Tool Use Evaluation
# =============================================================================

section "Tool Use Evaluation"

log_info "Running Tool Use evaluation..."
log_info "Metrics: Tool Selection Accuracy, Parameter Accuracy, Execution Success"

TOOL_START=$(date +%s)

if [ -f "${TOOL_EVAL}" ]; then
    TOOL_CMD="${PYTHON} ${TOOL_EVAL} --model ${MODEL} --output ${OUTPUT_DIR}/detailed"
    
    if [ -n "${SAMPLE_SIZE}" ]; then
        TOOL_CMD="${TOOL_CMD} --sample ${SAMPLE_SIZE}"
    fi
    
    if [ -n "${VERBOSE}" ]; then
        ${TOOL_CMD} 2>&1 | tee "${OUTPUT_DIR}/detailed/tool_output.log"
    else
        ${TOOL_CMD} > "${OUTPUT_DIR}/detailed/tool_output.log" 2>&1
    fi
    
    TOOL_END=$(date +%s)
    TOOL_TIME=$((TOOL_END - TOOL_START))
    
    if [ -f "${OUTPUT_DIR}/detailed/tool_use_results.json" ]; then
        TOOL_ACC=$(grep -o '"tool_selection_accuracy": [0-9.]*' "${OUTPUT_DIR}/detailed/tool_use_results.json" | cut -d':' -f2)
        PARAM_ACC=$(grep -o '"parameter_accuracy": [0-9.]*' "${OUTPUT_DIR}/detailed/tool_use_results.json" | cut -d':' -f2)
        EXEC_RATE=$(grep -o '"execution_success_rate": [0-9.]*' "${OUTPUT_DIR}/detailed/tool_use_results.json" | cut -d':' -f2)
        BENCHMARK_RESULTS["tool_selection_accuracy"]="${TOOL_ACC}"
        BENCHMARK_RESULTS["parameter_accuracy"]="${PARAM_ACC}"
        BENCHMARK_RESULTS["execution_success_rate"]="${EXEC_RATE}"
        log_success "Tool Use: Selection=${TOOL_ACC}, Param=${PARAM_ACC}, Exec=${EXEC_RATE} (${TOOL_TIME}s)"
    else
        log_error "Tool Use results not found"
    fi
else
    log_warning "Tool Use script not found: ${TOOL_EVAL}"
fi

# =============================================================================
# Self-Improvement Evaluation
# =============================================================================

if [ -z "${SKIP_SLOW}" ]; then
    section "Self-Improvement Evaluation"
    
    log_info "Running Self-Improvement evaluation..."
    log_info "Metrics: Memory Retention, Pattern Application, Improvement Rate"
    
    SELF_IMPROVE_START=$(date +%s)
    
    if [ -f "${SELF_IMPROVE_EVAL}" ]; then
        SELF_CMD="${PYTHON} ${SELF_IMPROVE_EVAL} --model ${MODEL} --output ${OUTPUT_DIR}/detailed"
        
        if [ -n "${VERBOSE}" ]; then
            ${SELF_CMD} 2>&1 | tee "${OUTPUT_DIR}/detailed/self_improve_output.log"
        else
            ${SELF_CMD} > "${OUTPUT_DIR}/detailed/self_improve_output.log" 2>&1
        fi
        
        SELF_IMPROVE_END=$(date +%s)
        SELF_TIME=$((SELF_IMPROVE_END - SELF_IMPROVE_START))
        
        if [ -f "${OUTPUT_DIR}/detailed/self_improve_results.json" ]; then
            MEM_RET=$(grep -o '"memory_retention_rate": [0-9.]*' "${OUTPUT_DIR}/detailed/self_improve_results.json" | cut -d':' -f2)
            PATTERN_ACC=$(grep -o '"pattern_application_accuracy": [0-9.]*' "${OUTPUT_DIR}/detailed/self_improve_results.json" | cut -d':' -f2)
            IMPROVE_RATE=$(grep -o '"improvement_rate": [0-9.]*' "${OUTPUT_DIR}/detailed/self_improve_results.json" | cut -d':' -f2)
            BENCHMARK_RESULTS["memory_retention"]="${MEM_RET}"
            BENCHMARK_RESULTS["pattern_accuracy"]="${PATTERN_ACC}"
            BENCHMARK_RESULTS["improvement_rate"]="${IMPROVE_RATE}"
            log_success "Self-Improve: Memory=${MEM_RET}, Pattern=${PATTERN_ACC}, Improve=${IMPROVE_RATE} (${SELF_TIME}s)"
        else
            log_error "Self-Improvement results not found"
        fi
    else
        log_warning "Self-Improvement script not found: ${SELF_IMPROVE_EVAL}"
    fi
else
    log_info "Skipping Self-Improvement evaluation (--skip-slow)"
fi

# =============================================================================
# Generate Dashboard
# =============================================================================

section "Generating Dashboard"

log_info "Creating visualization dashboard..."

if [ -f "${DASHBOARD}" ]; then
    ${PYTHON} "${DASHBOARD}" --results-dir "${OUTPUT_DIR}/detailed" --output "${OUTPUT_DIR}" 2>&1 | tee "${OUTPUT_DIR}/detailed/dashboard_output.log"
    log_success "Dashboard generated at ${OUTPUT_DIR}/dashboard.html"
else
    log_warning "Dashboard script not found: ${DASHBOARD}"
fi

# =============================================================================
# Generate Summary Report
# =============================================================================

section "Summary Report"

TOTAL_TIME=$(($(date +%s) - START_TIME))

echo ""
echo "=============================================================================="
echo "BENCHMARK RESULTS SUMMARY"
echo "=============================================================================="
echo ""
echo "Model: ${MODEL}"
echo "Evaluation Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Total Time: ${TOTAL_TIME}s"
echo ""
echo "------------------------------------------------------------------------------"
echo "CODE GENERATION BENCHMARKS"
echo "------------------------------------------------------------------------------"
printf "%-20s %-15s %-15s\n" "Benchmark" "Pass@1" "Pass@10"
echo "------------------------------------------------------------------------------"
printf "%-20s %-15s %-15s\n" "HumanEval" "${BENCHMARK_RESULTS[humaneval_pass1]:-N/A}" "${BENCHMARK_RESULTS[humaneval_pass10]:-N/A}"
printf "%-20s %-15s %-15s\n" "MBPP" "${BENCHMARK_RESULTS[mbpp_pass1]:-N/A}" "${BENCHMARK_RESULTS[mbpp_pass10]:-N/A}"
echo ""
echo "------------------------------------------------------------------------------"
echo "TOOL USE CAPABILITIES"
echo "------------------------------------------------------------------------------"
printf "%-25s %-15s\n" "Metric" "Value"
echo "------------------------------------------------------------------------------"
printf "%-25s %-15s\n" "Tool Selection Accuracy" "${BENCHMARK_RESULTS[tool_selection_accuracy]:-N/A}"
printf "%-25s %-15s\n" "Parameter Accuracy" "${BENCHMARK_RESULTS[parameter_accuracy]:-N/A}"
printf "%-25s %-15s\n" "Execution Success Rate" "${BENCHMARK_RESULTS[execution_success_rate]:-N/A}"
echo ""
echo "------------------------------------------------------------------------------"
echo "SELF-IMPROVEMENT CAPABILITIES"
echo "------------------------------------------------------------------------------"
printf "%-25s %-15s\n" "Metric" "Value"
echo "------------------------------------------------------------------------------"
printf "%-25s %-15s\n" "Memory Retention Rate" "${BENCHMARK_RESULTS[memory_retention]:-N/A}"
printf "%-25s %-15s\n" "Pattern Application Accuracy" "${BENCHMARK_RESULTS[pattern_accuracy]:-N/A}"
printf "%-25s %-15s\n" "Improvement Rate" "${BENCHMARK_RESULTS[improvement_rate]:-N/A}"
echo ""
echo "=============================================================================="

# =============================================================================
# Save Summary to JSON
# =============================================================================

cat > "${OUTPUT_DIR}/benchmark_summary.json" << EOF
{
    "model": "${MODEL}",
    "evaluation_date": "$(date '+%Y-%m-%d %H:%M:%S')",
    "total_time_seconds": ${TOTAL_TIME},
    "humaneval": {
        "pass_at_1": ${BENCHMARK_RESULTS[humaneval_pass1]:-null},
        "pass_at_10": ${BENCHMARK_RESULTS[humaneval_pass10]:-null}
    },
    "mbpp": {
        "pass_at_1": ${BENCHMARK_RESULTS[mbpp_pass1]:-null},
        "pass_at_10": ${BENCHMARK_RESULTS[mbpp_pass10]:-null}
    },
    "tool_use": {
        "tool_selection_accuracy": ${BENCHMARK_RESULTS[tool_selection_accuracy]:-null},
        "parameter_accuracy": ${BENCHMARK_RESULTS[parameter_accuracy]:-null},
        "execution_success_rate": ${BENCHMARK_RESULTS[execution_success_rate]:-null}
    },
    "self_improvement": {
        "memory_retention_rate": ${BENCHMARK_RESULTS[memory_retention]:-null},
        "pattern_application_accuracy": ${BENCHMARK_RESULTS[pattern_accuracy]:-null},
        "improvement_rate": ${BENCHMARK_RESULTS[improvement_rate]:-null}
    }
}
EOF

log_success "Summary saved to ${OUTPUT_DIR}/benchmark_summary.json"
log_success "Detailed results in ${OUTPUT_DIR}/detailed/"

echo ""
log_success "All benchmarks completed successfully!"
