from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--adapter-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()
    
    print(f"Loading base model: {args.base_model}")
    # Load without device_map to avoid the error
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float32,
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    
    print(f"Loading adapter: {args.adapter_path}")
    model = PeftModel.from_pretrained(model, args.adapter_path)
    
    print("Merging...")
    model = model.merge_and_unload()
    
    print(f"Saving to: {args.output_path}")
    model.save_pretrained(args.output_path)
    tokenizer.save_pretrained(args.output_path)
    print("✅ Done!")

if __name__ == "__main__":
    main()
