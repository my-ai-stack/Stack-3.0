import json
import os
from pathlib import Path

def merge_datasets():
    source_dir = Path(os.getenv("DATA_SOURCE_PATH", "training/training-data-expanded/"))
    target_file = Path("/Users/walidsobhi/stack-3.0/training/master_dataset_v3.jsonl")

    files_to_merge = [
        "tool_examples_smart_20k.jsonl",
        "tool_examples_20k.jsonl",
        "tool_examples_15k.jsonl",
        "tool_examples.jsonl"
    ]

    seen_messages = set()
    total_count = 0

    with open(target_file, "w", encoding="utf-8") as outfile:
        for filename in files_to_merge:
            filepath = source_dir / filename
            if not filepath.exists():
                print(f"Skipping {filename}: File not found")
                continue

            print(f"Processing {filename}...")
            with open(filepath, "r", encoding="utf-8") as infile:
                for line in infile:
                    try:
                        data = json.loads(line)
                        # Deduplication based on the messages content
                        msg_hash = hash(json.dumps(data["messages"], sort_keys=True))
                        if msg_hash in seen_messages:
                            continue

                        seen_messages.add(msg_hash)

                        # Normalize to ChatML (Basic version)
                        # The original files already have a 'messages' list.
                        # We ensure it's a clean JSONL line.
                        outfile.write(json.dumps(data) + "\n")
                        total_count += 1
                    except json.JSONDecodeError:
                        continue

    print(f"Successfully merged {total_count} unique examples into {target_file}")

if __name__ == "__main__":
    merge_datasets()
