#!/usr/bin/env python3
"""
Diagnostic script to verify import paths and dependencies for embedding providers.
This script is used as part of the test process to ensure the environment is correctly set up.
"""

import sys
import importlib.util
from pathlib import Path


def try_import(module_name):
    """Try to import a module and print success/failure message."""
    try:
        module = __import__(module_name, fromlist=['*'])
        print(f"✅ Successfully imported {module_name}")
        return module
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return None


def check_module_exists(module_name):
    """Check if a module exists without importing it."""
    return importlib.util.find_spec(module_name) is not None


def main():
    """Run diagnostics on imports and dependencies."""
    # Add the parent directory to the path to ensure create_embeddings can be found
    create_embeddings_path = Path(__file__).parent / "create_embeddings"
    sys.path.insert(0, str(create_embeddings_path))

    # Check if the directory exists
    print(f"Checking path: {create_embeddings_path}")
    print(f"Path exists: {create_embeddings_path.exists()}")

    # Check if the providers directory exists
    providers_path = create_embeddings_path / "providers"
    print(f"Providers path: {providers_path}")
    print(f"Providers path exists: {providers_path.exists()}")

    # Check for __init__.py files
    init_path = providers_path / "__init__.py"
    print(f"__init__.py exists in providers: {init_path.exists()}")

    # List files in the providers directory
    if providers_path.exists():
        print("\nFiles in providers directory:")
        for file in providers_path.glob("*.py"):
            print(f"  - {file.name}")

    # Try to import the modules
    print("\nImport attempts:")
    
    try_import("create_embeddings")
    providers_module = try_import("create_embeddings.providers")

    # Try to directly import the provider classes
    if providers_module:
        try:
            # Use a temporary import to check if all classes are available
            import create_embeddings.providers  # pylint: disable=import-outside-toplevel
            
            provider_classes = [
                "EmbeddingProvider",
                "OpenAIEmbeddingProvider",
                "OllamaEmbeddingProvider", 
                "DummyEmbeddingProvider",
                "EmbeddingProviderFactory"
            ]
            
            all_found = all(hasattr(create_embeddings.providers, cls) for cls in provider_classes)
            
            if all_found:
                print("✅ Successfully imported all provider classes")
            else:
                print("❌ Some provider classes are missing")
                
            has_ollama = hasattr(providers_module, '__all__') and 'OllamaEmbeddingProvider' in providers_module.__all__
            print(f"OllamaEmbeddingProvider in __all__: {has_ollama}")
        except ImportError as e:
            print(f"❌ Failed to import provider classes: {e}")

    # Check for OpenAI
    try:
        import openai  # pylint: disable=import-outside-toplevel
        print(f"✅ OpenAI module version: {openai.__version__}")
        
        # Check if AsyncOpenAI is available without storing it
        has_async = hasattr(openai, 'AsyncOpenAI')
        if has_async:
            print("✅ AsyncOpenAI class is available")
        else:
            print("❌ AsyncOpenAI class is not available")
            
    except ImportError as e:
        print(f"❌ OpenAI module not available: {e}")
    except AttributeError as e:
        print(f"❌ Issue with OpenAI module: {e}")

    # Check for httpx
    try:
        import httpx  # pylint: disable=import-outside-toplevel
        print(f"✅ httpx module version: {httpx.__version__}")
    except ImportError as e:
        print(f"❌ httpx module not available: {e}")


if __name__ == "__main__":
    main()
