import os
from config.config_loader import load_config, get_config, refresh_config


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv('PROVIDER', raising=False)
    monkeypatch.delenv('DISTANCE_THRESHOLD', raising=False)
    cfg = load_config({})
    assert cfg.provider.name == 'dummy'
    assert 0 < cfg.search.distance_threshold <= 1
    assert cfg.embedding.timeout == 30.0


def test_provider_validation(monkeypatch):
    bad_env = {'PROVIDER': 'invalid'}
    try:
        load_config(bad_env)
        assert False, 'Expected ValueError for invalid provider'
    except ValueError as e:
        assert 'Invalid PROVIDER' in str(e)


def test_distance_threshold_parsing(monkeypatch):
    cfg = load_config({'DISTANCE_THRESHOLD': '0.42'})
    assert abs(cfg.search.distance_threshold - 0.42) < 1e-9
    # invalid value fallback
    cfg2 = load_config({'DISTANCE_THRESHOLD': 'not-a-number'})
    assert abs(cfg2.search.distance_threshold - 0.5) < 1e-9


def test_singleton_and_refresh(monkeypatch):
    # Ensure singleton caches
    os.environ['DISTANCE_THRESHOLD'] = '0.33'
    c1 = get_config()
    assert abs(c1.search.distance_threshold - 0.33) < 1e-9
    # Change env, still cached
    os.environ['DISTANCE_THRESHOLD'] = '0.44'
    c2 = get_config()
    assert c1 is c2
    assert abs(c2.search.distance_threshold - 0.33) < 1e-9
    # Refresh should pick up new value
    c3 = refresh_config()
    assert abs(c3.search.distance_threshold - 0.44) < 1e-9
    assert c3 is get_config()


def test_safe_dict_masks(monkeypatch):
    cfg = load_config({'POSTGRES_PASSWORD': 'secret', 'OPENAI_API_KEY': 'sk-xxx'})
    safe = cfg.to_safe_dict()
    assert safe['database']['password'] == '***'
    assert safe['provider']['openai_api_key'] == '***'
