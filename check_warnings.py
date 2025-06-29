#!/usr/bin/env python3
"""
Script to check for warnings from dependencies.
"""

import warnings
import sys

# Capture all warnings
warnings.filterwarnings("default")

print("Checking for warnings from imports...")

try:
    # Import main dependencies that might generate warnings
    import asyncio
    print("✓ asyncio imported")
    
    import openai
    print("✓ openai imported")
    
    import httpx
    print("✓ httpx imported")
    
    import pymupdf
    print("✓ pymupdf imported")
    
    import psycopg2
    print("✓ psycopg2 imported")
    
    import asyncpg
    print("✓ asyncpg imported")
    
    import langchain_text_splitters
    print("✓ langchain_text_splitters imported")
    
    import tqdm
    print("✓ tqdm imported")
    
    # Try importing our own modules
    sys.path.append('/Users/steen/Library/Mobile Documents/com~apple~CloudDocs/Projekter/SlægtBib/src')
    
    from create_embeddings.providers.embedding_providers import OpenAIEmbeddingProvider, OllamaEmbeddingProvider
    print("✓ embedding providers imported")
    
    from database.postgresql_service import PostgreSQLService
    print("✓ postgresql service imported")
    
    print("\n✓ All imports completed successfully!")
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Other error: {e}")

print("\nIf there were any warnings, they would have appeared above.")
