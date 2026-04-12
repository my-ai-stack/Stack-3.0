import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def export_distilled_model(base_model_id, lora_weights_path, output_dir):
    \"\"\"
    Merges LoRA weights with the base model and exports the full model for deployment.
    \"\"\"
    print(f\"Loading base model: {base_model_id}\")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.float16,
        device_map=\"cpu\"
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model_id)

    print(f\"Loading LoRA weights from: {lora_weights_path}\")
    model = PeftModel.from_pretrained(base_model, lora_weights_path)

    print(\"Merging weights...\")
    model = model.merge_and_unload()

    print(f\"Saving final model to: {output_dir}\")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(\"Export complete.\")

if __name__ == \"__main__\":
    import sys
    if len(sys.argv) < 4:
        print(\"Usage: python export_weights.py <base_model_id> <lora_weights_path> <output_dir>\")
        sys.exit(1)

    export_distilled_model(sys.argv[1], sys.argv[2], sys.argv[3])
