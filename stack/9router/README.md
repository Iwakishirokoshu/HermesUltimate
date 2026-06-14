# 9router

Hermes Ultimate uses 9router as the single OpenAI-compatible LLM gateway for Hermes and Decepticon services.

## URLs

- Local UI/API: http://localhost:20128
- Container API base URL: http://9router:20128/v1
- Host API base URL: http://localhost:20128/v1
- Hermes env base URL: `NINEROUTER_BASE_URL=http://localhost:20128/v1`

## Access

- The Hermes stack binds 9router to `127.0.0.1:20128` on the host.
- Password login is disabled by `scripts/disable-9router-auth.sh`.
- On a VPS, access it through the dashboard SSH tunnel rather than exposing port `20128` publicly.

## Add A Provider

1. Start the stack with `docker compose -f stack/docker-compose.yml up -d 9router`.
2. Run `scripts/disable-9router-auth.sh` once the container is running.
3. Open http://localhost:20128.
4. Add an OpenAI-compatible provider in the 9router UI.
5. Copy the generated API key into `NINEROUTER_API_KEY` for Hermes and local tooling.
6. Keep `NINEROUTER_BASE_URL` pointed at the OpenAI-compatible `/v1` URL.
