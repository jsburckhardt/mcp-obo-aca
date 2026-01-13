# Contributing to MCP Server with OAuth 2.1 and OBO Flow

Thank you for your interest in contributing to this project! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/mcp-obo-aca.git`
3. Add upstream remote: `git remote add upstream https://github.com/jsburckhardt/mcp-obo-aca.git`

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Docker](https://docs.docker.com/get-docker/) (optional, for containerized testing)

### Local Development

```bash
# Navigate to the src directory
cd src

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (including dev dependencies)
pip install -r requirements.txt
pip install pytest pytest-asyncio cryptography

# Copy environment template
cp .env.example .env

# Edit .env with your Azure AD configuration
# (See docs/02-azure-setup.md for detailed instructions)

# Run tests
pytest tests/ -v

# Run the server locally (without auth for testing)
python server.py --no-auth

# Run with authentication
python server.py
```

## How to Contribute

### Reporting Bugs

- Check if the bug has already been reported in [Issues](https://github.com/jsburckhardt/mcp-obo-aca/issues)
- If not, create a new issue with:
  - Clear title and description
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (OS, Python version, etc.)
  - Relevant logs or screenshots

### Suggesting Enhancements

- Check existing [Issues](https://github.com/jsburckhardt/mcp-obo-aca/issues) and [Pull Requests](https://github.com/jsburckhardt/mcp-obo-aca/pulls)
- Create a new issue describing:
  - The enhancement and its benefits
  - Potential implementation approach
  - Any breaking changes

### Contributing Code

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes following the [coding standards](#coding-standards)
3. Write or update tests as needed
4. Ensure all tests pass: `pytest tests/ -v`
5. Commit your changes with clear messages
6. Push to your fork: `git push origin feature/your-feature-name`
7. Open a Pull Request

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for function signatures
- Write docstrings for all public modules, functions, classes, and methods
- Keep functions focused and concise
- Maximum line length: 100 characters (soft limit), 120 (hard limit)

### Documentation

- Update relevant documentation in `src/docs/` when making changes
- Keep the main `README.md` up to date
- Document new features with usage examples
- Update API documentation for new endpoints or tools

### Git Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add feature", "Fix bug", "Update docs")
- Reference related issues: `Fix #123: Description of fix`
- Keep the first line under 72 characters
- Add detailed explanation in the body if needed

Example:
```
Add health check endpoint for container orchestration

- Implement /health endpoint returning JSON status
- Add tests for health check endpoint
- Update documentation with endpoint details

Fixes #45
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_verifier.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Writing Tests

- Write tests for all new features and bug fixes
- Follow existing test patterns in the `tests/` directory
- Use descriptive test names that explain what is being tested
- Mock external dependencies (Azure AD, Microsoft Graph, etc.)
- Ensure tests are deterministic and can run in isolation

## Pull Request Process

1. **Before Submitting:**
   - Ensure all tests pass
   - Update documentation as needed
   - Verify your code follows the coding standards
   - Rebase on latest main: `git pull --rebase upstream main`

2. **PR Description:**
   - Clearly describe what the PR does
   - Reference related issues
   - List any breaking changes
   - Include screenshots for UI changes (if applicable)

3. **Review Process:**
   - Maintainers will review your PR
   - Address any feedback or requested changes
   - Keep the PR focused on a single feature/fix
   - Be responsive to comments and questions

4. **After Approval:**
   - Maintainers will merge your PR
   - Your contribution will be included in the next release

## Questions?

If you have questions or need help, feel free to:
- Open an issue
- Reach out to maintainers
- Check existing documentation in the `src/docs/` directory

Thank you for contributing! 🎉
