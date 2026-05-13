from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class ModelCategory(Enum):
    TEXT_CHAT = "text_chat"
    TTS = "tts"
    STT = "stt"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    AUDIO_LIVE = "audio_live"
    EMBEDDINGS = "embeddings"
    ROBOTICS = "robotics"
    COMPUTER_USE = "computer_use"

    @property
    def display_name(self) -> str:
        names = {
            "text_chat": "Text / Chat",
            "tts": "Text-to-Speech",
            "stt": "Speech-to-Text",
            "image_generation": "Image Generation",
            "video_generation": "Video Generation",
            "audio_live": "Audio / Live",
            "embeddings": "Embeddings",
            "robotics": "Robotics",
            "computer_use": "Computer Use",
        }
        return names.get(self.value, self.value)

    @property
    def icon(self) -> str:
        icons = {
            "text_chat": "💬",
            "tts": "🔊",
            "stt": "🎤",
            "image_generation": "🖼️",
            "video_generation": "🎬",
            "audio_live": "🎙️",
            "embeddings": "📦",
            "robotics": "🤖",
            "computer_use": "💻",
        }
        return icons.get(self.value, "📄")

@dataclass
class ModelInfo:
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[ModelCategory] = None
    capabilities: List[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    supports_streaming: bool = False
    supports_thinking: bool = False

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if self.category else None,
            "category_display": self.category.display_name if self.category else None,
            "category_icon": self.category.icon if self.category else "📄",
            "capabilities": self.capabilities,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "supports_streaming": self.supports_streaming,
            "supports_thinking": self.supports_thinking,
        }


def categorize_model(name: str, capabilities: List[str]) -> ModelCategory:
    name_lower = name.lower()
    
    if "embedContent" in capabilities or "embed" in name_lower or "embedding" in name_lower:
        return ModelCategory.EMBEDDINGS
    
    if "imagen" in name_lower or "-image" in name_lower or "flash-image" in name_lower:
        return ModelCategory.IMAGE_GENERATION
    
    if name_lower.startswith("veo"):
        return ModelCategory.VIDEO_GENERATION
    
    if "tts" in name_lower:
        return ModelCategory.TTS
    
    # Check for STT suitability
    if "flash" in name_lower or "pro" in name_lower or "whisper" in name_lower:
        # Multimodal models that also support audio natively
        if "native-audio" in name_lower or "live" in name_lower:
            return ModelCategory.AUDIO_LIVE
        return ModelCategory.STT

    if "live" in name_lower or "native-audio" in name_lower:
        return ModelCategory.AUDIO_LIVE
    
    if "robotics" in name_lower:
        return ModelCategory.ROBOTICS
    
    if "computer-use" in name_lower:
        return ModelCategory.COMPUTER_USE
    
    return ModelCategory.TEXT_CHAT