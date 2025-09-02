# Environment Files

This directory holds environment-specific configuration files introduced in Stage 1 of the multi-environment rollout.

Files:
- `local.env`       : Local development (often Ollama provider, debug-friendly)
- `test.env`        : Test/CI environment (dummy provider, isolation)
- `production.env`  : Production deployment (OpenAI or Ollama, hardened)

Each file MUST contain an `ENVIRONMENT=` key with one of: `local`, `test`, `production`.

At this stage the application still uses the root `.env` file. A later stage will add an `env_switch` script and validation.

Do NOT place secrets in version-controlled copies intended for public or shared repos. Replace sensitive values with placeholders (e.g., `REPLACE_ME`).

Last Updated: 2025-09-02
