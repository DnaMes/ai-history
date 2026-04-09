import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import LLMConfig, LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    # Gemini CLI OAuth credentials location
    GEMINI_CLI_CREDS_PATH = Path.home() / ".gemini" / "oauth_creds.json"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
        self._cache_dir = Path(
            config.cache_dir or Path.home() / ".ai-history" / "llm_cache"
        )
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # Default Gemini CLI OAuth client credentials (public, safe to embed)
    # These are from the official Gemini CLI and are intentionally public.
    # Users can override via environment variables if needed.
    DEFAULT_GEMINI_CLIENT_ID = (
        "REDACTED_GEMINI_CLIENT_ID"
    )
    DEFAULT_GEMINI_CLIENT_SECRET = "REDACTED_GEMINI_CLIENT_SECRET"

    def _load_gemini_cli_creds(self) -> Optional[Dict[str, str]]:
        """Load OAuth credentials from Gemini CLI installation.

        Note: Gemini CLI OAuth tokens have Cloud Platform scopes, not Generative Language API scopes.
        This means they won't work directly with the Gemini API. You'll need either:
        1. An API key from https://aistudio.google.com/app/apikey (recommended)
        2. Or use Vertex AI with a Google Cloud project
        """
        try:
            if self.GEMINI_CLI_CREDS_PATH.exists():
                with open(self.GEMINI_CLI_CREDS_PATH, "r") as f:
                    creds = json.load(f)
                    # Use environment variables if set, otherwise use defaults
                    client_id = os.environ.get(
                        "GEMINI_CLI_CLIENT_ID", self.DEFAULT_GEMINI_CLIENT_ID
                    )
                    client_secret = os.environ.get(
                        "GEMINI_CLI_CLIENT_SECRET", self.DEFAULT_GEMINI_CLIENT_SECRET
                    )
                    return {
                        "refresh_token": creds.get("refresh_token"),
                        "client_id": client_id,
                        "client_secret": client_secret,
                    }
        except Exception:
            pass
        return None

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            import google.generativeai as genai

            # Method 1: API Key (highest priority if provided)
            api_key = self.config.api_key
            if not api_key:
                api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get(
                    "GOOGLE_API_KEY"
                )

            if api_key:
                genai.configure(api_key=api_key)
                self._client = genai
                return self._client

            # Method 2: OAuth2 credentials from config
            client_id = self.config.oauth_client_id or os.environ.get(
                "GOOGLE_CLIENT_ID"
            )
            client_secret = self.config.oauth_client_secret or os.environ.get(
                "GOOGLE_CLIENT_SECRET"
            )
            refresh_token = self.config.oauth_refresh_token or os.environ.get(
                "GOOGLE_REFRESH_TOKEN"
            )

            # Method 2b: Try Gemini CLI credentials
            if not (client_id and client_secret and refresh_token):
                gemini_creds = self._load_gemini_cli_creds()
                if gemini_creds:
                    client_id = client_id or gemini_creds["client_id"]
                    client_secret = client_secret or gemini_creds["client_secret"]
                    refresh_token = refresh_token or gemini_creds["refresh_token"]

            if client_id and client_secret and refresh_token:
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials

                credentials = Credentials(
                    token=None,
                    refresh_token=refresh_token,
                    client_id=client_id,
                    client_secret=client_secret,
                    token_uri="https://oauth2.googleapis.com/token",
                )

                # Refresh the token
                credentials.refresh(Request())

                genai.configure(credentials=credentials)
                self._client = genai
                return self._client

            # Method 3: Application Default Credentials (ADC)
            if self.config.use_adc or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                import google.auth

                credentials, project = google.auth.default()
                genai.configure(credentials=credentials)
                self._client = genai
                return self._client

            # No valid authentication found
            raise ValueError(
                "Gemini authentication not found. Use one of:\n"
                "  1. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable\n"
                "  2. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN for OAuth\n"
                "  3. Login with Gemini CLI (creates ~/.gemini/oauth_creds.json)\n"
                "  4. Run 'gcloud auth application-default login' and set use_adc=True\n"
                "  5. Pass credentials in config"
            )

        except ImportError as e:
            raise ImportError(
                f"Required package not installed: {e}. Install with: pip install google-generativeai google-auth"
            )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        cache_key = None
        if self.config.cache_enabled:
            cache_key = self._get_cache_key(prompt, system_prompt)
            cached = self._load_from_cache(cache_key)
            if cached:
                return cached

        client = self._get_client()

        model = client.GenerativeModel(
            self.config.model,
            system_instruction=system_prompt if system_prompt else None,
        )

        generation_config = client.types.GenerationConfig(
            max_output_tokens=max_tokens or self.config.max_tokens,
            temperature=(
                temperature if temperature is not None else self.config.temperature
            ),
        )

        response = model.generate_content(prompt, generation_config=generation_config)

        content = response.text

        result = LLMResponse(
            content=content,
            model=self.config.model,
            tokens_used=(
                response.usage_metadata.total_token_count
                if hasattr(response, "usage_metadata")
                else 0
            ),
            cached=False,
        )

        if self.config.cache_enabled and cache_key:
            self._save_to_cache(cache_key, result)

        return result

    def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
    ) -> List[LLMResponse]:
        return [self.generate(p, system_prompt) for p in prompts]

    def is_available(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "gemini",
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

    def _get_cache_key(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        combined = f"{system_prompt or ''}|{prompt}|{self.config.model}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[LLMResponse]:
        cache_file = self._cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                return LLMResponse(
                    content=data["content"],
                    model=data["model"],
                    tokens_used=data.get("tokens_used", 0),
                    cached=True,
                )
            except Exception:
                pass
        return None

    def _save_to_cache(self, cache_key: str, response: LLMResponse):
        cache_file = self._cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "content": response.content,
                        "model": response.model,
                        "tokens_used": response.tokens_used,
                    },
                    f,
                )
        except Exception:
            pass
