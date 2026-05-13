import os
import base64
from typing import List, Dict, AsyncIterator
from contextlib import asynccontextmanager
from mistralai.client import Mistral
from .base import AIProvider, get_rate_limiter

class MistralProvider(AIProvider):
    @property
    def name(self) -> str:
        return "mistral"
    
    @property
    def display_name(self) -> str:
        return "Mistral AI"
    
    @staticmethod
    def has_api_key() -> bool:
        return bool(os.getenv("MISTRAL_API_KEY"))
    
    def get_rate_limit_config(self) -> Dict:
        return {
            "requests_per_minute": 60,
            "tokens_per_minute": 100000,
            "max_retries": 3,
            "timeout_seconds": 60
        }
    
    def _get_client(self) -> Mistral:
        return Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    
    async def get_models(self) -> List[Dict]:
        if not self.has_api_key():
            return []
            
        try:
            client = self._get_client()
            # Fetch models with specific modalities to discover audio/speech capable models
            response = await client.models.list_async()
            
            models = []
            for m in response.data:
                # Filter/Detect based on name for now if architecture isn't consistently exposed
                # as the current SDK might abstract it.
                capabilities = []
                if "voxtral" in m.id:
                    if "transcribe" in m.id: capabilities.append("stt")
                    if "tts" in m.id: capabilities.append("tts")
                else:
                    capabilities.append("text_chat")
                
                models.append({
                    "id": m.id,
                    "name": m.id,
                    "capabilities": capabilities
                })
            return models
        except Exception as e:
            print(f"Error fetching Mistral models: {e}")
            return []

    async def get_models_by_category(self, category: str) -> List[Dict[str, str]]:
        all_models = await self.get_models()
        return [{"id": m["id"], "name": m["name"]} for m in all_models if category in m.get("capabilities", [])]

    async def stt(self, audio_data: bytes, model: str) -> str:
        client = self._get_client()
        # Create a temp file for the SDK to read
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            # Mistral SDK expects a file tuple: (filename, file_object)
            with open(tmp_path, "rb") as f:
                response = client.audio.transcriptions.complete(
                    model=model,
                    file={
                        "file_name": "recording.wav",
                        "content": f,
                    }
                )
            return response.text
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def tts(self, text: str, model: str) -> bytes:
        client = self._get_client()
        
        # Fetch available voices to pick a valid one
        voices = client.audio.voices.list()
        if not voices.items:
            raise Exception("No voices found for Mistral TTS. Please create a voice via the Mistral Voice API.")
        
        # Use the first available voice_id
        voice_id = voices.items[0].id
        
        # Official Mistral speech generation returns audio_data in the response
        response = client.audio.speech.complete(
            model=model,
            input=text,
            voice_id=voice_id,
            response_format="mp3"
        )
        return base64.b64decode(response.audio_data)

    @asynccontextmanager
    async def connect_live_stt(self, model: str, audio_stream: AsyncIterator[bytes]):
        """Mistral realtime transcription stream."""
        client = self._get_client()
        from mistralai.client.models import AudioFormat
        
        audio_format = AudioFormat(encoding="pcm_s16le", sample_rate=16000)
        
        # The SDK returns the stream directly from transcribe_stream
        stream = client.audio.realtime.transcribe_stream(
            audio_stream=audio_stream,
            model=model,
            audio_format=audio_format,
        )
        yield stream

    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        await limiter.wait_if_needed()
        
        client = self._get_client()
        response = await client.chat.complete_async(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    
    async def chat_streaming(self, messages: List[Dict[str, str]], model: str):
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        await limiter.wait_if_needed()
        
        client = self._get_client()
        stream = await client.chat.stream_async(
            model=model,
            messages=messages
        )
        async for chunk in stream:
            if chunk.data.choices[0].delta.content:
                yield chunk.data.choices[0].delta.content
