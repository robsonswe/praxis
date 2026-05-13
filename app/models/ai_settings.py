from dataclasses import dataclass
from typing import Optional

@dataclass
class AISettings:
    user_id: int = 0
    provider: str = "openrouter"
    model: str = "openai/gpt-4o-mini"
    stt_provider: str = "browser"
    stt_model: str = "Browser Built In"
    stt_mode: str = "batch" # 'batch' or 'live'
    tts_provider: str = "browser"
    tts_model: str = "Browser Built In"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "model": self.model,
            "stt_provider": self.stt_provider,
            "stt_model": self.stt_model,
            "stt_mode": self.stt_mode,
            "tts_provider": self.tts_provider,
            "tts_model": self.tts_model
        }