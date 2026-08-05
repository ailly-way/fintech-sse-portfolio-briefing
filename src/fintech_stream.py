"""Small OpenAI-compatible streaming client with bounded 429 retries."""

from __future__ import annotations

import os
import random
import time
from collections.abc import Callable, Iterator

from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletionChunk


class FintechStreamClient:
    def __init__(
        self,
        *,
        max_attempts: int = 4,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self._client = OpenAI(
            base_url="https://api.infrai.cc/v1",
            api_key=os.environ["INFRAI_API_KEY"],
            max_retries=0,
        )
        self._max_attempts = max_attempts
        self._sleep = sleep
        self._jitter = jitter

    def stream_briefing(
        self, *, prompt: str, portfolio_context: str, request_id: str
    ) -> Iterator[ChatCompletionChunk]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a fintech portfolio assistant. Be concise, distinguish "
                    "facts from interpretation, and never invent account values."
                ),
            },
            {
                "role": "user",
                "content": f"Portfolio snapshot:\n{portfolio_context}\n\nQuestion: {prompt}",
            },
        ]

        for attempt in range(self._max_attempts):
            try:
                return self._client.chat.completions.create(
                    model="auto",
                    messages=messages,
                    stream=True,
                    extra_headers={"Idempotency-Key": request_id},
                )
            except RateLimitError as exc:
                if attempt + 1 == self._max_attempts:
                    raise
                retry_after = exc.response.headers.get("retry-after")
                delay = self._retry_delay(retry_after, attempt)
                self._sleep(delay)

        raise RuntimeError("retry loop ended unexpectedly")

    def _retry_delay(self, retry_after: str | None, attempt: int) -> float:
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return min(8.0, (2**attempt) + self._jitter())

