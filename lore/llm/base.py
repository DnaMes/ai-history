from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskType(Enum):
    TITLE_GENERATION = "title_generation"
    SESSION_FORMAT = "session_format"
    STATISTICS = "statistics"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    SUMMARIZATION = "summarization"
    TAGGING = "tagging"


@dataclass
class LLMConfig:
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    cache_enabled: bool = True
    cache_dir: Optional[str] = None
    # OAuth2 credentials (alternative to api_key)
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_refresh_token: Optional[str] = None
    # Use Application Default Credentials (ADC)
    use_adc: bool = False


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    def __init__(self, config: LLMConfig):
        self.config = config
        self._cache: Dict[str, LLMResponse] = {}

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        pass

    @abstractmethod
    def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
    ) -> List[LLMResponse]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        pass

    def _get_cache_key(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        import hashlib

        combined = f"{system_prompt or ''}|{prompt}"
        return hashlib.sha256(combined.encode()).hexdigest()
