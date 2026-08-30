import os
import logging
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class UnifiedLLMProvider:
    """
    Unified LLM interface supporting local models (Ollama) and cloud providers.
    Includes mock fallback when local server is offline or in testing mode.
    """

    def __init__(self, provider: str = "ollama", model_name: str = "llama3.2", temperature: float = 0.7):
        self.provider = provider.lower()
        self.model_name = model_name
        self.temperature = temperature

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes generation request against configured model provider.
        """
        if self.provider == "ollama":
            return self._call_ollama(prompt, system_prompt)
        elif self.provider in ["mock", "test"]:
            return self._call_mock(prompt)
        else:
            # Fallback to mock if provider is unknown or unconfigured cloud provider
            logger.warning(f"Provider '{self.provider}' falling back to mock response handler.")
            return self._call_mock(prompt)

    def _call_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature}
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "")
                    prompt_eval_count = data.get("prompt_eval_count", 0)
                    eval_count = data.get("eval_count", 0)
                    return {
                        "text": response_text,
                        "input_tokens": prompt_eval_count,
                        "output_tokens": eval_count,
                        "total_tokens": prompt_eval_count + eval_count,
                        "provider": "ollama",
                        "model": self.model_name
                    }
                else:
                    logger.warning(f"Ollama returned status {resp.status_code}. Falling back to mock handler.")
                    return self._call_mock(prompt, reason=f"Ollama HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Failed to connect to Ollama at {url}: {e}. Falling back to mock handler.")
            return self._call_mock(prompt, reason=f"Ollama connection exception: {str(e)}")

    def _call_mock(self, prompt: str, reason: str = "Mock execution") -> Dict[str, Any]:
        simulated_text = (
            f"[Jarvis Agent Runtime - Execution Result ({reason})]\n"
            f"Processed request using model '{self.model_name}' (provider: {self.provider}).\n"
            f"Task analysis completed successfully."
        )
        return {
            "text": simulated_text,
            "input_tokens": len(prompt) // 4,
            "output_tokens": len(simulated_text) // 4,
            "total_tokens": (len(prompt) + len(simulated_text)) // 4,
            "provider": self.provider,
            "model": self.model_name
        }
