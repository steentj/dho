#!/usr/bin/env python3
"""Environment validation script (Stage 2)

Validates the active .env file (or a specified env file) against rules
per ENVIRONMENT value: local | test | production.

Usage:
    python scripts/validate_env.py              # validates ./ .env (root)
    python scripts/validate_env.py --file env/local.env
    python scripts/validate_env.py --strict     # escalate warnings to errors
    python scripts/validate_env.py --json       # machine-readable output

Exit codes:
    0 = success (no errors; warnings allowed unless --strict)
    1 = validation errors
    2 = unexpected internal failure

Transitional behavior: if the root .env lacks ENVIRONMENT, we downgrade the
error to a warning and assume ENVIRONMENT=local (to avoid breaking legacy
workflows). This can be removed in a later stage once all environments adopt
the ENVIRONMENT variable explicitly.

Future extensions: schema checks, DB connectivity, provider table coverage.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

SEVERITY_ERROR = "error"
SEVERITY_WARN = "warning"

class ValidationIssue:
    def __init__(self, message: str, severity: str):
        self.message = message
        self.severity = severity
    def to_dict(self):
        return {"message": self.message, "severity": self.severity}

REQUIRED_COMMON = [
    "POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT", "POSTGRES_DB",
    "PROVIDER", "CHUNKING_STRATEGY", "CHUNK_SIZE"
]
# Provider-specific requirements
OPENAI_REQUIRED = ["OPENAI_API_KEY"]
OLLAMA_REQUIRED = ["OLLAMA_BASE_URL", "OLLAMA_MODEL"]

ALLOWED_PROVIDERS = {"openai", "ollama", "dummy"}
ALLOWED_ENVIRONMENTS = {"local", "test", "production"}

PLACEHOLDER_TOKENS = {"REPLACE_WITH_SECURE_PASSWORD", "REPLACE_WITH_OPENAI_KEY"}


def load_env_file(path: Path) -> Dict[str, str]:
    """Load simple KEY=VALUE lines (without executing shell). Comments (#) ignored."""
    data: Dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        data[key.strip()] = value.strip()
    return data


def gather_issues(env: Dict[str,str], strict: bool) -> Tuple[List[ValidationIssue], List[ValidationIssue]]:
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    def add(msg: str, severity: str):
        (errors if severity == SEVERITY_ERROR else warnings).append(ValidationIssue(msg, severity))

    env_name = env.get("ENVIRONMENT")
    if not env_name:
        add("Missing ENVIRONMENT variable", SEVERITY_ERROR)
    elif env_name not in ALLOWED_ENVIRONMENTS:
        add(f"Invalid ENVIRONMENT value '{env_name}'", SEVERITY_ERROR)

    # Basic required
    for key in REQUIRED_COMMON:
        if not env.get(key):
            add(f"Missing required variable: {key}", SEVERITY_ERROR)

    provider = env.get("PROVIDER")
    if provider and provider not in ALLOWED_PROVIDERS:
        add(f"Invalid PROVIDER '{provider}' (allowed: {', '.join(sorted(ALLOWED_PROVIDERS))})", SEVERITY_ERROR)

    # Provider-specific checks
    if provider == "openai":
        for k in OPENAI_REQUIRED:
            if not env.get(k):
                add(f"Missing OpenAI variable: {k}", SEVERITY_ERROR)
    elif provider == "ollama":
        for k in OLLAMA_REQUIRED:
            if not env.get(k):
                add(f"Missing Ollama variable: {k}", SEVERITY_ERROR)
    elif provider == "dummy":
        # Should NOT set real provider secrets
        if env.get("OPENAI_API_KEY"):
            add("OPENAI_API_KEY present with PROVIDER=dummy (remove to avoid accidental calls)", SEVERITY_WARN)
        if env.get("OLLAMA_BASE_URL"):
            add("OLLAMA_BASE_URL present with PROVIDER=dummy (remove to keep test env minimal)", SEVERITY_WARN)

    # Environment-specific policies
    if env_name == "production":
        # Forbid dummy provider
        if provider == "dummy":
            add("Production environment cannot use PROVIDER=dummy", SEVERITY_ERROR)
        # Forbid placeholders
        for key, value in env.items():
            if value in PLACEHOLDER_TOKENS:
                add(f"Placeholder value still present for {key}", SEVERITY_ERROR)
        # Discourage DEBUG logging
        if env.get("LOG_LEVEL", "").upper() == "DEBUG":
            add("LOG_LEVEL=DEBUG in production (recommend INFO or higher)", SEVERITY_WARN)
    elif env_name == "test":
        # Enforce dummy provider unless explicitly overridden
        if provider != "dummy":
            add("Test environment must use PROVIDER=dummy", SEVERITY_ERROR)
        # Any presence of real keys is suspicious
        if env.get("OPENAI_API_KEY"):
            add("Test env should not contain OPENAI_API_KEY", SEVERITY_ERROR)
    elif env_name == "local":
        # If openai chosen but no key -> error
        if provider == "openai" and not env.get("OPENAI_API_KEY"):
            add("Local environment using PROVIDER=openai but OPENAI_API_KEY missing", SEVERITY_ERROR)
        # Warn if both provider credential sets partially present
        if env.get("OPENAI_API_KEY") and env.get("OLLAMA_BASE_URL"):
            add("Both OpenAI and Ollama settings present; consider removing unused for clarity", SEVERITY_WARN)

    # Chunking strategy sanity
    strategy = env.get("CHUNKING_STRATEGY")
    if strategy not in {"sentence_splitter", "word_overlap"}:
        add(f"Unknown CHUNKING_STRATEGY '{strategy}'", SEVERITY_ERROR)

    # Basic numeric validations
    try:
        int(env.get("CHUNK_SIZE", ""))
    except ValueError:
        add("CHUNK_SIZE is not an integer", SEVERITY_ERROR)

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate environment configuration")
    parser.add_argument('--file', '-f', help='Path to env file (default ./.env)')
    parser.add_argument('--strict', action='store_true', help='Treat warnings as errors')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args()

    env_path = Path(args.file) if args.file else Path('.env')

    try:
        env_data = load_env_file(env_path)
        errors, warnings = gather_issues(env_data, args.strict)

        # Transitional fallback: missing ENVIRONMENT in legacy root .env
        if not args.file and 'ENVIRONMENT' not in env_data:
            # Look for the specific error and downgrade if not strict
            missing_env_err = None
            for e in errors:
                if e.message == 'Missing ENVIRONMENT variable':
                    missing_env_err = e
                    break
            if missing_env_err and not args.strict:
                # Downgrade to warning
                errors.remove(missing_env_err)
                warnings.append(ValidationIssue(
                    'ENVIRONMENT missing in root .env -> assuming ENVIRONMENT=local (transitional fallback)',
                    SEVERITY_WARN
                ))
                env_data['ENVIRONMENT'] = 'local'
        exit_code = 0
        if errors:
            exit_code = 1
        elif args.strict and warnings:
            exit_code = 1

        if args.json:
            print(json.dumps({
                "file": str(env_path),
                "errors": [e.to_dict() for e in errors],
                "warnings": [w.to_dict() for w in warnings],
                "status": "ok" if exit_code == 0 else "fail"
            }, indent=2))
        else:
            print(f"Validating: {env_path}")
            if errors:
                print("Errors:")
                for e in errors:
                    print(f"  - {e.message}")
            if warnings:
                print("Warnings:")
                for w in warnings:
                    print(f"  - {w.message}")
            if not errors and not warnings:
                print("No issues detected.")
            elif not errors and warnings:
                print("Validation passed with warnings.")
        sys.exit(exit_code)
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected failure: {e}")
        sys.exit(2)

if __name__ == '__main__':
    main()
