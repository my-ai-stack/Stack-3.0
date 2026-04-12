#!/usr/bin/env python3
"""
Stack 3.0 Model Client
Unified API client for Ollama, OpenAI, Anthropic, and other LLM backends.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result from model generation."""
    text: str
    model: str
    tokens: int
    duration: float
    finish_reason: str
    raw_response: Optional[Dict] = None


@dataclass
class ChatMessage:
    """Chat message structure."""
    role: str  # "system", "user", "assistant"
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


class BaseModelClient(ABC):
    """Abstract base class for model clients."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate response from chat messages."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name."""
        pass


class OllamaClient(BaseModelClient):
    """Client for Ollama local API."""

    def __init__(
        self,
        model: str = "qwen2.5-coder:32b",
        base_url: str = "http://localhost:11434",
        timeout: int = 300
    ):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text using Ollama."""
        import requests

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        if stop:
            payload["stop"] = stop

        start_time = time.time()

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            duration = time.time() - start_time

            return GenerationResult(
                text=data.get("response", ""),
                model=self.model,
                tokens=data.get("eval_count", 0),
                duration=duration,
                finish_reason=data.get("done_reason", "stop"),
                raw_response=data
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate chat response using Ollama."""
        import requests

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        if tools:
            payload["tools"] = tools

        start_time = time.time()

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            duration = time.time() - start_time

            # Extract response
            msg = data.get("message", {})
            text = msg.get("content", "")

            return GenerationResult(
                text=text,
                model=self.model,
                tokens=data.get("eval_count", 0),
                duration=duration,
                finish_reason=data.get("done_reason", "stop"),
                raw_response=data
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama chat request failed: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model


class OpenAIClient(BaseModelClient):
    """Client for OpenAI API."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")

    def _get_client(self):
        """Get OpenAI client."""
        try:
            from openai import OpenAI
            return OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text using OpenAI."""
        client = self._get_client()

        start_time = time.time()

        try:
            response = client.completions.create(
                model=self.model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                **kwargs
            )

            duration = time.time() - start_time

            return GenerationResult(
                text=response.choices[0].text,
                model=self.model,
                tokens=response.usage.completion_tokens,
                duration=duration,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response.model_dump()
            )
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            raise

    def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate chat response using OpenAI."""
        client = self._get_client()

        # Convert messages to OpenAI format
        chat_messages = []
        for msg in messages:
            msg_dict = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            chat_messages.append(msg_dict)

        # Build request
        request_params = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            request_params["tools"] = tools

        request_params.update(kwargs)

        start_time = time.time()

        try:
            response = client.chat.completions.create(**request_params)

            duration = time.time() - start_time

            msg = response.choices[0].message
            text = msg.content or ""

            return GenerationResult(
                text=text,
                model=self.model,
                tokens=response.usage.completion_tokens,
                duration=duration,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response.model_dump()
            )
        except Exception as e:
            logger.error(f"OpenAI chat request failed: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model


class AnthropicClient(BaseModelClient):
    """Client for Anthropic API."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        timeout: int = 120
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY environment variable.")

    def _get_client(self):
        """Get Anthropic client."""
        try:
            from anthropic import Anthropic
            return Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs
    ) -> GenerationResult:
        """Generate text using Anthropic."""
        client = self._get_client()

        # Anthropic uses system prompt separately
        system = kwargs.pop("system", None)
        if system:
            messages = [{"role": "user", "content": prompt}]
            messages = [{"role": "system", "content": system}] + messages
        else:
            messages = [{"role": "user", "content": prompt}]

        start_time = time.time()

        try:
            response = client.messages.create(
                model=self.model,
                system=system,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            duration = time.time() - start_time

            text = response.content[0].text if response.content else ""

            return GenerationResult(
                text=text,
                model=self.model,
                tokens=response.usage.output_tokens,
                duration=duration,
                finish_reason=response.stop_reason,
                raw_response=response.model_dump()
            )
        except Exception as e:
            logger.error(f"Anthropic request failed: {e}")
            raise

    def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate chat response using Anthropic."""
        client = self._get_client()

        # Convert to Anthropic format
        # System message should be separate
        system = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        request_params = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system:
            request_params["system"] = system

        if tools:
            request_params["tools"] = tools

        request_params.update(kwargs)

        start_time = time.time()

        try:
            response = client.messages.create(**request_params)

            duration = time.time() - start_time

            text = response.content[0].text if response.content else ""

            return GenerationResult(
                text=text,
                model=self.model,
                tokens=response.usage.output_tokens,
                duration=duration,
                finish_reason=response.stop_reason,
                raw_response=response.model_dump()
            )
        except Exception as e:
            logger.error(f"Anthropic chat request failed: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model


class TogetherClient(BaseModelClient):
    """Client for Together AI API (OpenAI-compatible)."""

    def __init__(
        self,
        model: str = "togethercomputer/Qwen2.5-Coder-32B-Instruct",
        api_key: Optional[str] = None,
        base_url: str = "https://api.together.xyz/v1",
        timeout: int = 120
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("TOGETHER_API_KEY", "")
        self.base_url = base_url
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("Together API key required. Set TOGETHER_API_KEY environment variable.")

    def _get_client(self):
        """Get OpenAI-compatible client."""
        try:
            from openai import OpenAI
            return OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text using Together."""
        client = self._get_client()

        start_time = time.time()

        try:
            response = client.completions.create(
                model=self.model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                **kwargs
            )

            duration = time.time() - start_time

            return GenerationResult(
                text=response.choices[0].text,
                model=self.model,
                tokens=response.usage.completion_tokens,
                duration=duration,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response.model_dump()
            )
        except Exception as e:
            logger.error(f"Together request failed: {e}")
            raise

    def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate chat response using Together."""
        client = self._get_client()

        # Convert messages to chat format
        chat_messages = [{"role": m.role, "content": m.content} for m in messages]

        request_params = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            request_params["tools"] = tools

        request_params.update(kwargs)

        start_time = time.time()

        try:
            response = client.chat.completions.create(**request_params)

            duration = time.time() - start_time

            msg = response.choices[0].message
            text = msg.content or ""

            result = GenerationResult(
                text=text,
                model=self.model,
                tokens=response.usage.completion_tokens,
                duration=duration,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response.model_dump()
            )

            return result
        except Exception as e:
            logger.error(f"Together chat request failed: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model


class OpenRouterClient(BaseModelClient):
    """Client for OpenRouter API (unified interface for multiple models)."""

    def __init__(
        self,
        model: str = "qwen/qwen2.5-coder-32b",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 120,
        http_referer: Optional[str] = None,
        x_title: Optional[str] = None
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = base_url
        self.timeout = timeout
        self.http_referer = http_referer or os.environ.get("HTTP_REFERER", "")
        self.x_title = x_title or os.environ.get("X_TITLE", "Stack 3.0")

        if not self.api_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY environment variable.")

    def _get_client(self):
        """Get OpenAI-compatible client."""
        try:
            from openai import OpenAI
            return OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text using OpenRouter."""
        client = self._get_client()

        start_time = time.time()

        try:
            response = client.completions.create(
                model=self.model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                **kwargs
            )

            duration = time.time() - start_time

            result = GenerationResult(
                text=response.choices[0].text,
                model=self.model,
                tokens=response.usage.completion_tokens,
                duration=duration,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response.model_dump()
            )

            return result
        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            raise

    def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate chat response using OpenRouter."""
        client = self._get_client()

        # Convert messages to chat format
        chat_messages = [{"role": m.role, "content": m.content} for m in messages]

        request_params = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            request_params["tools"] = tools

        request_params.update(kwargs)

        # Add OpenRouter-specific headers
        extra_headers = {}
        if self.http_referer:
            extra_headers["HTTP-Referer"] = self.http_referer
        if self.x_title:
            extra_headers["X-Title"] = self.x_title

        start_time = time.time()

        try:
            response = client.chat.completions.create(
                extra_headers=extra_headers if extra_headers else None,
                **request_params
            )

            duration = time.time() - start_time

            msg = response.choices[0].message
            text = msg.content or ""

            result = GenerationResult(
                text=text,
                model=self.model,
                tokens=response.usage.completion_tokens,
                duration=duration,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response.model_dump()
            )

            return result
        except Exception as e:
            logger.error(f"OpenRouter chat request failed: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model



def create_model_client(
    provider: str = "ollama",
    model: Optional[str] = None,
    **kwargs
) -> BaseModelClient:
    """
    Factory function to create model client.

    Args:
        provider: One of "ollama", "openai", "anthropic", "openrouter", "together"
        model: Model name (defaults to provider's default)
        **kwargs: Additional client configuration

    Returns:
        BaseModelClient instance
    """
    if provider == "ollama":
        default_model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:32b")
        return OllamaClient(model=default_model, **kwargs)
    elif provider == "openai":
        default_model = model or os.environ.get("OPENAI_MODEL", "gpt-4o")
        return OpenAIClient(model=default_model, **kwargs)
    elif provider == "anthropic":
        default_model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        return AnthropicClient(model=default_model, **kwargs)
    elif provider == "openrouter":
        default_model = model or os.environ.get("OPENROUTER_MODEL", "qwen/qwen2.5-coder-32b")
        return OpenRouterClient(model=default_model, **kwargs)
    elif provider == "together":
        default_model = model or os.environ.get("TOGETHER_MODEL", "togethercomputer/Qwen2.5-Coder-32B-Instruct")
        return TogetherClient(model=default_model, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use: ollama, openai, anthropic, openrouter, together")


class ModelClientPool:
    """Pool of model clients for different purposes."""

    def __init__(self):
        self.clients: Dict[str, BaseModelClient] = {}

    def add_client(self, name: str, client: BaseModelClient):
        """Add a client to the pool."""
        self.clients[name] = client

    def get_client(self, name: str = "default") -> BaseModelClient:
        """Get client by name."""
        if name not in self.clients:
            # Try to create default client
            provider = os.environ.get("MODEL_PROVIDER", "ollama")
            self.clients[name] = create_model_client(provider)
        return self.clients[name]

    def generate(
        self,
        prompt: str,
        client_name: str = "default",
        **kwargs
    ) -> GenerationResult:
        """Generate using named client."""
        return self.get_client(client_name).generate(prompt, **kwargs)

    def chat(
        self,
        messages: List[ChatMessage],
        client_name: str = "default",
        **kwargs
    ) -> GenerationResult:
        """Chat using named client."""
        return self.get_client(client_name).chat(messages, **kwargs)


# Default pool instance
_default_pool = None

def get_default_pool() -> ModelClientPool:
    """Get default model client pool."""
    global _default_pool
    if _default_pool is None:
        _default_pool = ModelClientPool()
    return _default_pool


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stack 3.0 Model Client")
    parser.add_argument("--provider", choices=["ollama", "openai", "anthropic", "openrouter", "together"],
                        default="ollama", help="Model provider")
    parser.add_argument("--model", type=str, help="Model name")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt to generate")
    parser.add_argument("--temperature", type=float, default=0.2, help="Temperature")

    args = parser.parse_args()

    # Create client
    client = create_model_client(args.provider, args.model)

    print(f"Using model: {client.get_model_name()}")
    print(f"Provider: {args.provider}")
    print("-" * 40)

    # Generate
    result = client.generate(args.prompt, temperature=args.temperature)

    print(f"Response:\n{result.text}")
    print("-" * 40)
    print(f"Tokens: {result.tokens}, Duration: {result.duration:.2f}s")