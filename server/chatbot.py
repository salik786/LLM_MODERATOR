from __future__ import annotations
import os, time
from typing import Optional, Callable, Any
from dotenv import load_dotenv
load_dotenv()

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False

class _LocalReply:
    def __init__(self, content: str): self.content = content

class Chatbot:
    def __init__(self, system_prompt: str, model_name=None, temperature=None, max_tokens=None):
        self.system_prompt = system_prompt.strip()
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(temperature or os.getenv("OPENAI_TEMP", "0.3"))
        self.max_tokens = int(max_tokens or os.getenv("OPENAI_MAX_TOKENS", "1500"))
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
        self._use_openai = _OPENAI_AVAILABLE and bool(os.getenv("OPENAI_API_KEY"))
        self.client = OpenAI() if self._use_openai else None
        self._max_prompt_chars = int(os.getenv("CHATBOT_MAX_PROMPT_CHARS", "12000"))

    def _retry(self, fn: Callable[[], Any]):
        delay = 0.8
        for attempt in range(1, self.max_retries + 1):
            try: return fn()
            except Exception as e:
                if attempt == self.max_retries: raise e
                time.sleep(delay); delay *= 1.7

    def _truncate(self, text: str) -> str:
        if len(text) <= self._max_prompt_chars: return text
        half = self._max_prompt_chars // 2
        return text[:half] + "\n...\n" + text[-half:]

    def send_message(self, prompt: str, thread_id: Optional[str] = None):
        if not self._use_openai:
            return _LocalReply(f"(Fallback) Auto-reply: {prompt[:200]}")
        user_prompt = self._truncate(prompt)
        def _call():
            resp = self.client.chat.completions.create(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content
        try:
            return _LocalReply(self._retry(_call))
        except Exception as e:
            return _LocalReply(f"(Error Fallback) {str(e)[:150]}")
