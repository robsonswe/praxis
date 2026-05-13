import os
import httpx
import base64
from typing import List, Dict
from openai import AsyncOpenAI
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

    async def _get_models_by_modality(self, modality: str) -> List[Dict]:
        """Fetch models from OpenRouter filtered by modality."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"}
                response = await client.get(
                    f"https://openrouter.ai/api/v1/models?output_modalities={modality}", 
                    headers=headers
                )
                data = response.json().get("data", [])
                return [{"id": m["id"], "name": m.get("name", m["id"])} for m in data]
        except Exception as e:
            print(f"Error fetching OpenRouter models ({modality}): {e}")
            return []

    async def get_models(self) -> List[Dict]:
        # Fetch text models by default
        return await self._get_models_by_modality("text")

    async def get_models_by_category(self, category: str) -> List[Dict[str, str]]:
        if category == "stt":
            return await self._get_models_by_modality("transcription")
        elif category == "tts":
            return await self._get_models_by_modality("speech")
        else:
            return await self.get_models()
    
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        await limiter.wait_if_needed()
        
        client = AsyncOpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        response = await client.chat.completions.create(model=model, messages=messages)
        return response.choices[0].message.content
    
    async def chat_streaming(self, messages: List[Dict[str, str]], model: str):
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        await limiter.wait_if_needed()
        
        client = AsyncOpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1")
        stream = await client.chat.completions.create(model=model, messages=messages, stream=True)
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def stt(self, audio_data: bytes, model: str) -> str:
        async with httpx.AsyncClient() as client:
            encoded_audio = base64.b64encode(audio_data).decode("utf-8")
            payload = {
                "model": model,
                "input_audio": {"data": encoded_audio, "format": "wav"}
            }
            response = await client.post(
                "https://openrouter.ai/api/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"},
                json=payload, timeout=60.0
            )
            if response.status_code != 200:
                raise Exception(f"OpenRouter STT failed: {response.text}")
            return response.json().get("text", "")

    async def tts(self, text: str, model: str) -> bytes:
        async with httpx.AsyncClient() as client:
            payload = {
                "model": model,
                "input": text,
                "voice": "alloy",
                "response_format": "mp3"
            }
            response = await client.post(
                "https://openrouter.ai/api/v1/audio/speech",
                headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"},
                json=payload, timeout=60.0
            )
            if response.status_code != 200:
                raise Exception(f"OpenRouter TTS failed: {response.text}")
            return response.content
