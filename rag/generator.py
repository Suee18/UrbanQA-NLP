"""Pluggable LLM generator — used by BOTH graph nodes (rewrite + answer).

One interface, two backends, chosen by config (`generator.backend`):
  - LocalGenerator : Qwen2.5-Instruct via HF transformers (runs on your GPU)
  - APIGenerator   : Claude via the anthropic SDK (needs ANTHROPIC_API_KEY)

Both expose chat(messages) -> str, where messages is the OpenAI-style list
[{"role": "system"|"user"|"assistant", "content": "..."}].
"""

from __future__ import annotations
from rag.config import load_config, anthropic_api_key, env


class BaseGenerator:
    def chat(self, messages: list[dict]) -> str:
        raise NotImplementedError


# ── Local backend (Qwen2.5 via transformers) ─────────────────────────────
class LocalGenerator(BaseGenerator):
    def __init__(self, cfg: dict):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_name = cfg["local"]["model"]
        self.temperature = cfg.get("temperature", 0.1)
        self.max_tokens = cfg.get("max_tokens", 512)

        print(f"Loading local LLM {self.model_name} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype="auto",
            device_map="auto",          # uses CUDA if available
        )
        self.model.eval()
        self._torch = torch

    def chat(self, messages: list[dict]) -> str:
        # Qwen chat template turns the message list into a prompt string.
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        with self._torch.no_grad():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=self.max_tokens,
                do_sample=self.temperature > 0,
                temperature=max(self.temperature, 1e-5),
                pad_token_id=self.tokenizer.eos_token_id,
            )
        # Strip the prompt tokens, decode only the new completion.
        new_tokens = generated[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


# ── API backend (Claude) ──────────────────────────────────────────────────
class APIGenerator(BaseGenerator):
    def __init__(self, cfg: dict):
        from anthropic import Anthropic

        key = anthropic_api_key()
        if not key:
            raise RuntimeError(
                "generator.backend is 'api' but ANTHROPIC_API_KEY is not set in .env."
            )
        self.client = Anthropic(api_key=key)
        self.model_name = cfg["api"]["model"]
        self.temperature = cfg.get("temperature", 0.1)
        self.max_tokens = cfg.get("max_tokens", 512)

    def chat(self, messages: list[dict]) -> str:
        # Anthropic takes the system prompt separately from the turn list.
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        turns = [
            {"role": m["role"], "content": m["content"]}
            for m in messages if m["role"] in ("user", "assistant")
        ]
        resp = self.client.messages.create(
            model=self.model_name,
            system=system or None,
            messages=turns,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()


# ── Groq backend (free, fast, OpenAI-compatible) ──────────────────────────
class GroqGenerator(BaseGenerator):
    """Free Groq cloud inference. Get a key at https://console.groq.com
    and put GROQ_API_KEY in .env. Model set in config.generator.groq.model."""

    def __init__(self, cfg: dict):
        from groq import Groq

        key = env("GROQ_API_KEY")
        if not key:
            raise RuntimeError(
                "generator.backend is 'groq' but GROQ_API_KEY is not set in .env. "
                "Get a free key at https://console.groq.com."
            )
        self.client = Groq(api_key=key)
        self.model_name = cfg["groq"]["model"]
        self.temperature = cfg.get("temperature", 0.1)
        self.max_tokens = cfg.get("max_tokens", 512)

    def chat(self, messages: list[dict]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,                 # OpenAI-style; Groq accepts as-is
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content.strip()


def make_generator(config: dict | None = None) -> BaseGenerator:
    """Factory: build the generator named by config.generator.backend."""
    cfg = (config or load_config())["generator"]
    backend = cfg.get("backend", "local").lower()
    if backend == "local":
        return LocalGenerator(cfg)
    if backend == "groq":
        return GroqGenerator(cfg)
    if backend == "api":
        return APIGenerator(cfg)
    raise ValueError(
        f"Unknown generator backend: {backend!r} (use 'local', 'groq', or 'api')"
    )
