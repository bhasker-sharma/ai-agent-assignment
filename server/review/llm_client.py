import json

from openai import OpenAI

from server.config import settings


class LlmClient:
    """One chat model behind the OpenAI SDK. Gemini is reached through its OpenAI-compatible endpoint."""

    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __init__(self) -> None:
        if settings.llm_provider == "openai":
            api_key, base_url = settings.openai_api_key, None
        elif settings.llm_provider == "gemini":
            api_key, base_url = settings.gemini_api_key, self.GEMINI_BASE_URL
        else:
            raise ValueError("LLM_PROVIDER must be 'openai' or 'gemini'. Set it in .env.")
        if not api_key or not settings.llm_model:
            raise ValueError(f"Set LLM_MODEL and the API key for {settings.llm_provider} in .env.")

        self.model = settings.llm_model
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def ask_json(self, messages: list[dict[str, str]]) -> dict:
        """Sends the conversation and returns the reply parsed as a JSON object."""
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "")
