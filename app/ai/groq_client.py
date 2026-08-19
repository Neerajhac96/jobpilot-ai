import os
import time
from pathlib import Path

from app.config import settings
from groq import Groq
import groq

class GroqClient:

    def __init__(self):
        api_key = settings.GROQ_API_KEY

        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured.")

        self.client = Groq(api_key=api_key)
        self.model = settings.GROQ_MODEL

    def generate(
        self,
        prompt: str,
        json_mode: bool = False
    ) -> str:

        request = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise AI assistant. "
                        "Follow the requested output format exactly."
                        + (" Ensure the output is valid JSON." if json_mode else "")
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_completion_tokens": 2048
        }

        if json_mode:
            request["response_format"] = {
                "type": "json_object"
            }

        max_retries = 3
        base_wait = 2

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    **request
                )
                
                content = response.choices[0].message.content

                if content is None or not content.strip():
                    raise ValueError(
                        "Groq returned an empty response."
                    )

                return content.strip()
                
            except groq.RateLimitError as e:
                if attempt == max_retries:
                    raise e
                time.sleep(base_wait * attempt)
            except (groq.APIConnectionError, groq.InternalServerError) as e:
                if attempt == max_retries:
                    raise e
                time.sleep(base_wait * attempt)
