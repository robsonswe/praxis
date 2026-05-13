from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name"""
        pass
    
    @staticmethod
    @abstractmethod
    def has_api_key() -> bool:
        """Check if API key is configured"""
        pass
    
    @abstractmethod
    async def get_models(self) -> List[Dict[str, str]]:
        """Get list of available models. Returns list of {id, name}"""
        pass

    async def get_models_by_category(self, category: str) -> List[Dict[str, str]]:
        """Get models for a specific category (text_chat, stt, tts)"""
        # Default implementation: return all models and let the provider override filtering
        return await self.get_models()
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        """Send chat request and return response content"""
        pass
    
    @abstractmethod
    async def chat_streaming(self, messages: List[Dict[str, str]], model: str):
        """Yield chunks for streaming responses"""
        pass

    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def connect_live(self, model: str, config: Dict):
        """Connect to a live multimodal session"""
        yield None
        raise NotImplementedError(f"Live session not implemented for {self.name}")

    async def stt(self, audio_data: bytes, model: str) -> str:
        """Transcribe audio data to text"""
        raise NotImplementedError(f"STT not implemented for {self.name}")

    async def tts(self, text: str, model: str) -> bytes:
        """Convert text to speech audio data (mp3/wav)"""
        raise NotImplementedError(f"TTS not implemented for {self.name}")

    def get_rate_limit_config(self) -> Dict:
        """Get rate limit configuration for this provider"""
        return {
            "requests_per_minute": 60,
            "tokens_per_minute": 90000,
            "max_retries": 3,
            "timeout_seconds": 60
        }


class RateLimiter:
    """Simple in-memory rate limiter using token bucket"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
    
    def can_proceed(self) -> bool:
        from time import time
        now = time()
        # Remove requests older than 1 minute
        self.requests = [ts for ts in self.requests if now - ts < 60]
        return len(self.requests) < self.requests_per_minute
    
    def record_request(self):
        from time import time
        self.requests.append(time())
    
    async def wait_if_needed(self):
        """Wait if rate limit exceeded, then proceed"""
        import asyncio
        while not self.can_proceed():
            await asyncio.sleep(1)
        self.record_request()


# Global rate limiters per provider
_rate_limiters: Dict[str, RateLimiter] = {}

def get_rate_limiter(provider_name: str, requests_per_minute: int = 60) -> RateLimiter:
    if provider_name not in _rate_limiters:
        _rate_limiters[provider_name] = RateLimiter(requests_per_minute)
    return _rate_limiters[provider_name]