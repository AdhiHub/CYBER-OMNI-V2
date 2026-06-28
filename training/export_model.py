"""
CYBER-OMNI Model Export
Converts fine-tuned LoRA model → merged GGUF for use in CYBER-OMNI.
"""
import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from training.config import (
    BASE_MODEL, OUTPUT_DIR, EXPORT_QUANTIZATION, EXPORT_DIR, CHAT_TEMPLATE,
)
from core.utils import colored


def export_to_gguf():
    """Merge LoRA weights into base model and export as GGUF."""
    print(colored("\n" + "=" * 55, "36"))
    print(colored("  CYBER-OMNI Model Export", "36"))
    print(colored("  LoRA → Merged GGUF", "36"))
    print(colored("=" * 55, "36"))

    lora_path = os.path.join(OUTPUT_DIR, "cyber-omni-lora")
    if not os.path.exists(lora_path):
        print(colored(f"  [!] LoRA adapter not found: {lora_path}", "31"))
        print(colored("  [*] Run training first: python -m training.train", "33"))
        return

    # ─── Method 1: Use unsloth for merging ────────────────
    try:
        from unsloth import FastLanguageModel
        import torch

        print(colored(f"\n[*] Loading base model: {BASE_MODEL}", "33"))
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=BASE_MODEL,
            max_seq_length=2048,
            dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            load_in_4bit=False,  # Merge in higher precision
            device_map="auto",
        )

        print(colored(f"[*] Loading LoRA adapter: {lora_path}", "33"))
        model.load_adapter(lora_path)

        print(colored("[*] Merging LoRA weights into base model...", "33"))
        model = model.merge_and_unload()

        # Set chat template
        tokenizer.chat_template = CHAT_TEMPLATE

        # ─── Export to GGUF ──────────────────────────────
        modelfile = f"cyber-omni-finetuned-{EXPORT_QUANTIZATION}"
        save_path = os.path.join(EXPORT_DIR, f"{modelfile}.gguf")

        print(colored(f"\n[*] Exporting to GGUF (quantization: {EXPORT_QUANTIZATION})...", "33"))
        print(colored("  [*] This may take a while for larger models...", "33"))

        from unsloth import save_gguf

        save_gguf(
            model=model,
            tokenizer=tokenizer,
            quantization_method=EXPORT_QUANTIZATION,
            save_path=save_path,
        )

        file_size = os.path.getsize(save_path) / (1024 * 1024 * 1024)
        print(colored(f"\n[+] GGUF exported: {save_path}", "32"))
        print(colored(f"    Size: {file_size:.2f} GB", "32"))

        # ─── Copy to models directory ─────────────────────
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        os.makedirs(models_dir, exist_ok=True)
        dest_path = os.path.join(models_dir, os.path.basename(save_path))
        shutil.copy2(save_path, dest_path)
        print(colored(f"\n[+] Copied to models dir: {dest_path}", "32"))
        print(colored("\n[*] To use this model in CYBER-OMNI:", "33"))
        print(colored("    1. Update config.json with:", "33"))
        print(colored(f'       "model": "cyber-omni-finetuned-{EXPORT_QUANTIZATION}"', "36"))
        print(colored("    2. Or run: python omni.py", "33"))
        print(colored("    3. The model will be auto-detected", "33"))

        return save_path

    except ImportError:
        print(colored("  [!] Unsloth not available. Trying llama.cpp method...", "31"))
        return _export_via_llamacpp(lora_path)


def _export_via_llamacpp(lora_path):
    """Fallback: use llama.cpp's convert and quantize scripts."""
    print(colored("\n[*] The recommended path is to install Unsloth:", "33"))
    print(colored("    pip install unsloth", "33"))
    print(colored("\n[*] Alternative: Manual conversion steps:", "33"))
    print(colored("    1. Merge LoRA manually using the notebook:", "33"))
    print(colored("       training/notebooks/merge_lora.ipynb", "33"))
    print(colored("    2. Or use convert.py from llama.cpp:", "33"))
    print(colored("       python llama.cpp/convert.py model_dir --outfile model.gguf", "33"))
    print(colored("    3. Quantize with:", "33"))
    print(colored("       llama.cpp/quantize model.gguf model-q4_k_m.gguf q4_k_m", "33"))
    print(colored("\n[*] Or simply copy the LoRA adapter and use it directly:", "33"))
    print(colored(f"    Source: {lora_path}", "33"))
    print(colored(f"    Copy to: {os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'lora_adapter')}", "33"))

    lora_copy = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "models", "lora_adapter"
    )
    if os.path.exists(lora_copy):
        shutil.rmtree(lora_copy)
    shutil.copytree(lora_path, lora_copy)
    print(colored(f"[+] LoRA adapter copied: {lora_copy}", "32"))
    return None


def main():
    global EXPORT_QUANTIZATION, EXPORT_DIR
    import argparse
    parser = argparse.ArgumentParser(description="Export CYBER-OMNI fine-tuned model to GGUF")
    parser.add_argument("--quantization", default=EXPORT_QUANTIZATION,
                        choices=["q4_k_m", "q5_k_m", "q8_0", "f16"],
                        help="GGUF quantization method")
    parser.add_argument("--output-dir", default=EXPORT_DIR, help="Output directory")
    args = parser.parse_args()

    EXPORT_QUANTIZATION = args.quantization
    EXPORT_DIR = args.output_dir

    export_to_gguf()


if __name__ == "__main__":
    main()
