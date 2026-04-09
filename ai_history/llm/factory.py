from typing import Optional

from .base import LLMConfig, LLMProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider


def get_provider(
    provider: str = "gemini",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    provider = provider.lower()

    if provider == "gemini":
        config = LLMConfig(
            provider="gemini",
            model=model or "gemini-2.0-flash",
            api_key=api_key,
            **kwargs,
        )
        return GeminiProvider(config)

    elif provider == "ollama":
        config = LLMConfig(
            provider="ollama",
            model=model or "llama3.2",
            **kwargs,
        )
        return OllamaProvider(config)

    else:
        raise ValueError(f"Unknown provider: {provider}. Supported: gemini, ollama")
