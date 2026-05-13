from typing import List, Dict, Optional, AsyncIterator
from contextlib import asynccontextmanager
from app.repositories.ai_settings import AISettingsRepository
from app.services.ai import get_available_providers, get_provider, PROVIDERS

class AIService:
    def __init__(self):
        self.repo = AISettingsRepository()
        
    async def initialize(self):
        await self.repo.initialize()
    
    async def get_available_providers(self) -> List[Dict]:
        """Get list of providers that have API keys configured"""
        providers = get_available_providers()
        return [
            {"id": name, "name": provider.display_name}
            for name, provider in providers.items()
        ]
    
    async def get_models(self, provider: str) -> List[Dict[str, str]]:
        """Get list of models for a specific provider"""
        try:
            p = get_provider(provider)
            return await p.get_models()
        except Exception as e:
            print(f"Error getting models for {provider}: {e}")
            return []
    
    async def get_models_grouped(self, provider: str, category: str = None) -> Dict:
        """Get models grouped by category for a specific provider"""
        try:
            p = get_provider(provider)
            
            if category:
                # Use the new provider-specific categorization
                models = await p.get_models_by_category(category)
            else:
                models = await p.get_models()
                
            # Formatting for the frontend
            grouped = {}
            for m in models:
                # Use provided category if it exists, otherwise default to other
                cat = m.get("category", "other")
                if cat not in grouped:
                    grouped[cat] = {
                        "category": cat,
                        "display_name": m.get("category_display", cat.replace("_", " ").title()),
                        "icon": m.get("category_icon", "📄"),
                        "models": []
                    }
                grouped[cat]["models"].append(m)
            
            return {"grouped": list(grouped.values()), "flat": models}
        except Exception as e:
            print(f"Error getting grouped models for {provider}: {e}")
            return {"grouped": [], "flat": []}
    
    async def get_user_settings(self, user_id: int) -> Optional[Dict]:
        """Get user's AI settings"""
        return await self.repo.get_by_user(user_id)
    
    async def save_user_settings(self, user_id: int, provider: str, model: str,
                              stt_provider: str = "browser", stt_model: str = "Browser Built In", stt_mode: str = "batch",
                              tts_provider: str = "browser", tts_model: str = "Browser Built In"):
        """Save user's AI settings"""
        return await self.repo.upsert(user_id, provider, model, stt_provider, stt_model, stt_mode, tts_provider, tts_model)

    async def transcribe_audio(self, user_id: int, audio_data: bytes) -> str:
        """Transcribe audio using configured STT provider"""
        settings = await self.repo.get_by_user(user_id)
        if not settings or settings.get("stt_provider", "browser") == "browser":
            raise Exception("No external STT provider configured")
        
        provider_name = settings["stt_provider"]
        model = settings["stt_model"]
        
        provider = get_provider(provider_name)
        return await provider.stt(audio_data, model)

    async def transcribe_audio_batch(self, user_id: int, audio_data: bytes) -> str:
        """Transcribe audio using batch processing (Record-and-Upload)"""
        settings = await self.repo.get_by_user(user_id)
        if not settings or settings.get("stt_provider", "browser") == "browser":
            raise Exception("No external STT provider configured for batch")

        provider_name = settings["stt_provider"]
        model = settings["stt_model"]

        provider = get_provider(provider_name)
        return await provider.stt(audio_data, model)

    async def text_to_speech(self, user_id: int, text: str) -> bytes:
        """Convert text to speech using configured TTS provider"""
        settings = await self.repo.get_by_user(user_id)
        if not settings or settings.get("tts_provider", "browser") == "browser":
            raise Exception("No external TTS provider configured")
        
        provider_name = settings["tts_provider"]
        model = settings["tts_model"]
        
        provider = get_provider(provider_name)
        return await provider.tts(text, model)

    @asynccontextmanager
    async def connect_live_stt(self, user_id: int, audio_stream: Optional[AsyncIterator[bytes]] = None):
        """Connect to the configured STT provider's live session"""
        settings = await self.repo.get_by_user(user_id)
        if not settings or settings.get("stt_provider", "browser") == "browser":
            raise Exception("No external STT provider configured for live streaming")

        provider_name = settings["stt_provider"]
        model = settings["stt_model"]

        provider = get_provider(provider_name)

        if provider_name == "mistral":
            async with provider.connect_live_stt(model, audio_stream) as session:
                yield session
        else:
            # We assume streaming/live STT only uses providers that support Live API
            config = {
                "response_modalities": ["TEXT"],
                "transcribe_input": True
            }
            async with provider.connect_live(model, config) as session:
                yield session

    async def generate_title(self, user_id: int, username: str, message: str) -> str:
        """Generate a short title for a chat based on the first message"""
        prompt = [
            {"role": "system", "content": "Generate a very short, concise title (max 3-4 words) for a chat conversation based on the user's first message. Respond ONLY with the title text, no quotes or periods."},
            {"role": "user", "content": f"Message: {message}"}
        ]
        
        try:
            # We use the user's configured provider/model for title generation too
            response = await self.send_message(user_id, username, 0, prompt)
            if "content" in response:
                return response["content"].strip()
            return "Untitled Chat"
        except Exception as e:
            print(f"Error generating title: {e}")
            return "Untitled Chat"
    
    async def send_message(self, user_id: int, username: str, session_id: int, messages: List[Dict[str, str]]) -> Dict:
        """Send message to AI and return response"""
        # Get user's settings
        settings = await self.repo.get_by_user(user_id)
        if not settings:
            return {"error": "Please configure your AI settings first"}
        
        provider_name = settings["provider"]
        model = settings["model"]
        base_system_prompt = settings.get("system_prompt", "You are a helpful assistant.")
        
        # Inject user identity into system prompt
        personalized_system_prompt = f"The user you are assisting is named {username}. {base_system_prompt}"
        
        # Check if we already have a system message in the thread
        thread = messages.copy()
        if not any(m["role"] == "system" for m in thread):
            thread.insert(0, {"role": "system", "content": personalized_system_prompt})
        else:
            # Update existing system prompt if it exists
            for m in thread:
                if m["role"] == "system":
                    m["content"] = f"The user you are assisting is named {username}. {m['content']}"
        
        try:
            provider = get_provider(provider_name)
            response = await provider.chat(thread, model)
            return {"content": response, "provider": provider_name, "model": model}
        except Exception as e:
            return {"error": str(e)}
    
    async def send_message_streaming(self, user_id: int, username: str, session_id: int, messages: List[Dict[str, str]]):
        """Send message to AI with streaming response"""
        settings = await self.repo.get_by_user(user_id)
        if not settings:
            raise Exception("Please configure your AI settings first")
        
        provider_name = settings["provider"]
        model = settings["model"]
        base_system_prompt = settings.get("system_prompt", "You are a helpful assistant.")
        
        # Inject user identity
        personalized_system_prompt = f"The user you are assisting is named {username}. {base_system_prompt}"
        
        thread = messages.copy()
        if not any(m["role"] == "system" for m in thread):
            thread.insert(0, {"role": "system", "content": personalized_system_prompt})
        else:
            for m in thread:
                if m["role"] == "system":
                    m["content"] = f"The user you are assisting is named {username}. {m['content']}"
        
        provider = get_provider(provider_name)
        async for chunk in provider.chat_streaming(thread, model):
            yield chunk