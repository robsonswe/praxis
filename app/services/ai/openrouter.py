import os
from typing import List, Dict
from openrouter import OpenRouter
from .base import AIProvider, get_rate_limiter

class OpenRouterProvider(AIProvider):
    @property
    def name(self) -> str:
        return "openrouter"
    
    @property
    def display_name(self) -> str:
        return "OpenRouter"
    
    @staticmethod
    def has_api_key() -> bool:
        return bool(os.getenv("OPENROUTER_API_KEY"))
    
    def get_rate_limit_config(self) -> Dict:
        return {
            "requests_per_minute": 60,
            "tokens_per_minute": 100000,
            "max_retries": 3,
            "timeout_seconds": 60
        }
    
    async def get_models(self) -> List[Dict[str, str]]:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            return []
        
        await limiter.wait_if_needed()
        
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        try:
            with OpenRouter(api_key=api_key) as client:
                response = client.models.list()
                models = []
                for m in response.data:
                    # Filter to text models only
                    if hasattr(m, 'supported_parameters') and 'text' in str(getattr(m, 'output_modalities', ['text'])):
                        models.append({
                            "id": m.id,
                            "name": getattr(m, 'display_name', m.id) or m.id
                        })
                return models[:50]  # Limit to 50 to avoid huge lists
        except Exception as e:
            print(f"Error fetching OpenRouter models: {e}")
            return []
    
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            raise Exception("OpenRouter API key not configured")
        
        await limiter.wait_if_needed()
        
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        try:
            with OpenRouter(api_key=api_key) as client:
                response = client.chat.send(
                    model=model,
                    messages=messages
                )
                return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenRouter API error: {str(e)}")
    
    async def chat_streaming(self, messages: List[Dict[str, str]], model: str):
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            raise Exception("OpenRouter API key not configured")
        
        await limiter.wait_if_needed()
        
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        with OpenRouter(api_key=api_key) as client:
            response = client.chat.send(
                model=model,
                messages=messages,
                stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content