# DHO Semantic Search System

## Overview

A semantic search system for PDF files from slaegtsbibliotek.dk that uses embeddings and vector similarity to enable intelligent document retrieval.

## Core Functionality

### PDF Processing Pipeline

- Download PDF files from slaegtsbibliotek.dk
- Chunk documents into manageable segments
- Generate embeddings for text chunks
- Store embeddings in PostgreSQL with pgvector

### Semantic Search API

- Public read-only RESTful API for querying documents
- Vector similarity search using embeddings
- Return relevant document chunks with confidence scores

## Technical Architecture

### Infrastructure

- **Deployment**: Docker containers on Linux server
- **Development**: macOS environment
- **Database**: PostgreSQL with pgvector extension

### Technology Stack

- **Backend**: Python with FastAPI
- **Database**: PostgreSQL + pgvector
- **Testing**: pytest (unit and integration tests)
- **Code Quality**: PEP8 compliance via linting

### Performance Requirements

- **Expected Load**: < 500 requests per day
- **Response Time**: Reasonable (not sub-second required, but avoid minutes)
- **Authentication**: None required - public read-only interface

### Design Principles

- **Architecture**: Follow SOLID principles and GoF patterns
- **Dependency Injection**: Pluggable embedding providers, chunking mechanisms and database provider
- **Development**: Test-driven development with incremental steps
- **Quality Gate**: All tests must pass before proceeding. No linting problems found.

### Embedding Configuration

- **Default Provider**: OpenAI with text-embedding-3-small model
- **Alternative Provider**: Local Nomic Text Embed V2 model
- **Environment Configuration**: Provider and model configurable via environment variables
- **Injection Support**: Pluggable embedding providers through dependency injection
- **Provider Interface**: Standardized interface for easy provider switching

### Chunking Strategy

- **Current Implementation**: Single chunking algorithm in use
- **Extensibility**: Pluggable chunking providers through dependency injection
- **Configuration**: Chunking method selectable via environment variables
- **Provider Interface**: Standardized chunking interface for consistent behavior

### API Versioning Strategy

- **URL Versioning**: Use `/api/v1/` prefix for all endpoints
- **Version Headers**: Accept `API-Version` header for client preference
- **Backward Compatibility**: Maintain v1 support for minimum 12 months after v2 release
- **Deprecation Process**: 6-month deprecation notice via response headers and documentation
- **Version Documentation**: Separate OpenAPI specs per version

### Database Migration Strategy

- **Schema Evolution**: Handle database schema changes as system evolves
- **Data Integrity**: Ensure existing embeddings remain valid during schema updates
- **Rollback Capability**: All migrations must be reversible for safe deployments
- **Version Tracking**: Track schema version in database for migration state management
- **Production Safety**: Test all migrations on staging environment before production
- **Performance**: Large table migrations planned during maintenance windows

## Error Handling & Logging

### Embedding Process

- **Logging**: All activities logged to file
- **Transaction Safety**: Book processing follows ACID principles
- **Failure Handling**: If one book fails, continue processing remaining books
- **Progress Monitoring**: Real-time progress monitoring during embedding runs

### API Error Handling

- **HTTP Status Codes**: Use standard HTTP status codes for all responses
- **Client Responsibility**: Client must provide user-friendly error messages
- **Error Logging**: Log all errors to file with 30-day log rotation

### Log Management

- **File Logging**: All processes log to files
- **Rotation**: Automatic log file cycling after 30 days
- **Backup**: Out of scope for this project

## Development Workflow

1. Write failing test
2. Implement minimal code to pass test
3. Refactor if needed
4. Ensure all tests remain green
5. Repeat for next feature

## Development Process

### Code rules

- **Class**: One class per file

### Version Control

- **Repository**: Code versioned in GitHub
- **Branching**: Feature branches for development, merge to main
- **Commits**: Clear, descriptive commit messages following conventional commits

### Code Review

- **Single Developer Project**: Copilot used for code reviews and suggestions
- **AI-Assisted Quality**: Leverage Copilot for code quality improvements and best practices
- **Self-Review**: Manual review of Copilot suggestions before acceptance

### Environment Setup

- **Configuration**: To be addressed in future documentation
- **Local Development**: macOS environment setup guide (pending)
- **Production**: Linux server deployment instructions (pending)

### Dependency Management

- **Current**: requirements.txt with pip for package management
- **Virtual enviroment**: All development and tests must be in a python virtual environment
- **Future Migration**: Potential migration to uv and pyproject.toml
- **Lock Files**: Pin exact versions for reproducible builds
- **Security**: Regular dependency updates for security patches

## Documentation Structure

All documentation located in `/documentation/` folder:

### User Guides

- **README.md**: Project overview and quick start
- **Processing Guide**: How to download, chunk, and embed new books
- **Local Testing**: Setup and testing procedures
- **Deployment Guide**: Production deployment on Linux server
- **Language**: All documentation must be in Danish. The documentation must be short and concise, but also allow for a reader/user, who is not familiar with the tools and infrastructure used.

### Technical Documentation

- API documentation
- Database schema
- Architecture decisions