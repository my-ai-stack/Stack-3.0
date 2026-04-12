
import os
import modal
from modal import Image, App, Volume, mount

# --- Configuration ---
# Using the 7B scale hyperparameters we decided on
MODEL_NAME = "Qwen/Qwen2.5-Coder-7B"
LORA_R = 16
LORA_ALPHA = 32
MAX_LENGTH = 8192
BATCH_SIZE = 4
USE_4BIT = True
HF_TOKEN = os.environ.get("HF_TOKEN", "your_huggingface_token_here")

# Define the Modal Image
image = (
    Image.debian_slim()
    .pip_install(
        "torch",
        "transformers",
        "peft",
        "accelerate",
        "bitsandbytes",
        "datasets",
        "sentencepiece",
        "pyyaml"
    )
    .add_local_dir(".", remote_path="/root/project")
)

# Create the Modal App
app = App("stack-3-0-training-giant")

# Create a volume to store training data and checkpoints
volume = Volume.from_name("stack-3-0-training-data", create_if_missing=True)

@app.function(
    image=image,
    gpu="A100",
    timeout=14400,
    volumes={"/root/project/checkpoints": volume},
)
def train_model():
    print("🚀 Starting Stack 3.0 Giant Model Training on Modal...")

    # Set environment variables
    os.environ["HF_TOKEN"] = HF_TOKEN

    # We call the existing run_training.py from the lauch_train.sh logic
    # Note: We assume the files are already in the volume or we mount them
    # For the first run, we can use a mount or upload the directory.

    import subprocess

    # Command to run the training
    # We use the same parameters as defined in launch_train.sh 7b
    cmd = [
        "python3",
        "cognitive_core/training/run_training.py",
        "--model_name", MODEL_NAME,
        "--lora_r", str(LORA_R),
        "--lora_alpha", str(LORA_ALPHA),
        "--max_length", str(MAX_LENGTH),
        "--batch_size", str(BATCH_SIZE),
        "--use_4bit", str(USE_4BIT).lower(),
        "--config", "cognitive_core/training/train_config.yaml",
        "--deepspeed_stage", "3",
        "--pipeline", "giant_sft_rlhf",
        "--precision", "bf16",
        "--cluster_config", "gcp_a100_cluster"
    ]

    print(f"Executing: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/root/project"
        )

        # Stream logs back to the console
        for line in process.stdout:
            print(f"[Training Log]: {line.strip()}")

        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print("✅ Training completed successfully!")
        else:
            print(f"❌ Training failed with exit code {process.returncode}")
            print(f"Error: {stderr}")

    except Exception as e:
        print(f"💥 Fatal error during training: {str(e)}")

if __name__ == "__main__":
    # Use the app.run() context to properly hydrate the function and launch it on Modal
    with app.run():
        train_model.remote()
