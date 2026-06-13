# 9router

Hermes Ultimate uses 9router as the single OpenAI-compatible LLM gateway for Hermes and Decepticon services.

## URLs

- Local UI/API: http://localhost:20128
- Container API base URL: http://9router:20128/v1
- Host API base URL: http://localhost:20128/v1

## Login

- User: `admin`
- Password: value of `NINEROUTER_INITIAL_PASSWORD` from `stack/.env`

## Add A Provider

1. Start the stack with `docker compose -f stack/docker-compose.yml up -d 9router`.
2. Open http://localhost:20128 and sign in.
3. Add an OpenAI-compatible provider in the 9router UI.
4. Copy the generated API key into `NINEROUTER_API_KEY` for Hermes and local tooling.
