"""
CYBER-OMNI Model Evaluator
Tests the fine-tuned model against benchmark prompts.
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.utils import colored


BENCHMARK_PROMPTS = [
    # Tool usage
    "scan 192.168.1.1 for open ports",
    "how do I exploit a SQL injection vulnerability?",
    "run a full recon on example.com",
    "write a Python reverse shell for Linux",
    "explain how buffer overflow works",

    # Code generation
    "write a Python script to check for subdomain takeover",
    "create a hydra command for SSH brute force",

    # Explanations
    "what's the difference between white hat and black hat hacking?",
    "explain the OWASP Top 10",
    "how does Kerberoasting work?",

    # Multi-turn capability
    "I found an open SMB port. What should I do next?",
    "I have a shell on a Windows server. How do I get admin?",

    # Questions back to user
    "help me learn pentesting",
    "I want to start bug bounty hunting",
]


def evaluate_model(model_path, tokenizer_path=None, max_new_tokens=150):
    """Load model and run benchmark prompts."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
    except ImportError:
        print(colored("[!] transformers not installed. Skipping evaluation.", "31"))
        return []

    print(colored("\n[*] Loading model for evaluation...", "33"))
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path or model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    model.eval()

    results = []
    for prompt in BENCHMARK_PROMPTS:
        messages = [
            {"role": "system", "content": "You are CYBER-OMNI, an elite cybersecurity AI assistant."},
            {"role": "user", "content": prompt},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        start = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                do_sample=True,
            )
        elapsed = time.time() - start

        response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
        tokens_per_sec = max_new_tokens / elapsed if elapsed > 0 else 0

        results.append({
            "prompt": prompt,
            "response": response[:300],
            "time": round(elapsed, 2),
            "tokens_per_sec": round(tokens_per_sec, 1),
        })

        print(colored(f"\n{'='*50}", "36"))
        print(colored(f"Prompt: {prompt}", "33"))
        print(colored(f"Time: {elapsed:.2f}s ({tokens_per_sec:.1f} tok/s)", "32"))
        print(colored(f"Response: {response[:200]}...", "37"))

    return results


def compare_models(original_path, finetuned_path):
    """Compare original vs fine-tuned model on same prompts."""
    print(colored("\n" + "=" * 55, "36"))
    print(colored("  MODEL COMPARISON", "36"))
    print(colored("=" * 55, "36"))

    print(colored("\n[*] Testing original model...", "33"))
    original_results = evaluate_model(original_path)

    print(colored("\n[*] Testing fine-tuned model...", "33"))
    finetuned_results = evaluate_model(finetuned_path)

    print(colored("\n" + "=" * 55, "36"))
    print(colored("  COMPARISON SUMMARY", "36"))
    print(colored("=" * 55, "36"))

    for orig, ft in zip(original_results, finetuned_results):
        print(colored(f"\nPrompt: {orig['prompt']}", "33"))
        print(colored(f"  Original ({orig['time']}s): {orig['response'][:100]}", "31"))
        print(colored(f"  Fine-tuned ({ft['time']}s): {ft['response'][:100]}", "32"))
        print()

    return original_results, finetuned_results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CYBER-OMNI Model Evaluator")
    parser.add_argument("model", help="Path to model directory or GGUF file")
    parser.add_argument("--tokenizer", help="Tokenizer path (if different from model)")
    parser.add_argument("--compare", help="Path to second model for comparison")
    parser.add_argument("--max-tokens", type=int, default=200, help="Max generation tokens")
    args = parser.parse_args()

    if args.compare:
        compare_models(args.model, args.compare)
    else:
        evaluate_model(args.model, args.tokenizer, args.max_tokens)


if __name__ == "__main__":
    main()
