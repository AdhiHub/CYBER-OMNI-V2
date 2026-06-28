"""
CYBER-OMNI Fine-Tuning Script
Trains a local LLM to become a specialized pentesting AI.
Uses Unsloth for efficient LoRA/QLoRA training.
"""
import os
import sys
import json
import random
import torch
from datasets import Dataset, DatasetDict
from transformers import TrainingArguments, HfArgumentParser
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM
from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import get_chat_template, standardize_sharegpt

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from training.config import (
    BASE_MODEL, LORA_R, LORA_ALPHA, LORA_DROPOUT, LORA_TARGET_MODULES,
    DATASET_PATH, MAX_SEQ_LENGTH, BATCH_SIZE, GRADIENT_ACCUMULATION_STEPS,
    LEARNING_RATE, WARMUP_STEPS, NUM_EPOCHS, OPTIMIZER, SCHEDULER,
    WEIGHT_DECAY, MAX_GRAD_NORM, OUTPUT_DIR, SAVE_STEPS, SAVE_TOTAL_LIMIT,
    LOGGING_STEPS, EVAL_STEPS, USE_FP16, USE_FLASH_ATTENTION,
    VALIDATION_SPLIT, SEED, CHAT_TEMPLATE, NUM_GPUS,
)
from core.utils import colored


def load_jsonl(path):
    """Load a JSONL file (ShareGPT format)"""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(colored(f"  [!] Line {i+1} parse error: {e}", "31"))
    return data


def format_dataset(conversations, tokenizer):
    """Apply chat template to each conversation."""
    formatted = []
    for conv in conversations:
        try:
            text = tokenizer.apply_chat_template(
                conv["conversations"],
                tokenize=False,
                add_generation_prompt=False,
            )
            formatted.append({"text": text})
        except Exception as e:
            continue
    return formatted


def train():
    print(colored("\n" + "=" * 55, "36"))
    print(colored("  CYBER-OMNI Fine-Tuning Pipeline", "36"))
    print(colored("  Powered by Unsloth + LoRA", "36"))
    print(colored("=" * 55, "36"))

    # ─── Step 1: Load Dataset ───────────────────────────────
    print(colored("\n[*] Loading dataset...", "33"))
    if not os.path.exists(DATASET_PATH):
        print(colored(f"  [!] Dataset not found: {DATASET_PATH}", "31"))
        print(colored("  [*] Run: python -m training.dataset_generator", "33"))
        return

    raw_data = load_jsonl(DATASET_PATH)
    print(colored(f"  [+] Loaded {len(raw_data)} conversations", "32"))

    # ─── Step 2: Load Model ─────────────────────────────────
    print(colored(f"\n[*] Loading base model: {BASE_MODEL}", "33"))
    print(colored(f"  [*] Max sequence length: {MAX_SEQ_LENGTH}", "33"))

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,  # Auto-detect
        load_in_4bit=True,  # QLoRA — saves VRAM
        token=None,  # No HF token needed for public models
        device_map="auto",
    )

    # Set chat template
    tokenizer = get_chat_template(
        tokenizer,
        chat_template=CHAT_TEMPLATE,
    )

    # ─── Step 3: Format Dataset ─────────────────────────────
    print(colored("\n[*] Formatting dataset with chat template...", "33"))
    formatted = format_dataset(raw_data, tokenizer)

    # Split into train/validation
    random.seed(SEED)
    random.shuffle(formatted)
    split_idx = int(len(formatted) * (1 - VALIDATION_SPLIT))
    train_data = formatted[:split_idx]
    eval_data = formatted[split_idx:] if split_idx < len(formatted) else formatted[:1]

    dataset = DatasetDict({
        "train": Dataset.from_list(train_data),
        "eval": Dataset.from_list(eval_data),
    })
    print(colored(f"  [+] Train: {len(train_data)} samples", "32"))
    print(colored(f"  [+] Eval: {len(eval_data)} samples", "32"))

    # ─── Step 4: Apply LoRA ─────────────────────────────────
    print(colored("\n[*] Applying LoRA adapters...", "33"))
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=LORA_TARGET_MODULES,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        use_gradient_checkpointing=True,
        random_state=SEED,
        use_rslora=True,  # ReLoRA for better training
    )

    # Print trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(colored(f"  [+] Trainable: {trainable_params:,} / {total_params:,} params ({100*trainable_params/total_params:.2f}%)", "32"))

    # ─── Step 5: Configure Training ─────────────────────────
    print(colored("\n[*] Configuring training...", "33"))

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        warmup_steps=WARMUP_STEPS,
        num_train_epochs=NUM_EPOCHS,
        optim=OPTIMIZER,
        lr_scheduler_type=SCHEDULER,
        weight_decay=WEIGHT_DECAY,
        max_grad_norm=MAX_GRAD_NORM,
        evaluation_strategy="steps" if len(eval_data) > 1 else "no",
        eval_steps=EVAL_STEPS if len(eval_data) > 1 else None,
        save_strategy="steps",
        save_steps=SAVE_STEPS,
        save_total_limit=SAVE_TOTAL_LIMIT,
        logging_steps=LOGGING_STEPS,
        fp16=USE_FP16 if not is_bfloat16_supported() else False,
        bf16=is_bfloat16_supported(),
        report_to="none",  # No wandb/tensorboard
        seed=SEED,
        dataloader_num_workers=0,
        ddp_find_unused_parameters=False if NUM_GPUS > 1 else None,
        remove_unused_columns=True,
    )

    # Data collator for completion-only loss
    collator = DataCollatorForCompletionOnlyLM(
        response_template="<|assistant|>",
        tokenizer=tokenizer,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("eval"),
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        data_collator=collator,
        packing=False,
    )

    # ─── Step 6: Train ──────────────────────────────────────
    print(colored("\n" + "=" * 55, "36"))
    print(colored("  Starting Training!", "32"))
    print(colored("  Press Ctrl+C to stop (checkpoints are saved)", "33"))
    print(colored("=" * 55, "36"))
    print()

    trainer.train()

    # ─── Step 7: Save Final Model ───────────────────────────
    print(colored("\n[*] Saving final model...", "33"))
    final_path = os.path.join(OUTPUT_DIR, "cyber-omni-final")
    trainer.save_model(final_path)
    tokenizer.save_pretrained(final_path)
    print(colored(f"  [+] Model saved: {final_path}", "32"))

    # Also save the LoRA adapter separately
    lora_path = os.path.join(OUTPUT_DIR, "cyber-omni-lora")
    model.save_pretrained(lora_path)
    print(colored(f"  [+] LoRA adapter saved: {lora_path}", "32"))

    print(colored("\n" + "=" * 55, "36"))
    print(colored("  Training Complete!", "32"))
    print(colored(f"  Model: {final_path}", "32"))
    print(colored(f"  Next: python -m training.export_model", "33"))
    print(colored("=" * 55, "36"))

    return final_path


def main():
    """Entry point. Handle args and run training."""
    global DATASET_PATH, BASE_MODEL, NUM_EPOCHS, LEARNING_RATE, BATCH_SIZE, OUTPUT_DIR
    import argparse
    parser = argparse.ArgumentParser(description="CYBER-OMNI Fine-Tuning")
    parser.add_argument("--dataset", default=DATASET_PATH, help="Path to training dataset JSONL")
    parser.add_argument("--model", default=BASE_MODEL, help="Base model name/path")
    parser.add_argument("--epochs", type=int, default=NUM_EPOCHS, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=LEARNING_RATE, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Per device batch size")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    # Update config from args
    DATASET_PATH = args.dataset
    BASE_MODEL = args.model
    NUM_EPOCHS = args.epochs
    LEARNING_RATE = args.lr
    BATCH_SIZE = args.batch_size
    OUTPUT_DIR = args.output

    train()


if __name__ == "__main__":
    main()
