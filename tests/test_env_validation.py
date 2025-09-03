from pathlib import Path

from scripts.validate_env import validate_env_file

BASE = Path(__file__).parent.parent


def write_temp_env(tmp_path, content: str, name: str = '.env') -> Path:
    p = tmp_path / name
    p.write_text(content, encoding='utf-8')
    return p


def test_success_local_ollama(tmp_path):
    env_content = """
ENVIRONMENT=local
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev
POSTGRES_PORT=5432
POSTGRES_DB=dhodb
PROVIDER=ollama
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=400
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
""".strip()
    env_path = write_temp_env(tmp_path, env_content)
    result = validate_env_file(env_path)
    assert result['status'] == 'ok', result
    assert not result['errors']


def test_missing_required_variable(tmp_path):
    env_content = """
ENVIRONMENT=local
POSTGRES_HOST=localhost
# POSTGRES_USER missing
POSTGRES_PASSWORD=dev
POSTGRES_PORT=5432
POSTGRES_DB=dhodb
PROVIDER=dummy
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=400
""".strip()
    env_path = write_temp_env(tmp_path, env_content)
    result = validate_env_file(env_path)
    assert result['status'] == 'fail'
    messages = [e['message'] for e in result['errors']]
    assert any('POSTGRES_USER' in m for m in messages)


def test_production_rejects_dummy_provider(tmp_path):
    env_content = """
ENVIRONMENT=production
POSTGRES_HOST=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=prod
POSTGRES_PORT=5432
POSTGRES_DB=dhodb
PROVIDER=dummy
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=400
""".strip()
    env_path = write_temp_env(tmp_path, env_content)
    result = validate_env_file(env_path)
    assert result['status'] == 'fail'
    assert any('Production environment cannot use PROVIDER=dummy' in e['message'] for e in result['errors'])


def test_test_env_requires_dummy(tmp_path):
    env_content = """
ENVIRONMENT=test
POSTGRES_HOST=localhost
POSTGRES_USER=test
POSTGRES_PASSWORD=test
POSTGRES_PORT=5432
POSTGRES_DB=test_db
PROVIDER=ollama
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=400
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
""".strip()
    env_path = write_temp_env(tmp_path, env_content)
    result = validate_env_file(env_path)
    assert result['status'] == 'fail'
    assert any('Test environment must use PROVIDER=dummy' in e['message'] for e in result['errors'])


def test_transitional_root_env_missing_environment(tmp_path):
    # Simulate legacy root .env missing ENVIRONMENT
    env_content = """
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev
POSTGRES_PORT=5432
POSTGRES_DB=dhodb
PROVIDER=dummy
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=400
""".strip()
    env_path = write_temp_env(tmp_path, env_content)  # name .env
    # Ensure name is .env to trigger transitional path
    result = validate_env_file(env_path)
    # Should pass (ok) but have a warning about assumed environment
    assert result['status'] == 'ok'
    warn_msgs = [w['message'] for w in result['warnings']]
    assert any('transitional fallback' in m for m in warn_msgs)
    assert result.get('assumed_environment') == 'local'


def test_openai_local_requires_key(tmp_path):
    env_content = """
ENVIRONMENT=local
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev
POSTGRES_PORT=5432
POSTGRES_DB=dhodb
PROVIDER=openai
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=400
# Missing OPENAI_API_KEY
""".strip()
    env_path = write_temp_env(tmp_path, env_content)
    result = validate_env_file(env_path)
    assert result['status'] == 'fail'
    assert any('OPENAI_API_KEY' in e['message'] for e in result['errors'])


def test_placeholder_in_production_fails(tmp_path):
    env_content = """
ENVIRONMENT=production
POSTGRES_HOST=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=REPLACE_WITH_SECURE_PASSWORD
POSTGRES_PORT=5432
POSTGRES_DB=dhodb
PROVIDER=ollama
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=400
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=nomic-embed-text
""".strip()
    env_path = write_temp_env(tmp_path, env_content)
    result = validate_env_file(env_path)
    assert result['status'] == 'fail'
    assert any('Placeholder value still present' in e['message'] for e in result['errors'])
