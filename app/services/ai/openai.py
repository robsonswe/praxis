import os
from typing import List, Dict
from openai import AsyncOpenAI
from .base import AIProvider, get_rate_limiter

class OpenAIProvider(AIProvider):
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def display_name(self) -> str:
        return "OpenAI"
    
    @staticmethod
    def has_api_key() -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))
    
    def get_rate_limit_config(self) -> Dict:
        return {
            "requests_per_minute": 500,  # OpenAI has higher limits
            "tokens_per_minute": 150000,
            "max_retries": 3,
            "timeout_seconds": 60
        }
    
    async def get_models(self) -> List[Dict[str, str]]:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            return []
        
        await limiter.wait_if_needed()
        
        try:
            client = AsyncOpenAI()
            response = await client.models.list()
            models = []
            for m in response.data:
                # Basic name/id list for legacy compatibility
                models.append({
                    "id": m.id,
                    "name": m.id
                })
            return models
        except Exception as e:
            print(f"Error fetching OpenAI models: {e}")
            return []

    async def get_models_by_category(self, category: str) -> List[Dict[str, str]]:
        all_models = await self.get_models()
        
        filtered = []
        for m in all_models:
            m_id = m.id.lower()
            
            if category == "text_chat":
                if m_id.startswith("gpt-") or m_id.startswith("o"):
                    filtered.append(m)
            elif category == "stt":
                if "whisper" in m_id:
                    filtered.append(m)
            elif category == "tts":
                if "tts-" in m_id:
                    filtered.append(m)
                    
        return filtered
    
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            raise Exception("OpenAI API key not configured")
        
        await limiter.wait_if_needed()
        
        try:
            client = AsyncOpenAI()
            response = await client.chat.completions.create(
                model=model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def chat_streaming(self, messages: List[Dict[str, str]], model: str):
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            raise Exception("OpenAI API key not configured")
        
        await limiter.wait_if_needed()
        
        client = AsyncOpenAI()
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def stt(self, audio_data: bytes, model: str) -> str:
        if not self.has_api_key():
            raise Exception("OpenAI API key not configured")
        
        # Temporary file for Whisper (it requires a file-like object with a name)
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            client = AsyncOpenAI()
            with open(tmp_path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model=model, 
                    file=audio_file
                )
            return transcript.text
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def tts(self, text: str, model: str) -> bytes:
        if not self.has_api_key():
            raise Exception("OpenAI API key not configured")
        
        client = AsyncOpenAI()
        response = await client.audio.speech.create(
            model=model,
            voice="alloy", # Default voice
            input=text
        )
        return response.content