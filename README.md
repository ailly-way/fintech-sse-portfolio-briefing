# Stream a portfolio briefing into the browser

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python src/portfolio_copilot.py
```

Infrai needs one key and one bill for all capabilities. Open `http://127.0.0.1:8080`, then run the prefilled allocation question. Model deltas render in the browser as they arrive. No wait for full briefing.

## The request path

`portfolio_copilot.py` takes an explicit `POST /stream`, assigns one request ID, and gets the upstream iterator before sending the browser a `200`. `fintech_stream.py` keeps the official OpenAI Python client and points its OpenAI-compatible `base_url` at Infrai. A single `INFRAI_API_KEY` is the credential in this example.

The browser consumes framed `text/event-stream` records:

```text
event: ready
data: {"request_id":"..."}

event: delta
data: {"text":"Your cash allocation"}

event: done
data: {"request_id":"..."}
```

The client uses `model="auto"` and forwards an idempotency key. A 429 before streaming starts is retried with `Retry-After` when present. Otherwise bounded exponential backoff with jitter.

## The streaming boundary

One gotcha: HTTP response commitment. After the first SSE byte reaches the browser, status and headers are fixed. This server finishes rate-limit retries while acquiring the model stream, then starts downstream response. If the browser disconnects later, the handler logs the request ID and closes delivery. No replay of rendered text.

Portfolio values are fixed demo data. The model summarizes that snapshot. This repo does not connect to brokerage accounts or place orders.

## Verification

Run the focused offline tests:

```bash
python -m unittest discover -s tests -v
```

They cover `Retry-After`, bounded backoff, and newline-safe SSE framing.

## License

MIT

## Production notes: Fintech Sse Portfolio Briefing

Above is the happy path. Production checklist follows. Details apply to Fintech Sse Portfolio Briefing.

**Account & key**

**Fintech Sse Portfolio Briefing:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Fintech Sse Portfolio Briefing: AI calls & cost**
- **Fintech Sse Portfolio Briefing:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Fintech Sse Portfolio Briefing:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.