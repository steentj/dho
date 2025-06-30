"""
Tests for enhanced configuration validation in book_processor_wrapper.py
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add the src directory to the path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from create_embeddings.book_processor_wrapper import validate_config


@pytest.mark.unit
class TestConfigurationValidation:
    """Test the enhanced configuration validation functionality."""

    def test_validate_config_all_valid_openai(self):
        """Test validation with all valid OpenAI configuration."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass',
            'POSTGRES_DB': 'testdb',
            'PROVIDER': 'openai',
            'OPENAI_API_KEY': 'sk-test123',
            'CHUNKING_STRATEGY': 'sentence_splitter',
            'CHUNK_SIZE': '500',
            'LOG_LEVEL': 'INFO'
        }):
            config = validate_config()
            assert config['provider'] == 'openai'
            assert config['chunking_strategy'] == 'sentence_splitter'
            assert config['chunk_size'] == 500
            assert config['log_level'] == 'INFO'

    def test_validate_config_all_valid_ollama(self):
        """Test validation with all valid Ollama configuration."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'postgres',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'password',
            'POSTGRES_DB': 'dhodb',
            'PROVIDER': 'ollama',
            'OLLAMA_BASE_URL': 'http://localhost:11434',
            'OLLAMA_MODEL': 'nomic-embed-text',
            'CHUNKING_STRATEGY': 'word_overlap',
            'CHUNK_SIZE': '400'
        }):
            config = validate_config()
            assert config['provider'] == 'ollama'
            assert config['chunking_strategy'] == 'word_overlap'
            assert config['chunk_size'] == 400
            assert config['log_level'] is None

    def test_validate_config_dummy_provider(self):
        """Test validation with dummy provider (minimal requirements)."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy',
            'CHUNKING_STRATEGY': 'sentence_splitter',
            'CHUNK_SIZE': '300'
        }):
            config = validate_config()
            assert config['provider'] == 'dummy'
            assert config['chunking_strategy'] == 'sentence_splitter'
            assert config['chunk_size'] == 300

    def test_validate_config_missing_postgres_host(self):
        """Test validation fails when POSTGRES_HOST is missing."""
        with patch.dict(os.environ, {
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy'
        }, clear=True):
            with pytest.raises(ValueError, match="Manglende påkrævede miljøvariabler.*POSTGRES_HOST"):
                validate_config()

    def test_validate_config_missing_openai_key(self):
        """Test validation fails when OpenAI provider lacks API key."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'openai'
        }, clear=True):
            with pytest.raises(ValueError, match="Manglende påkrævede miljøvariabler.*OPENAI_API_KEY"):
                validate_config()

    def test_validate_config_missing_ollama_config(self):
        """Test validation fails when Ollama provider lacks required config."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'ollama'
        }, clear=True):
            with pytest.raises(ValueError, match="Manglende påkrævede miljøvariabler.*OLLAMA_BASE_URL.*OLLAMA_MODEL"):
                validate_config()

    def test_validate_config_invalid_provider(self):
        """Test validation fails with invalid provider."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'invalid_provider'
        }, clear=True):
            with pytest.raises(ValueError, match="Ukendt PROVIDER.*invalid_provider.*Skal være en af: openai, ollama, dummy"):
                validate_config()

    def test_validate_config_invalid_chunking_strategy(self):
        """Test validation fails with invalid chunking strategy."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy',
            'CHUNKING_STRATEGY': 'invalid_strategy'
        }, clear=True):
            with pytest.raises(ValueError, match=r"Ugyldig CHUNKING_STRATEGY.*invalid_strategy.*Skal være en af: \['sentence_splitter', 'word_overlap'\]"):
                validate_config()

    def test_validate_config_invalid_chunk_size_non_numeric(self):
        """Test validation fails with non-numeric chunk size."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy',
            'CHUNK_SIZE': 'not_a_number'
        }, clear=True):
            with pytest.raises(ValueError, match="CHUNK_SIZE skal være et tal, ikke 'not_a_number'"):
                validate_config()

    def test_validate_config_invalid_chunk_size_negative(self):
        """Test validation fails with negative chunk size."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy',
            'CHUNK_SIZE': '-100'
        }, clear=True):
            with pytest.raises(ValueError, match="CHUNK_SIZE skal være et positivt tal"):
                validate_config()

    def test_validate_config_invalid_chunk_size_zero(self):
        """Test validation fails with zero chunk size."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy',
            'CHUNK_SIZE': '0'
        }, clear=True):
            with pytest.raises(ValueError, match="CHUNK_SIZE skal være et positivt tal"):
                validate_config()

    def test_validate_config_invalid_log_level(self):
        """Test validation fails with invalid log level."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy',
            'LOG_LEVEL': 'INVALID'
        }, clear=True):
            with pytest.raises(ValueError, match="Ugyldig LOG_LEVEL.*INVALID.*Skal være en af: \\['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'\\]"):
                validate_config()

    def test_validate_config_defaults(self):
        """Test validation with default values."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy'  # Use dummy provider to avoid need for Ollama config
        }, clear=True):
            config = validate_config()
            # Test defaults
            assert config['provider'] == 'dummy'  # Explicitly set to dummy
            assert config['chunking_strategy'] == 'sentence_splitter'  # Default strategy
            assert config['chunk_size'] == 500  # Default chunk size
            assert config['log_level'] is None  # No LOG_LEVEL set

    def test_validate_config_default_provider_ollama_requires_config(self):
        """Test that default provider (ollama) requires Ollama configuration."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test'
            # No PROVIDER set, so default is 'ollama'
        }, clear=True):
            with pytest.raises(ValueError, match="Manglende påkrævede miljøvariabler.*OLLAMA_BASE_URL.*OLLAMA_MODEL"):
                validate_config()

    def test_validate_config_case_insensitive_log_level(self):
        """Test that log level validation is case insensitive."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy',
            'LOG_LEVEL': 'debug'  # lowercase
        }, clear=True):
            config = validate_config()
            assert config['log_level'] == 'debug'

    def test_validate_config_all_valid_log_levels(self):
        """Test all valid log levels are accepted."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        for level in valid_levels:
            with patch.dict(os.environ, {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_USER': 'test',
                'POSTGRES_PASSWORD': 'test',
                'POSTGRES_DB': 'test',
                'PROVIDER': 'dummy',
                'LOG_LEVEL': level
            }, clear=True):
                config = validate_config()
                assert config['log_level'] == level

    def test_validate_config_multiple_missing_vars(self):
        """Test validation properly reports multiple missing variables."""
        with patch.dict(os.environ, {
            'PROVIDER': 'openai'
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_config()
            
            error_msg = str(exc_info.value)
            assert "Manglende påkrævede miljøvariabler" in error_msg
            assert "POSTGRES_HOST" in error_msg
            assert "POSTGRES_USER" in error_msg
            assert "POSTGRES_PASSWORD" in error_msg
            assert "POSTGRES_DB" in error_msg
            assert "OPENAI_API_KEY" in error_msg

    def test_validate_config_return_structure(self):
        """Test that validate_config returns the expected structure."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'dummy',
            'CHUNKING_STRATEGY': 'sentence_splitter',
            'CHUNK_SIZE': '500',
            'LOG_LEVEL': 'INFO'
        }, clear=True):
            config = validate_config()
            
            # Check all expected keys are present
            expected_keys = ['provider', 'chunking_strategy', 'chunk_size', 'log_level', 'required_vars_present']
            assert all(key in config for key in expected_keys)
            
            # Check types
            assert isinstance(config['provider'], str)
            assert isinstance(config['chunking_strategy'], str)
            assert isinstance(config['chunk_size'], int)
            assert isinstance(config['required_vars_present'], int)
            # log_level can be None or str
            assert config['log_level'] is None or isinstance(config['log_level'], str)

    def test_validate_config_ollama_missing_only_model(self):
        """Test validation fails when only OLLAMA_MODEL is missing."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'ollama',
            'OLLAMA_BASE_URL': 'http://localhost:11434'
        }, clear=True):
            with pytest.raises(ValueError, match="Manglende påkrævede miljøvariabler.*OLLAMA_MODEL"):
                validate_config()

    def test_validate_config_ollama_missing_only_url(self):
        """Test validation fails when only OLLAMA_BASE_URL is missing."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'test',
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'test',
            'PROVIDER': 'ollama',
            'OLLAMA_MODEL': 'nomic-embed-text'
        }, clear=True):
            with pytest.raises(ValueError, match="Manglende påkrævede miljøvariabler.*OLLAMA_BASE_URL"):
                validate_config()
