"""
CYBER-OMNI Fine-Tuning Configuration
All settings in one place for easy tweaking.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Model Settings ──────────────────────────────────────────
# Base model to fine-tune from. Supports:
#   - Unsloth GGUF models: "unsloth/...-GGUF"
#   - HuggingFace models: "meta-llama/...", "Qwen/..."
BASE_MODEL = "unsloth/Llama-3.2-1B-Instruct-GGUF"  # 1B — fast, low resource

# Fine-tuning method
USE_RSLORA = True       # Use ReLoRA (better for small models)
USE_GRADIENT_CHECKPOINTING = True

# ─── LoRA Configuration ─────────────────────────────────────
LORA_R = 32             # Rank — higher = more parameters tuned (16-64)
LORA_ALPHA = 32         # Scaling factor (usually same as r)
LORA_DROPOUT = 0.0      # Dropout for regularization
LORA_TARGET_MODULES = [  # Which layers to apply LoRA to
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# ─── Dataset Settings ────────────────────────────────────────
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "cyber_omni_training.jsonl")
VALIDATION_SPLIT = 0.05   # 5% for validation
MAX_SEQ_LENGTH = 2048     # Max token length per sample
DATASET_TEXT_FIELD = "text"  # Field name after formatting

# ─── Training Hyperparameters ────────────────────────────────
BATCH_SIZE = 2            # Per device — adjust based on VRAM (1-4 for 1B)
GRADIENT_ACCUMULATION_STEPS = 4  # Effective batch size = BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS * GPUS
LEARNING_RATE = 2e-4
WARMUP_STEPS = 10
NUM_EPOCHS = 3            # 2-3 for initial, 5+ for production quality
OPTIMIZER = "adamw_8bit"  # 8-bit optimizer saves VRAM
SCHEDULER = "cosine"      # Learning rate schedule
WEIGHT_DECAY = 0.01
MAX_GRAD_NORM = 1.0

# ─── Saving ──────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SAVE_STEPS = 50            # Save checkpoint every N steps
SAVE_TOTAL_LIMIT = 3       # Keep only last 3 checkpoints
LOGGING_STEPS = 5
EVAL_STEPS = 50

# ─── Export Settings ─────────────────────────────────────────
EXPORT_QUANTIZATION = "q4_k_m"  # Output GGUF quantization (q4_k_m = 4-bit, good balance)
EXPORT_DIR = BASE_DIR           # Where to save final GGUF

# ─── System ──────────────────────────────────────────────────
USE_FP16 = True           # Use mixed precision (requires compatible GPU)
USE_FLASH_ATTENTION = False  # Flash Attention 2 (faster, requires compatible GPU)
NUM_GPUS = 1              # Number of GPUs for training
SEED = 42

# ─── Chat Template ───────────────────────────────────────────
CHAT_TEMPLATE = """{% if messages[0]['role'] == 'system' %}{% set system_message = messages[0]['content'] %}{% endif %}{% if system_message %}<|system|>
{{ system_message }}<|end|>
{% endif %}{% for message in messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% if message['role'] == 'user' %}<|user|>
{{ message['content'] }}<|end|>
{% elif message['role'] == 'assistant' %}<|assistant|>
{{ message['content'] }}<|end|>
{% endif %}{% endfor %}{% if add_generation_prompt %}<|assistant|>
{% endif %}"""
