from .base import AIProvider
from .openrouter import OpenRouterProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .gemini import GeminiProvider
from .mistral import MistralProvider

PROVIDERS = {
    "openrouter": OpenRouterProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "mistral": MistralProvider,
}

def get_available_providers():
    """Returns dict of provider name -> provider instance for providers with valid API keys"""
    return {name: cls() for name, cls in PROVIDERS.items() if cls.has_api_key()}

def get_all_providers():
    """Returns dict of all providers regardless of API key"""
    return {name: cls() for name, cls in PROVIDERS.items()}

def get_provider(name: str) -> AIProvider:
    """Get provider instance by name"""
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}")
    return PROVIDERS[name]()

def get_provider_display_name(name: str) -> str:
    """Get human-readable name for a provider"""
    return get_provider(name).display_name