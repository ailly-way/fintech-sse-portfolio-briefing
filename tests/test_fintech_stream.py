import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("INFRAI_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from fintech_stream import FintechStreamClient  # noqa: E402
from portfolio_copilot import encode_sse  # noqa: E402


class FintechStreamTests(unittest.TestCase):
    def test_retry_after_takes_priority(self) -> None:
        client = FintechStreamClient(sleep=lambda _: None, jitter=lambda: 0.25)
        self.assertEqual(client._retry_delay("3", attempt=0), 3.0)

    def test_exponential_delay_is_bounded(self) -> None:
        client = FintechStreamClient(sleep=lambda _: None, jitter=lambda: 0.25)
        self.assertEqual(client._retry_delay(None, attempt=0), 1.25)
        self.assertEqual(client._retry_delay(None, attempt=8), 8.0)

    def test_sse_payload_keeps_newlines_inside_json(self) -> None:
        encoded = encode_sse("delta", {"text": "cash\nposition"})
        self.assertEqual(
            encoded,
            b'event: delta\ndata: {"text":"cash\\nposition"}\n\n',
        )


if __name__ == "__main__":
    unittest.main()

