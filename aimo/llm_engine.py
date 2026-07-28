# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
LLM Engine - Unified interface for math reasoning models.

Supports four backends:
- vllm: For Kaggle H100 deployment (GPT-OSS-120B or Qwen2.5-Math-72B)
- transformers: For local GPU (Qwen2.5-Math-1.5B or 7B)
- hf_api: HuggingFace Inference API (online)
- openrouter: OpenRouter API (OpenAI-compatible, supports GPT-OSS-120B)
"""

import sys
import os
import re
import time
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

sys.path.insert(0, '.')


@dataclass
class LLMConfig:
    """Configuration for the LLM engine."""
    model_name: str = "Qwen/Qwen2.5-Math-72B-Instruct"
    backend: str = "hf_api"  # "vllm", "transformers", "hf_api", "openrouter"
    max_tokens: int = 2048
    temperature: float = 0.7
    n_samples: int = 1
    tensor_parallel_size: int = 4
    top_p: float = 0.95
    stop_tokens: List[str] = field(default_factory=lambda: ["\n\nProblem", "---"])
    seed: Optional[int] = None
    api_token: Optional[str] = None  # HF token, OpenRouter key, or set env var
    api_base: Optional[str] = None  # Custom API base URL (e.g. OpenRouter)


class LLMEngine:
    """
    Unified LLM interface for mathematical reasoning.

    Provides generate() and generate_batch() regardless of backend.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._model = None
        self._tokenizer = None
        self._initialized = False

    def initialize(self):
        """Lazy initialization of the backend."""
        if self._initialized:
            return

        if self.config.backend == "vllm":
            self._init_vllm()
        elif self.config.backend == "transformers":
            self._init_transformers()
        elif self.config.backend == "hf_api":
            self._init_hf_api()
        elif self.config.backend == "openrouter":
            self._init_openrouter()
        elif self.config.backend == "mock":
            pass  # Mock backend: generate() returns empty, used for testing
        else:
            raise ValueError(f"Unknown backend: {self.config.backend}")

        self._initialized = True

    def _init_vllm(self):
        """Initialize vLLM backend for Kaggle H100 deployment."""
        try:
            from vllm import LLM, SamplingParams  # noqa: F401
            self._model = LLM(
                model=self.config.model_name,
                tensor_parallel_size=self.config.tensor_parallel_size,
                trust_remote_code=True,
                max_model_len=4096,
                gpu_memory_utilization=0.9,
            )
            self._sampling_params_cls = SamplingParams
        except ImportError:
            raise ImportError(
                "vLLM not installed. Install with: pip install vllm"
            )

    def _init_transformers(self):
        """Initialize HuggingFace Transformers backend for local GPU."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: F401
            import torch  # noqa: F401

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model_name = self.config.model_name

            self._tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True,
            )
            if device == "cpu":
                self._model = self._model.to(device)
        except ImportError:
            raise ImportError(
                "transformers not installed. Install with: pip install transformers torch"
            )

    def _init_hf_api(self):
        """Initialize HuggingFace Inference API backend."""
        from huggingface_hub import InferenceClient

        self._hf_token = (
            self.config.api_token
            or os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        )
        if not self._hf_token:
            try:
                from huggingface_hub import HfFolder
                self._hf_token = HfFolder.get_token()
            except Exception:
                pass

        self._hf_client = InferenceClient(
            self.config.model_name,
            token=self._hf_token,
            timeout=120,
        )

    def _init_openrouter(self):
        """Initialize OpenRouter API backend (OpenAI-compatible)."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            )

        api_key = (
            self.config.api_token
            or os.environ.get("OPENROUTER_API_KEY")
        )
        if not api_key:
            raise ValueError(
                "OpenRouter API key required. Set api_token in LLMConfig "
                "or OPENROUTER_API_KEY env var."
            )

        base_url = self.config.api_base or "https://openrouter.ai/api/v1"
        self._openai_client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

    def _generate_openrouter(self, prompt: str, n: int, temperature: float) -> List[str]:
        """Generate using OpenRouter API (OpenAI-compatible chat completions)."""
        import time
        results = []
        for _ in range(n):
            text = ""
            for attempt in range(3):  # 3 retries
                try:
                    response = self._openai_client.chat.completions.create(
                        model=self.config.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=self.config.max_tokens,
                        temperature=max(temperature, 0.01),
                        top_p=self.config.top_p,
                    )
                    text = response.choices[0].message.content or ""
                    break  # Success
                except Exception as e:
                    if attempt < 2:  # Don't sleep on last attempt
                        wait = 2 ** attempt  # 1s, 2s exponential backoff
                        print(f"  [OpenRouter] Retry {attempt+1}/3 after {wait}s: {e}", file=sys.stderr, flush=True)
                        time.sleep(wait)
                    else:
                        print(f"  [OpenRouter] Failed after 3 attempts: {e}", file=sys.stderr, flush=True)
            results.append(text)
        return results

    def _generate_chat_openrouter(self, messages: List[Dict[str, str]], n: int,
                                   temperature: float) -> List[str]:
        """Generate chat completion via OpenRouter API."""
        import time
        results = []
        for _ in range(n):
            text = ""
            for attempt in range(3):  # 3 retries
                try:
                    response = self._openai_client.chat.completions.create(
                        model=self.config.model_name,
                        messages=messages,
                        max_tokens=self.config.max_tokens,
                        temperature=max(temperature, 0.01),
                        top_p=self.config.top_p,
                    )
                    text = response.choices[0].message.content or ""
                    break  # Success
                except Exception as e:
                    if attempt < 2:  # Don't sleep on last attempt
                        wait = 2 ** attempt  # 1s, 2s exponential backoff
                        print(f"  [OpenRouter chat] Retry {attempt+1}/3 after {wait}s: {e}", file=sys.stderr, flush=True)
                        time.sleep(wait)
                    else:
                        print(f"  [OpenRouter chat] Failed after 3 attempts: {e}", file=sys.stderr, flush=True)
            results.append(text)
        return results

    def _generate_hf_api(self, prompt: str, n: int, temperature: float) -> List[str]:
        """Generate using HuggingFace Inference API via chat_completion."""
        results = []
        for _ in range(n):
            try:
                response = self._hf_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=min(self.config.max_tokens, 2048),
                    temperature=max(temperature, 0.01),
                    top_p=self.config.top_p,
                )
                text = response.choices[0].message.content
                results.append(text)
            except Exception as e:
                print(f"  [HF API] Error: {e}", file=sys.stderr)
                results.append("")

        return results

    def generate(self, prompt: str, n: int = 1, temperature: Optional[float] = None) -> List[str]:
        """
        Generate n responses for a single prompt.

        Args:
            prompt: The input prompt
            n: Number of responses to generate
            temperature: Override config temperature

        Returns:
            List of n response strings
        """
        self.initialize()
        temp = temperature if temperature is not None else self.config.temperature

        if self.config.backend == "vllm":
            return self._generate_vllm(prompt, n, temp)
        elif self.config.backend == "transformers":
            return self._generate_transformers(prompt, n, temp)
        elif self.config.backend == "hf_api":
            return self._generate_hf_api(prompt, n, temp)
        elif self.config.backend == "openrouter":
            return self._generate_openrouter(prompt, n, temp)
        else:
            raise ValueError(f"Unknown backend: {self.config.backend}")

    def generate_chat(self, messages: List[Dict[str, str]], n: int = 1,
                       temperature: Optional[float] = None) -> List[str]:
        """
        Multi-turn chat completion.

        Args:
            messages: List of {role, content} dicts
            n: Number of responses
            temperature: Override config temperature

        Returns:
            List of n response strings
        """
        self.initialize()
        temp = temperature if temperature is not None else self.config.temperature

        if self.config.backend == "hf_api":
            return self._generate_chat_hf_api(messages, n, temp)
        elif self.config.backend == "openrouter":
            return self._generate_chat_openrouter(messages, n, temp)
        elif self.config.backend in ("vllm", "transformers"):
            # Format messages into single prompt
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    prompt_parts.append(f"System: {content}")
                elif role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            prompt_parts.append("Assistant:")
            prompt = "\n\n".join(prompt_parts)
            return self.generate(prompt, n=n, temperature=temp)
        else:
            raise ValueError(f"Unknown backend: {self.config.backend}")

    def _generate_chat_hf_api(self, messages: List[Dict[str, str]], n: int,
                               temperature: float) -> List[str]:
        """Generate chat completion via HuggingFace Inference API."""
        results = []
        for i in range(n):
            try:
                response = self._hf_client.chat_completion(
                    messages=messages,
                    max_tokens=min(self.config.max_tokens, 2048),
                    temperature=max(temperature, 0.01),
                    top_p=self.config.top_p,
                )
                text = response.choices[0].message.content
                results.append(text)
            except Exception as e:
                print(f"  [HF API chat] Error: {e}", file=sys.stderr)
                results.append("")
        return results

    def generate_batch(self, prompts: List[str], n: int = 1) -> List[List[str]]:
        """
        Generate responses for multiple prompts.

        Args:
            prompts: List of input prompts
            n: Number of responses per prompt

        Returns:
            List of lists, each containing n response strings
        """
        self.initialize()

        if self.config.backend == "vllm":
            return self._generate_batch_vllm(prompts, n)
        else:
            # For transformers, hf_api, and openrouter, process sequentially
            return [self.generate(p, n) for p in prompts]

    def _generate_vllm(self, prompt: str, n: int, temperature: float) -> List[str]:
        """Generate using vLLM."""
        params = self._sampling_params_cls(
            max_tokens=self.config.max_tokens,
            temperature=temperature,
            top_p=self.config.top_p,
            n=n,
            stop=self.config.stop_tokens,
            seed=self.config.seed,
        )
        outputs = self._model.generate([prompt], params)
        return [out.text for out in outputs[0].outputs]

    def _generate_batch_vllm(self, prompts: List[str], n: int) -> List[List[str]]:
        """Batch generate using vLLM (leverages continuous batching)."""
        params = self._sampling_params_cls(
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            n=n,
            stop=self.config.stop_tokens,
            seed=self.config.seed,
        )
        outputs = self._model.generate(prompts, params)
        return [[out.text for out in output.outputs] for output in outputs]

    def _generate_transformers(self, prompt: str, n: int, temperature: float) -> List[str]:
        """Generate using HuggingFace Transformers."""
        import torch

        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        results = []

        for _ in range(n):
            with torch.no_grad():
                output = self._model.generate(
                    **inputs,
                    max_new_tokens=self.config.max_tokens,
                    temperature=max(temperature, 0.01),
                    top_p=self.config.top_p,
                    do_sample=temperature > 0,
                )
            response = self._tokenizer.decode(
                output[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            results.append(response)

        return results

    @staticmethod
    def extract_answer(response: str) -> Optional[int]:
        """
        Extract integer answer from an LLM response.

        Tries multiple patterns:
        1. \\boxed{N}
        2. "answer is N"
        3. "= N" at end of line
        4. Last integer in response
        """
        # Pattern 1: \boxed{N}
        boxed = re.findall(r'\\boxed\{(\d+)\}', response)
        if boxed:
            try:
                return int(boxed[-1])
            except ValueError:
                pass

        # Pattern 2: "answer is N" or "Answer: N"
        answer_match = re.search(
            r'(?:answer|result)\s*(?:is|=|:)\s*(\d+)',
            response, re.IGNORECASE
        )
        if answer_match:
            try:
                return int(answer_match.group(1))
            except ValueError:
                pass

        # Pattern 3: "= N" at end of line
        eq_match = re.findall(r'=\s*(\d+)\s*$', response, re.MULTILINE)
        if eq_match:
            try:
                return int(eq_match[-1])
            except ValueError:
                pass

        # Pattern 4: Last integer in response
        all_ints = re.findall(r'\b(\d+)\b', response)
        if all_ints:
            try:
                return int(all_ints[-1])
            except ValueError:
                pass

        return None

    @staticmethod
    def build_math_prompt(problem_text: str, strategy: str = "general") -> str:
        """
        Build a math reasoning prompt for the LLM.

        Args:
            problem_text: The math problem in LaTeX or plain text
            strategy: Strategy hint for the LLM

        Returns:
            Formatted prompt string
        """
        return (
            f"Please solve the following mathematics competition problem. "
            f"Show your reasoning step by step. "
            f"If helpful, include Python code to verify. "
            f"Put your final integer answer in \\boxed{{}}.\n\n"
            f"Strategy hint: {strategy}\n\n"
            f"Problem: {problem_text}\n\n"
            f"Solution:"
        )
