from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, TypeVar

from core.config import GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL, REASONING_EFFORT


T = TypeVar("T")


class LLMClient:
    # Initializes the LLM client with API credentials, model settings, and logging directory
    def __init__(
        self,
        run_dir: Path,
        api_key: str | None = GEMINI_API_KEY,
        base_url: str = GEMINI_BASE_URL,
        model: str = GEMINI_MODEL,
        reasoning_effort: str = REASONING_EFFORT,
    ) -> None:
        self.run_dir = run_dir
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.log_dir = run_dir / "llm"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    # Sends a prompt to the LLM and parses the JSON response using the provided schema and parser
    def complete_json(
        self,
        *,
        call_name: str,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        json_schema: dict[str, Any],
        parser: Callable[[dict[str, Any]], T],
    ) -> T:
        if not self.api_key:
            raise RuntimeError(
                "No LLM API key found. Set GEMINI_API_KEY, OPENAI_API_KEY, or LLM_API_KEY before running LLM stages."
            )

        last_error: Exception | None = None
        prompt = user_prompt
        for attempt in range(1, 3):
            payload = self._payload(
                system_prompt=system_prompt,
                user_prompt=prompt,
                schema_name=schema_name,
                json_schema=json_schema,
            )
            self._write_json(f"{call_name}_request_attempt_{attempt}.json", self._redacted_payload(payload))
            raw_response = self._post_json(payload)
            self._write_text(f"{call_name}_response_attempt_{attempt}.json", raw_response)

            try:
                content = self._extract_content(raw_response)
                parsed_json = json.loads(content)
                return parser(parsed_json)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                prompt = (
                    f"{user_prompt}\n\n"
                    "Your previous response was invalid because "
                    f"{exc}. Return only valid JSON matching the schema."
                )

        raise RuntimeError(f"LLM output for {call_name} was invalid after one retry: {last_error}")

    # Builds the API request payload with system/user prompts and JSON schema for structured output
    def _payload(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema,
                },
            },
        }

    # Sends a POST request to the LLM API and returns the raw response
    def _post_json(self, payload: dict[str, Any]) -> str:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API HTTP {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM API request failed: {exc}") from exc

    # Extracts the content field from the LLM API response JSON
    def _extract_content(self, raw_response: str) -> str:
        response_json = json.loads(raw_response)
        return response_json["choices"][0]["message"]["content"]

    # Logs JSON data to a file in the LLM log directory
    def _write_json(self, filename: str, data: dict[str, Any]) -> None:
        self._write_text(filename, json.dumps(data, indent=2))

    # Logs text data to a file in the LLM log directory
    def _write_text(self, filename: str, text: str) -> None:
        path = self.log_dir / filename
        path.write_text(text, encoding="utf-8")

    # Returns a copy of the payload with the API key redacted for safe logging
    def _redacted_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        redacted = json.loads(json.dumps(payload))
        redacted["logged_at_unix"] = time.time()
        redacted["api_key"] = "<redacted>"
        return redacted
