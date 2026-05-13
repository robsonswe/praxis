import os
from typing import List, Dict
from anthropic import AsyncAnthropic
from .base import AIProvider, get_rate_limiter

class AnthropicProvider(AIProvider):
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def display_name(self) -> str:
        return "Anthropic (Claude)"
    
    @staticmethod
    def has_api_key() -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    
    def get_rate_limit_config(self) -> Dict:
        return {
            "requests_per_minute": 50,
            "tokens_per_minute": 100000,
            "max_retries": 3,
            "timeout_seconds": 60
        }
    
    async def get_models(self) -> List[Dict[str, str]]:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            return []
        
        await limiter.wait_if_needed()
        
        try:
            client = AsyncAnthropic()
            response = await client.models.list()
            models = []
            async for m in response:
                if hasattr(m, 'id'):
                    models.append({
                        "id": m.id,
                        "name": m.id
                    })
            return models[:50]
        except Exception as e:
            print(f"Error fetching Anthropic models: {e}")
            return []
    
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            raise Exception("Anthropic API key not configured")
        
        await limiter.wait_if_needed()
        
        try:
            client = AsyncAnthropic()
            # Convert messages to Anthropic format and extract system prompt
            anthropic_messages = []
            system_prompt = None
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                    continue
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            response = await client.messages.create(
                model=model,
                system=system_prompt,
                messages=anthropic_messages,
                max_tokens=1024
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    async def chat_streaming(self, messages: List[Dict[str, str]], model: str):
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            raise Exception("Anthropic API key not configured")
        
        await limiter.wait_if_needed()
        
        client = AsyncAnthropic()
        anthropic_messages = []
        system_prompt = None
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
                continue
            anthropic_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        async with client.messages.stream(
            model=model,
            system=system_prompt,
            messages=anthropic_messages,
            max_tokens=1024
        ) as stream:
            async for chunk in stream.text_stream:
                if chunk:
                    yield chunk