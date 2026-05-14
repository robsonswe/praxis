import os
import io
import wave
import asyncio
import httpx
import json
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from gtts import gTTS
from .base import AIProvider, get_rate_limiter
from .models import ModelInfo, ModelCategory, categorize_model


class GeminiProvider(AIProvider):
    _cached_models: Optional[List[ModelInfo]] = None
    
    @property
    def name(self) -> str:
        return "gemini"
    
    @property
    def display_name(self) -> str:
        return "Google Gemini"
    
    @staticmethod
    def has_api_key() -> bool:
        return bool(os.getenv("GOOGLE_API_KEY"))
    
    def get_rate_limit_config(self) -> Dict:
        return {
            "requests_per_minute": 60,
            "tokens_per_minute": 100000,
            "max_retries": 3,
            "timeout_seconds": 60
        }
    
    def _get_client(self, model: str = None) -> genai.Client:
        """Get Gemini client with appropriate API version"""
        api_version = "v1"
        if model:
            m_lower = model.lower()
            # Most live/multimodal features and system_instruction require v1alpha
            if any(x in m_lower for x in ["preview", "alpha", "exp", "live", "audio", "2025", "2.0", "2.5"]):
                api_version = "v1alpha"
            
        return genai.Client(
            api_key=os.getenv("GOOGLE_API_KEY"),
            http_options={'api_version': api_version}
        )

    async def _fetch_all_models_raw(self) -> List[Dict]:
        """Fetch raw model data from API with full metadata"""
        if not self.has_api_key():
            return []
        
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        await limiter.wait_if_needed()
        
        try:
            # We use v1alpha for listing to see all preview/experimental models
            client = self._get_client("preview")
            raw_models = []
            
            async for m in await client.aio.models.list():
                raw_models.append({
                    "name": m.name,
                    "display_name": getattr(m, "display_name", None),
                    "description": getattr(m, "description", None),
                    "supported_actions": getattr(m, "supported_actions", []),
                    "input_token_limit": getattr(m, "input_token_limit", None),
                    "output_token_limit": getattr(m, "output_token_limit", None),
                })
            
            return raw_models
        except Exception as e:
            print(f"Error fetching Gemini models: {e}")
            return []
    
    def _convert_to_model_info(self, raw_model: Dict) -> Optional[ModelInfo]:
        """Convert raw model data to ModelInfo with category"""
        name = raw_model.get("name", "")
        if not name:
            return None
        
        if not (name.startswith("models/gemini") or name.startswith("models/gemma") or 
                name.startswith("models/imagen") or name.startswith("models/veo")):
            return None
        
        model_id = name.replace("models/", "")
        capabilities = raw_model.get("supported_actions", [])
        
        if not capabilities:
            capabilities = []
        
        supports_streaming = "generateContentStream" in capabilities
        # Check if the model ID itself suggests thinking capability if metadata is missing
        supports_thinking = "thinking" in model_id.lower() or raw_model.get("thinking", False)
        
        category = categorize_model(model_id, capabilities)
        
        return ModelInfo(
            id=model_id,
            name=raw_model.get("display_name") or model_id,
            description=raw_model.get("description"),
            category=category,
            capabilities=capabilities,
            input_tokens=raw_model.get("input_token_limit"),
            output_tokens=raw_model.get("output_token_limit"),
            supports_streaming=supports_streaming,
            supports_thinking=supports_thinking,
        )
    
    async def get_all_models(self) -> List[ModelInfo]:
        """Fetch ALL models with full metadata and categories"""
        if self._cached_models is not None:
            return self._cached_models
        
        raw_models = await self._fetch_all_models_raw()
        self._cached_models = [
            self._convert_to_model_info(m) 
            for m in raw_models
        ]
        self._cached_models = [m for m in self._cached_models if m is not None]
        
        return self._cached_models
    
    async def get_models(self) -> List[Dict[str, str]]:
        """Get models in legacy format for backward compatibility"""
        models = await self.get_all_models()
        return [
            {
                "id": m.id,
                "name": m.name,
                "category": m.category.value if m.category else None,
                "category_display": m.category.display_name if m.category else None,
                "category_icon": m.category.icon if m.category else "📄",
            }
            for m in models
        ]
    
    async def get_models_by_category(self, category: str) -> List[Dict[str, str]]:
        """Strict capability-based model categorization"""
        all_models = await self.get_all_models()
        self.clear_cache()
        
        filtered = []
        for m in all_models:
            m_id = m.id.lower()
            supports_gen = "generateContent" in m.capabilities
            supports_bidi = "bidiGenerateContent" in m.capabilities
            
            # Identify visual and robotics modality models
            is_visual = any(x in m_id for x in ["image", "video", "veo", "imagen", "banana"])
            is_robotics = "robotics" in m_id
            
            # Text Chat
            if category == "text_chat":
                if supports_gen and any(x in m_id for x in ["gemini", "gemma"]) and not is_visual and not is_robotics and "-tts" not in m_id:
                    filtered.append(m)
            
            elif category == "stt":
                is_stt_capable = supports_gen or supports_bidi
                if is_stt_capable and not is_visual and not is_robotics and "-tts" not in m_id:
                    filtered.append(m)
            
            elif category == "tts":
                if supports_gen and not is_visual and not is_robotics and any(x in m_id for x in ["tts", "audio", "live", "native-audio"]):
                    filtered.append(m)
                    
        return [
            {
                "id": m.id,
                "name": m.name,
                "category": m.category.value if m.category else None,
                "category_display": m.category.display_name if m.category else None,
                "category_icon": m.category.icon if m.category else "📄",
            }
            for m in filtered
        ]
    
    async def get_models_by_category_legacy(self, category: ModelCategory) -> List[ModelInfo]:
        """Filter models by category - abstraction for the app"""
        all_models = await self.get_all_models()
        return [m for m in all_models if m.category == category]
    
    async def get_models_with_capability(self, capability: str) -> List[ModelInfo]:
        """Filter models by capability (e.g., 'generateContent', 'embedContent')"""
        all_models = await self.get_all_models()
        return [m for m in all_models if capability in m.capabilities]
    
    def clear_cache(self):
        """Clear cached models - useful when API key changes"""
        self._cached_models = None
    
    def _convert_messages_to_contents(self, messages: List[Dict[str, str]]) -> List[types.Content]:
        """Convert OpenAI-style messages to Gemini contents format"""
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))
        return contents
    
    def _format_error(self, e: Exception) -> str:
        error_str = str(e)
        
        if "Cannot find field" in error_str:
            return "AI Provider Error: The SDK failed to parse the model response. This usually happens with 'thinking' models if the SDK is not the latest version. Try a non-thinking model or update dependencies."
            
        try:
            if "{'error':" in error_str:
                import ast
                start = error_str.find("{'error':")
                error_dict_str = error_str[start:]
                error_data = ast.literal_eval(error_dict_str)
                if 'error' in error_data and 'message' in error_data['error']:
                    return error_data['error']['message']
        except:
            pass
            
        if "503 UNAVAILABLE" in error_str:
            return "The model is currently overloaded. Please try again in a moment."
        if "429" in error_str or "QUOTA_EXCEEDED" in error_str:
            return "Rate limit exceeded. Please wait before sending more messages."
            
        return error_str

    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            raise Exception("Google API key not configured")
        
        await limiter.wait_if_needed()
        
        # We switch to the OpenAI-compatible endpoint to bypass SDK Protobuf decoding issues
        # especially common with "thinking" models or newer API fields.
        api_key = os.getenv("GOOGLE_API_KEY")
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                    },
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    # Try to parse error message from JSON
                    try:
                        err_data = response.json()
                        if "error" in err_data:
                            raise Exception(err_data["error"].get("message", response.text))
                    except:
                        pass
                    raise Exception(f"Gemini API Error ({response.status_code}): {response.text}")
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            except httpx.TimeoutException:
                raise Exception("The request to Gemini timed out. Try a smaller prompt or a faster model.")
            except Exception as e:
                raise Exception(self._format_error(e))
    
    async def chat_streaming(self, messages: List[Dict[str, str]], model: str):
        limiter = get_rate_limiter(self.name, self.get_rate_limit_config()["requests_per_minute"])
        
        if not self.has_api_key():
            raise Exception("Google API key not configured")
        
        await limiter.wait_if_needed()
        
        try:
            client = self._get_client(model)
            
            system_instruction = None
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                    break
            
            contents = self._convert_messages_to_contents([m for m in messages if m["role"] != "system"])
            
            async for chunk in await client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction
                ) if system_instruction else None
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"Error: {self._format_error(e)}"

    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def connect_live(self, model: str, config: Dict):
        """Connect to Gemini Multimodal Live API using proven patterns"""
        if not self.has_api_key():
            raise Exception("Google API key not configured")
        
        client = self._get_client(model)
        
        # Proven configuration from gemini_live.py
        live_config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                turn_coverage="TURN_INCLUDES_ONLY_ACTIVITY",
            )
        )
        
        print(f"DEBUG: Attempting connection to {model} with proven config")
        try:
            async with client.aio.live.connect(model=model, config=live_config) as session:
                print(f"DEBUG: Live session connected for {model}")
                yield session
        except Exception as e:
            print(f"DEBUG: Live session connection failed: {e}")
            raise e

    async def stt(self, audio_data: bytes, model: str) -> str:
        if not self.has_api_key():
            raise Exception("Google API key not configured")
        
        client = self._get_client(model)
        
        # Gemini handles audio as part of generate_content
        # We'll use a prompt to just transcribe
        prompt = "Transcribe this audio. Respond ONLY with the transcription text."
        
        response = await client.aio.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=audio_data, mime_type="audio/wav"),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ]
        )
        return response.text.strip()

    async def tts(self, text: str, model: str) -> bytes:
        if not self.has_api_key():
            raise Exception("Google API key not configured")
        
        # If it's a newer model (2.0+) or specifically marked as tts/audio, try native multimodal
        is_native_supported = any(x in model.lower() for x in ["2.0", "3.1", "2.5", "tts", "audio"])
        
        if is_native_supported:
            try:
                client = self._get_client(model)
                
                # We use a specific prompt to ensure the model behaves like a TTS engine
                # instead of a conversational assistant.
                prompt = f"Read the following text exactly as written, with no changes, preamble, or commentary: {text}"
                
                config = types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Puck" # High-fidelity energetic voice
                            )
                        )
                    )
                )
                
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                
                audio_part = response.candidates[0].content.parts[0]
                if audio_part.inline_data:
                    pcm_data = audio_part.inline_data.data
                    
                    # Wrap PCM in WAV header (Gemini native is 24kHz, 16-bit, Mono)
                    with io.BytesIO() as wav_io:
                        with wave.open(wav_io, 'wb') as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2) # 16-bit
                            wf.setframerate(24000)
                            wf.writeframes(pcm_data)
                        return wav_io.getvalue()
            except Exception as e:
                print(f"Native Gemini TTS failed, falling back to gTTS: {e}")
        
        # Fallback to gTTS (Google Text-to-Speech)
        def _generate_gtts():
            tts = gTTS(text=text, lang='en')
            with io.BytesIO() as f:
                tts.write_to_fp(f)
                return f.getvalue()
        
        return await asyncio.to_thread(_generate_gtts)
