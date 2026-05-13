import os
from typing import List, Dict, Optional, AsyncIterator
from contextlib import asynccontextmanager
from zai import ZaiClient
from .base import AIProvider, get_rate_limiter

class ZaiProvider(AIProvider):
    @property
    def name(self) -> str:
        return "zai"
    
    @property
    def display_name(self) -> str:
        return "Z.AI"
    
    @staticmethod
    def has_api_key() -> bool:
        return bool(os.getenv("ZAI_API_KEY"))
    
    def get_rate_limit_config(self) -> Dict:
        return {"requests_per_minute": 60, "tokens_per_minute": 100000, "max_retries": 3, "timeout_seconds": 60}
    
    def _get_client(self) -> ZaiClient:
        # Z.AI documentation specifies this base URL for API/PAAS
        return ZaiClient(api_key=os.getenv("ZAI_API_KEY"), base_url="https://api.z.ai/api/paas/v4/")
    
    async def get_models(self) -> List[Dict]:
        if not self.has_api_key(): return []
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.z.ai/api/paas/v4/models",
                    headers={"Authorization": f"Bearer {os.getenv('ZAI_API_KEY')}"}
                )
                data = response.json().get("data", [])
                
                models = []
                for m in data:
                    capabilities = []
                    if "asr" in m["id"] or "transcribe" in m["id"]:
                        capabilities.append("stt")
                    elif "tts" in m["id"]:
                        capabilities.append("tts")
                    else:
                        capabilities.append("text_chat")
                    
                    models.append({
                        "id": m["id"],
                        "name": m.get("id"),
                        "capabilities": capabilities
                    })
                return models
        except Exception as e:
            print(f"Error fetching Z.AI models: {e}")
            return []

    async def get_models_by_category(self, category: str) -> List[Dict[str, str]]:
        all_models = await self.get_models()
        return [{"id": m["id"], "name": m["name"]} for m in all_models if category in m.get("capabilities", [])]
    
    async def stt(self, audio_data: bytes, model: str) -> str:
        client = self._get_client()
        # Official Z.AI transcription expects a file object
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "rb") as f:
                # Z.AI transcription: client.audio.transcriptions.create
                transcript = client.audio.transcriptions.create(
                    model=model,
                    file=f
                )
            return transcript.text
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def tts(self, text: str, model: str) -> bytes:
        raise NotImplementedError("Z.AI provider does not support TTS.")

    @asynccontextmanager
    async def connect_live_stt(self, model: str, audio_stream: Optional[AsyncIterator[bytes]] = None):
        raise NotImplementedError("Z.AI realtime STT not integrated.")

    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        await limiter.wait_if_needed()
        
        client = self._get_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    
    async def chat_streaming(self, messages: List[Dict[str, str]], model: str):
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        await limiter.wait_if_needed()
        
        client = self._get_client()
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
