# Overview

LLM Debate is a research project that investigates whether debating with more persuasive LLMs leads to more truthful answers. The system enables LLM-vs-LLM debates where models argue for correct vs incorrect answers to questions from the QuALITY dataset, with both human and AI judges evaluating the debates. The project includes functionality for running various debate protocols (blind baselines, consultancy, debate, interactive debate) and analyzing their effectiveness at surfacing truthful information.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **FastAPI-based REST API** serving as the main backend server
- **SQLAlchemy ORM** with PostgreSQL database for data persistence
- **Alembic** for database migrations and schema management
- **Modular agent system** with separate debater and judge classes that can be configured for different LLM models
- **Asynchronous processing** using Python's asyncio for handling concurrent debate sessions and API calls

## Frontend Architecture
- **React with TypeScript** for the web interface
- **Tailwind CSS** for styling and responsive design
- **Vite** as the build tool and development server
- **React Router** for client-side routing
- **Component-based architecture** with reusable UI components for debates, transcripts, and judgments

## LLM Integration
- **Multi-provider support** for OpenAI (GPT models) and Anthropic (Claude models) APIs
- **Rate limiting and retry logic** to handle API constraints gracefully
- **Configurable model parameters** (temperature, max tokens, etc.) via YAML configuration files
- **Token counting and cost tracking** for budget management
- **Preference model integration** for ranking multiple candidate responses (Best-of-N sampling)

## Debate System Design
- **Rollout-based architecture** supporting sequential and simultaneous debate formats
- **Transcript management** with structured Round objects containing debater arguments
- **Judge evaluation system** supporting both human and AI judges with confidence scoring
- **Cross-examination capabilities** allowing judges to ask follow-up questions during debates
- **Experiment framework** for running controlled studies with different debate configurations

## Data Management
- **QuALITY dataset integration** for sourcing questions and correct/incorrect answer pairs
- **CSV import/export functionality** for processing experimental results
- **Caching system** for storing intermediate results during long-running experiments
- **File-based configuration** using YAML for experiment parameters and model settings

## Quality Assurance
- **Parsing and validation** for debate transcripts with error handling for malformed data
- **Scoring and accuracy calculation** with support for various evaluation metrics
- **Tournament system** for pitting different model configurations against each other
- **Human experiment infrastructure** for collecting judgments from human participants

# External Dependencies

## Core LLM APIs
- **OpenAI API** (GPT-3.5, GPT-4 models) for debate participants and judges
- **Anthropic API** (Claude models) as alternative LLM provider
- **API key management** through environment variables and secrets file

## Database & Storage
- **PostgreSQL** for persistent data storage of debates, judgments, and user data
- **SQLAlchemy** as the database ORM layer
- **Alembic** for database schema migrations

## Data Processing
- **Pandas** for data manipulation and CSV processing
- **Datasets library** for accessing the QuALITY dataset
- **TikToken** for accurate token counting across different models

## Web Framework & Utilities
- **FastAPI** as the web framework with automatic API documentation
- **Uvicorn** as the ASGI server for running the FastAPI application
- **Pydantic** for data validation and serialization (v1.x for compatibility)
- **Hydra** for hierarchical configuration management

## Development & Analysis
- **Pre-commit hooks** for code quality enforcement
- **Matplotlib/Seaborn** for generating visualizations and plots
- **Weights & Biases (wandb)** for experiment tracking and logging
- **TrueSkill** for tournament rating calculations
