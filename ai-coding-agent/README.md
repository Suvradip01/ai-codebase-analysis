# AI Codebase Analysis Agent

An intelligent AI-powered agent for analyzing and understanding codebases. This tool uses advanced language models to provide comprehensive code analysis, documentation generation, and architectural insights.

## Features

- **Automated Code Analysis**: Analyzes entire codebases to understand structure and patterns
- **Documentation Generation**: Automatically generates comprehensive documentation
- **Architecture Insights**: Provides high-level architectural understanding
- **Schema Analysis**: Analyzes data schemas and relationships
- **Prompt Engineering**: Uses optimized prompts for accurate analysis

## Project Structure

```
ai-coding-agent/
├── agent.py          # Main agent implementation
├── core/             # Core functionality modules
├── prompts/          # Prompt templates for AI interactions
├── schemas/          # Schema definitions and analysis
├── runs/             # Analysis run outputs
├── requirements.txt  # Python dependencies
└── .env             # Environment configuration
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env` file

## Usage

Run the agent to analyze a codebase:
```bash
python agent.py
```

## Target Repository

**Note**: The target repository used for analysis is excluded from this repository to maintain separation of concerns. The target repository should be placed in a separate directory and referenced by the agent during analysis.

The target repository contains the actual codebase being analyzed and is not part of this tool's source code.

## Configuration

- `.env`: Configure API keys and other environment variables
- `.gitignore`: Excludes target-repo, runs directory, and sensitive files

## License

MIT License
