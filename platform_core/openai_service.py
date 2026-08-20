from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

from platform_core.config import ROOT_DIR
from platform_core.logging_service import LOGGER

@dataclass(frozen=True)
class ModelConfig:
    default_model: str
    vision_model: str

def _streamlit_secret(name: str, default: str = "") -> str:
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        return str(value or default)
    except Exception:
        return default

class OpenAIService:
    def __init__(self):
        self._client = None
        self._client_key_fingerprint = None

    def refresh_environment(self) -> None:
        # Always load the platform-root file, regardless of the current
        # working directory or how Streamlit was launched.
        load_dotenv(ROOT_DIR / ".env", override=False)

    def _value(self, name: str, default: str = "") -> str:
        self.refresh_environment()
        value = str(os.getenv(name, "") or "").strip()
        if value:
            return value
        secret_value = _streamlit_secret(name, default).strip()
        return secret_value or default

    @property
    def api_key(self) -> str:
        return self._value("OPENAI_API_KEY")

    @property
    def models(self) -> ModelConfig:
        return ModelConfig(
            default_model=self._value("OPENAI_MODEL", "gpt-5"),
            vision_model=self._value(
                "OPENAI_VISION_MODEL",
                "gpt-4.1-mini",
            ),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def client(self):
        key = self.api_key
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured in the runtime environment or local .env file."
            )

        fingerprint = key[-8:]
        if (
            self._client is None
            or self._client_key_fingerprint != fingerprint
        ):
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "The openai package is not installed. "
                    "Run pip install -r requirements.txt."
                ) from exc
            self._client = OpenAI(api_key=key)
            self._client_key_fingerprint = fingerprint
        return self._client

    def text_response(
        self,
        *,
        instructions: str,
        input_text: str,
        model: str | None = None,
    ) -> str:
        selected_model = model or self.models.default_model
        LOGGER.info(
            "OpenAI text request using model %s",
            selected_model,
        )
        response = self.client().responses.create(
            model=selected_model,
            instructions=instructions,
            input=input_text,
        )
        return response.output_text

    def health(self) -> dict[str, Any]:
        self.refresh_environment()
        env_path = ROOT_DIR / ".env"
        return {
            "configured": self.configured,
            "runtime_env_present": bool(str(os.getenv("OPENAI_API_KEY", "") or "").strip()),
            "streamlit_secret_present": bool(_streamlit_secret("OPENAI_API_KEY", "").strip()),
            "env_path": str(env_path),
            "env_file_exists": env_path.exists(),
            "default_model": self.models.default_model,
            "vision_model": self.models.vision_model,
            "client_initialized": self._client is not None,
        }

OPENAI = OpenAIService()
