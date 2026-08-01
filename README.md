# AI Codebase Analysis Agent

An intelligent AI-powered agent for analyzing, understanding, and modifying codebases using advanced language models. This tool provides comprehensive code analysis, automated documentation generation, architectural insights, and intelligent code modification capabilities.

## 🚀 Features

- **Automated Code Analysis**: Deep analysis of entire codebases to understand structure, patterns, and relationships
- **Intelligent Planning**: AI-powered planning system that breaks down complex requests into actionable steps
- **Context-Aware Code Generation**: Generates code patches with full understanding of repository context
- **Automated Testing & Validation**: Validates changes with automated testing and route extraction
- **Documentation Generation**: Automatically generates comprehensive documentation and summaries
- **Architecture Insights**: Provides high-level architectural understanding and dependency mapping
- **Schema Analysis**: Analyzes data schemas, models, and their relationships
- **Multi-Stage Pipeline**: Complete pipeline from exploration to validation and summarization

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git
- API key for an LLM provider (OpenAI, Google Gemini, or compatible service)

## 🔧 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Suvradip01/ai-codebase-analysis.git
cd ai-codebase-analysis
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r ai-coding-agent/requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the `ai-coding-agent` directory:

```bash
cd ai-coding-agent
```

Create `.env` file with the following content:

```env
# LLM Provider Configuration
OPENAI_API_KEY=your_openai_api_key_here
# OR
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Model Configuration
MODEL_NAME=gpt-4o
# OR for Gemini
MODEL_NAME=gemini-flash-latest
```

## 🎯 Usage

### Basic Usage

Run the agent to analyze and modify a codebase:

```bash
cd ai-coding-agent
python agent.py --repo-path <path-to-your-repo> --request "<your-request>"
```

### Example Commands

```bash
# Analyze a repository and add a new feature
python agent.py --repo-path ../my-project --request "Add user authentication system"

# Fix a bug in existing code
python agent.py --repo-path ../my-project --request "Fix the memory leak in the data processing module"

# Refactor code for better performance
python agent.py --repo-path ../my-project --request "Refactor the database queries for better performance"

# Add documentation
python agent.py --repo-path ../my-project --request "Add comprehensive documentation to all API endpoints"
```

### Command Line Arguments

- `--repo-path`: (Required) Path to the target git repository you want to analyze/modify
- `--request`: (Required) Natural language description of what you want the agent to do

## 📁 Project Structure

```
ai-codebase-analysis/
├── ai-coding-agent/
│   ├── agent.py              # Main entry point and orchestration logic
│   ├── requirements.txt      # Python dependencies
│   ├── .env                  # Environment configuration (API keys, etc.)
│   ├── .gitignore           # Files to exclude from git
│   ├── core/                # Core functionality modules
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration constants and stage names
│   │   ├── llm_client.py    # LLM API client (OpenAI/Gemini integration)
│   │   ├── repo_explorer.py # Repository structure analysis
│   │   ├── context_selector.py # Intelligent context selection
│   │   ├── planner.py       # AI-powered planning system
│   │   ├── code_generator.py # Code patch generation
│   │   ├── patch_applier.py # Apply patches to repository
│   │   ├── validator.py     # Validation and testing
│   │   └── summarizer.py    # Final summary generation
│   ├── prompts/             # System prompts for LLM interactions
│   │   ├── planner_system.md
│   │   └── codegen_system.md
│   ├── schemas/             # Data models and schemas
│   │   ├── __init__.py
│   │   └── models.py
│   └── runs/                # Analysis run outputs and logs
│       └── .gitkeep
└── README.md               # This file
```

## 🔍 How It Works

The agent follows a multi-stage pipeline:

1. **Repository Exploration**: Analyzes the target repository structure, files, and dependencies
2. **Context Selection**: Intelligently selects relevant files and context based on the user's request
3. **Planning**: Uses AI to create a detailed plan for implementing the requested changes
4. **Code Generation**: Generates code patches with full understanding of repository context
5. **Patch Application**: Applies the generated patches to the target repository
6. **Validation**: Validates changes with automated testing and verification
7. **Summarization**: Generates a comprehensive summary of all changes and outcomes

## ⚙️ Configuration

### Environment Variables

Configure these in your `.env` file:

- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI)
- `GEMINI_API_KEY`: Your Google Gemini API key (if using Gemini)
- `MODEL_NAME`: The specific model to use (e.g., `gpt-4o`, `gemini-flash-latest`)

### Supported LLM Providers

- **OpenAI**: GPT-4, GPT-3.5, and compatible models
- **Google Gemini**: Gemini Pro, Gemini Flash, and compatible models
- **Other OpenAI-compatible APIs**: Any API that follows the OpenAI API format

## 📊 Output

The agent generates detailed outputs in the `runs/` directory:

- **Timestamped run directories**: Each run creates a new directory with timestamp
- **Summary files**: Comprehensive markdown summaries of the entire analysis
- **Patch files**: Generated code patches with explanations
- **Validation reports**: Detailed validation and testing results
- **Plan documents**: AI-generated implementation plans

## 🛠️ Troubleshooting

### Common Issues

**Issue**: Module not found errors
```bash
# Solution: Ensure you're in the correct directory and dependencies are installed
cd ai-coding-agent
pip install -r requirements.txt
```

**Issue**: API authentication errors
```bash
# Solution: Check your .env file and ensure API keys are correct
# Make sure the .env file is in the ai-coding-agent directory
```

**Issue**: Repository path not found
```bash
# Solution: Use absolute paths or ensure relative paths are correct
python agent.py --repo-path "C:/path/to/repo" --request "your request"
```

**Issue**: Git repository errors
```bash
# Solution: Ensure the target repository is a valid git repositorycd target-repo
git init
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🎯 Target Repository Note

**Important**: The target repository used for analysis is excluded from this repository to maintain separation of concerns. 

When using this agent:
- Place your target repository (the one you want to analyze/modify) in a separate directory
- Reference it using the `--repo-path` argument
- The target repository is NOT part of this tool's source code

Example structure:
```
parent-directory/
├── ai-codebase-analysis/    # This repository
└── my-project/              # Your target repository (to analyze)
```

## 📧 Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## 🙏 Acknowledgments

- Built with advanced AI language models
- Inspired by modern AI-assisted development tools
- Designed for seamless integration into development workflows
