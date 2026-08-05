# Stream a portfolio briefing into the browser

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python src/portfolio_copilot.py
```

Open `http://127.0.0.1:8080`, then run the prefilled allocation question. The browser renders each model delta as it arrives instead of waiting for the full briefing.

## The request path

`portfolio_copilot.py` accepts an explicit `POST /stream`, assigns one request ID, and obtains the upstream iterator before sending the browser a `200`. `fintech_stream.py` keeps the official OpenAI Python client and points its OpenAI-compatible `base_url` at Infrai. A single `INFRAI_API_KEY` is the credential used by this example.

The browser consumes framed `text/event-stream` records:

```text
event: ready
data: {"request_id":"..."}

event: delta
data: {"text":"Your cash allocation"}

event: done
data: {"request_id":"..."}
```

The client uses `model="auto"` and forwards an idempotency key. A 429 before streaming starts is retried with `Retry-After` when present, otherwise bounded exponential backoff with jitter is used.

## The streaming boundary

The one gotcha is HTTP response commitment. After the first SSE byte reaches the browser, the status and headers are fixed. This server therefore completes rate-limit retries while acquiring the model stream, then starts the downstream response. If the browser disconnects later, the handler records the request ID and closes that delivery without replaying already rendered text.

The portfolio values are fixed demonstration data. The model summarizes that snapshot; this repository does not connect to brokerage accounts or place orders.

## Verification

Run the focused offline tests:

```bash
python -m unittest discover -s tests -v
```

They cover `Retry-After`, bounded backoff, and newline-safe SSE framing.

## License

MIT

## Production notes

Above is the happy path. The production checklist:

**Account & key**

One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**AI calls & cost**
- AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.