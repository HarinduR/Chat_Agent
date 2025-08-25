# cq_manager/chat/llm_handler.py
import os
import requests
from typing import Optional, List, Any
from pydantic import Field
from langchain.llms.base import LLM  # still supported; subclass OK (LC v0.3 notes)

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterLLM(LLM):
    api_key: str = Field(...)
    model: str = Field(default="mistralai/mistral-small-3.2-24b-instruct-2506:free")
    max_tokens: int = Field(default=200)
    temperature: float = Field(default=0.8)
    top_p: float = Field(default=0.96)
    base_url: str = Field(default=OPENROUTER_BASE)

    class Config:
        extra = "forbid"

    @property
    def _llm_type(self) -> str:
        return "openrouter"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }
            if stop:
                payload["stop"] = stop

            r = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            if r.status_code == 200:
                j = r.json()
                return j["choices"][0]["message"]["content"].strip()
            print(f"OpenRouter API Error: {r.status_code} - {r.text}")
            return "I encountered an API error. Please try again."
        except requests.exceptions.Timeout:
            return "The request timed out. Please try again."
        except requests.exceptions.RequestException as e:
            print(f"OpenRouter request error: {e}")
            return "A connection error occurred. Please try again."
        except Exception as e:
            print(f"Unexpected LLM error: {e}")
            return "I hit an unexpected error. Please try again."


class LLMHandler:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        default_model = "mistralai/mistral-small-3.2-24b-instruct-2506:free"
        self.llm = OpenRouterLLM(
            api_key=self.api_key,
            model=os.getenv("OPENROUTER_MODEL", default_model),
            max_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", "200")),
            temperature=float(os.getenv("OPENROUTER_TEMPERATURE", "0.8")),
            top_p=float(os.getenv("OPENROUTER_TOP_P", "0.96")),
        )

        self.base_url = OPENROUTER_BASE
        self.model = self.llm.model
        self.max_tokens = self.llm.max_tokens
        self.temperature = self.llm.temperature
        self.top_p = self.llm.top_p

    def generate_response(self, prompt: str) -> str:
        return self.llm._call(prompt)

    def generate_response_direct(self, prompt: str) -> str:
        # For parity with your original; uses requests directly
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }
            r = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            print(f"API Error: {r.status_code} - {r.text}")
            return "I encountered an API error. Please try again."
        except requests.exceptions.Timeout:
            return "The request timed out. Please try again."
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return "A connection error occurred. Please try again."

    def set_model(self, model_name: str):
        self.model = model_name
        self.llm.model = model_name
