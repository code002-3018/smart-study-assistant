"""LLM client abstraction for free model providers.

Supported providers (selected via environment variable LLM_PROVIDER):
- "gemini"  -> Gemini 2.0 Flash (Generative Language API)
- "deepseek" -> DeepSeek-V3 (OpenAI-compatible chat API)
- "llama" -> Llama 3.1 70B via HuggingFace Inference API

All API keys are read from environment variables and MUST NOT be
hard-coded:
- GEMINI_API_KEY
- DEEPSEEK_API_KEY
- HF_API_KEY
"""

from __future__ import annotations

import json
import os
from typing import Optional

import requests


class LLMClient:
    """Thin wrapper around multiple free LLM providers."""

    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.4,
    ) -> str:
        """Generate a completion for the given prompt.

        The exact API call depends on the provider selected.
        """

        if self.provider == "deepseek":
            return self._generate_deepseek(prompt, system_prompt, max_tokens, temperature)
        if self.provider == "llama":
            return self._generate_llama_hf(prompt, system_prompt, max_tokens, temperature)
        # Default to Gemini
        return self._generate_gemini(prompt, system_prompt, max_tokens, temperature)

    # ------------------------------------------------------------------
    # Provider-specific implementations
    # ------------------------------------------------------------------
    def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.0-flash:generateContent"
        )
        headers = {"Content-Type": "application/json"}

        messages = []
        if system_prompt:
            messages.append({"role": "user", "parts": [{"text": system_prompt}]})
        messages.append({"role": "user", "parts": [{"text": prompt}]})

        body = {
            "contents": messages,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        resp = requests.post(url, headers=headers, params={"key": api_key}, json=body, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Unexpected Gemini response: {data}") from exc

    def _generate_deepseek(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> str:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set.")

        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(url, headers=headers, json=body, timeout=60)
        
        # Debug logging
        if resp.status_code != 200:
            print(f"❌ DeepSeek API Error - Status: {resp.status_code}")
            print(f"Response: {resp.text}")
        
        resp.raise_for_status()
        data = resp.json()
        
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            print(f"DeepSeek Response: {data}")
            raise RuntimeError(f"Unexpected DeepSeek response: {data}") from exc

    def _generate_llama_hf(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> str:
        api_key = os.getenv("HF_API_KEY")
        if not api_key:
            raise RuntimeError("HF_API_KEY is not set.")

        url = (
            "https://api-inference.huggingface.co/models/"
            "meta-llama/Meta-Llama-3.1-70B-Instruct"
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        body = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
            },
        }

        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # HF text generation APIs typically return a list of dicts with 'generated_text'
        try:
            if isinstance(data, list):
                return data[0].get("generated_text", "").strip()
            # Fallback to generic form
            return str(data)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Unexpected HF response: {data}") from exc
