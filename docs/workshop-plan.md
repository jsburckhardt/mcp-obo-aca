# 🛠 Workshop: GitHub Copilot CLI - Fundamentals & Customization

## Overview

| | |
|---|---|
| **Duration** | 3.5 hours (half-day) |
| **Audience** | Intermediate developers familiar with GitHub Copilot, new to CLI |
| **Format** | Hands-on workshop with exercises |
| **Prerequisites** | GitHub Copilot Pro/Business/Enterprise, terminal experience |

### Learning Outcomes

By the end of this workshop, participants will be able to:

1. Use GitHub Copilot CLI in interactive and programmatic modes
2. Create custom instructions with AGENTS.md for repository-specific context
3. Build custom agents for specialized tasks
4. Configure hooks for validation and automation
5. Create skills to extend Copilot's capabilities
6. Understand MCP (Model Context Protocol) for advanced extensibility
7. Apply security best practices for tool permissions

---

## Workshop Agenda

| Time | Module | Duration |
|------|--------|----------|
| 0:00 | [Module 1: Introduction & Setup](#module-1-introduction--setup-20-min) | 20 min |
| 0:20 | [Module 2: Copilot CLI Modes](#module-2-copilot-cli-modes-30-min) | 30 min |
| 0:50 | [Module 3: Custom Instructions & AGENTS.md](#module-3-custom-instructions--agentsmd-35-min) | 35 min |
| 1:25 | ☕ **Break** | 10 min |
| 1:35 | [Module 4: Custom Agents](#module-4-custom-agents-40-min) | 40 min |
| 2:15 | [Module 5: Hooks](#module-5-hooks-30-min) | 30 min |
| 2:45 | ☕ **Break** | 10 min |
| 2:55 | [Module 6: Skills](#module-6-skills-25-min) | 25 min |
| 3:20 | [Module 7: MCP Introduction](#module-7-mcp-introduction-30-min) | 30 min |
| 3:50 | [Module 8: Security & Best Practices](#module-8-security--best-practices-15-min) | 15 min |
| 4:05 | [Module 9: Wrap-Up & Challenge](#module-9-wrap-up--challenge-15-min) | 15 min |

---

## Module 1: Introduction & Setup (20 min)

### Goals

- Understand what GitHub Copilot CLI is and when to use it
- Install and authenticate Copilot CLI
- Verify the installation works

### Key Concepts

**What is GitHub Copilot CLI?**

GitHub Copilot CLI is an AI-powered terminal assistant that helps you:
- Write and debug code directly in your terminal
- Manage GitHub tasks (PRs, issues, commits)
- Automate workflows without leaving the command line
- Get contextual help based on your codebase

**When to use CLI vs IDE Extension:**

| Use CLI | Use IDE Extension |
|---------|-------------------|
| Terminal-based workflows | Visual editing |
| Automation scripts | Real-time code suggestions |
| Quick one-off tasks | Inline completions |
| CI/CD integration | Chat in editor |

### Installation

```bash
# Install Copilot CLI
curl -fsSL https://gh.io/copilot-install | bash

# Authenticate with GitHub
copilot auth login

# Verify installation
copilot --help
```

### Exercise 1.1: Verify Your Setup

1. Open your terminal
2. Run `copilot --version` to check the version
3. Run `copilot --help` to see available options
4. Start an interactive session with `copilot` and ask: "What can you do?"

**✅ Success criteria:** You see the Copilot CLI interface and get a response.

---

## Module 2: Copilot CLI Modes (30 min)

### Goals

- Master interactive mode for exploratory work
- Use programmatic mode for automation
- Understand tool permissions

### Key Concepts

**Two Modes of Operation:**

| Mode | Command | Use Case |
|------|---------|----------|
| **Interactive** | `copilot` | Exploration, multi-turn conversations, iterative tasks |
| **Programmatic** | `copilot -p "prompt"` | One-off commands, scripts, automation |

**Interactive Mode:**

```bash
# Start interactive session
copilot

# You can now have a conversation:
# > "What does this repo do?"
# > "Show me the main entry point"
# > "Suggest improvements to the README"
```

**Programmatic Mode:**

```bash
# One-off command
copilot -p "Summarize this week's commits"

# With tool permissions
copilot -p "Show git status" --allow-tool 'shell(git)'

# Chain with shell
copilot -p "List my open PRs" | head -20
```

**Tool Permissions:**

```bash
# Allow specific tools
--allow-tool 'shell(git)'        # Allow git commands
--allow-tool 'shell(npm)'        # Allow npm commands

# Deny dangerous tools
--deny-tool 'shell(rm)'          # Block rm command
--deny-tool 'shell(sudo)'        # Block sudo

# Allow all (use with caution!)
--allow-all-tools                # Only in sandboxed environments
```

### Exercise 2.1: Interactive Exploration

1. Clone a sample repository (or use any project you have)
2. Start `copilot` in interactive mode
3. Ask: "What does this repo do?"
4. Follow up: "What are the main dependencies?"
5. Ask: "Suggest three improvements"

### Exercise 2.2: Programmatic Commands

Run these one-liners and observe the output:

```bash
# Git summary
copilot -p "Show me the last 5 commits in a table format" --allow-tool 'shell(git)'

# Code analysis
copilot -p "Find all TODO comments in this project" --allow-tool 'shell(grep)'

# Documentation help
copilot -p "Generate a one-paragraph description of this project"
```

**✅ Success criteria:** You can switch between modes and use tool permissions appropriately.

---

## Module 3: Custom Instructions & AGENTS.md (35 min)

### Goals

- Understand how custom instructions shape Copilot's behavior
- Create an effective AGENTS.md file
- Apply project-specific context

### Key Concepts

**What are Custom Instructions?**

Custom instructions are guidelines stored in your repository that tell Copilot:
- How your project is structured
- What coding conventions to follow
- Which commands to use for building/testing
- Project-specific context and rules

**Where to Put Instructions:**

| File | Scope | Purpose |
|------|-------|---------|
| `AGENTS.md` | Repository root | General project guidelines |
| `.github/copilot-instructions.md` | Repository | GitHub-specific instructions |
| `docs/AGENTS.md` | Subdirectory | Module-specific guidelines |

**AGENTS.md Structure:**

```markdown
# AGENTS Guidelines for [Project Name]

## 1. Project Overview
Brief description of what this project does.

## 2. Development Environment
- Language/runtime requirements
- How to install dependencies
- Local development commands

## 3. Code Conventions
- Naming conventions
- File organization
- Testing requirements

## 4. Useful Commands
| Command | Purpose |
|---------|---------|
| `npm run dev` | Start development server |
| `npm test` | Run tests |

## 5. Rules
- Always run tests before committing
- Use conventional commits
- Document new features
```

### Exercise 3.1: Analyze an AGENTS.md

Review the AGENTS.md in this repository:

```bash
copilot
> "Show me the AGENTS.md file and explain what each section does"
```

### Exercise 3.2: Create Your Own AGENTS.md

1. Think of a project you work on (or create a simple one)
2. Create an AGENTS.md with:
   - Project overview (2-3 sentences)
   - Development setup commands
   - At least 3 coding conventions
   - A "Useful Commands" table

**Template to start:**

```markdown
# AGENTS Guidelines for My Project

## 1. Overview
[What does this project do?]

## 2. Setup
- Install: `[command]`
- Run: `[command]`
- Test: `[command]`

## 3. Conventions
- [Convention 1]
- [Convention 2]
- [Convention 3]

## 4. Commands
| Command | Purpose |
|---------|---------|
| ... | ... |
```

**✅ Success criteria:** You have a working AGENTS.md that Copilot CLI uses for context.

---

## Module 4: Custom Agents (40 min)

### Goals

- Understand what custom agents are
- Create specialized agents for different tasks
- Configure agent behavior and tools

### Key Concepts

**What are Custom Agents?**

Custom agents are specialized versions of Copilot with:
- Focused expertise (e.g., "frontend expert", "security reviewer")
- Predefined tools and permissions
- Custom prompts and behaviors

**Agent Configuration:**

Agents are defined in `.github/copilot/agents/` directory:

```
.github/
└── copilot/
    └── agents/
        ├── code-reviewer.md
        ├── docs-writer.md
        └── test-expert.md
```

**Agent File Format:**

```markdown
---
name: code-reviewer
description: Reviews code for best practices and potential issues
tools:
  - shell(git)
  - view
  - grep
---

# Code Reviewer Agent

You are an expert code reviewer. When reviewing code:

1. Check for potential bugs and edge cases
2. Verify error handling is appropriate
3. Look for security vulnerabilities
4. Suggest performance improvements
5. Ensure code follows project conventions

Be constructive and explain the "why" behind suggestions.
```

**Invoking Custom Agents:**

```bash
# Interactive mode - select agent
copilot

# Programmatic mode
copilot -p "Review my staged changes" --agent code-reviewer
```

### Exercise 4.1: Create a Documentation Agent

Create `.github/copilot/agents/docs-writer.md`:

```markdown
---
name: docs-writer
description: Helps write and improve documentation
tools:
  - view
  - edit
  - glob
---

# Documentation Writer Agent

You are a technical writing expert. When writing documentation:

1. Use clear, concise language
2. Include code examples where helpful
3. Structure content with headers and lists
4. Consider the reader's experience level
5. Add links to related documentation

Follow the project's existing documentation style.
```

Test it:
```bash
copilot -p "Improve the README introduction" --agent docs-writer
```

### Exercise 4.2: Create a Test Expert Agent

Create `.github/copilot/agents/test-expert.md`:

```markdown
---
name: test-expert
description: Helps write and debug tests
tools:
  - shell(pytest)
  - shell(npm test)
  - view
  - edit
---

# Test Expert Agent

You are a testing specialist. When working on tests:

1. Follow AAA pattern (Arrange, Act, Assert)
2. Test edge cases and error conditions
3. Keep tests focused and independent
4. Use descriptive test names
5. Mock external dependencies appropriately

Prefer integration tests for critical paths, unit tests for logic.
```

Test it:
```bash
copilot -p "Write tests for the authentication module" --agent test-expert
```

**✅ Success criteria:** You have created and invoked at least one custom agent.

---

## Module 5: Hooks (30 min)

### Goals

- Understand the hook system
- Create validation hooks
- Add logging and automation hooks

### Key Concepts

**What are Hooks?**

Hooks are scripts that run at specific points in Copilot's workflow:
- **Pre-hooks**: Run before an action (validation, confirmation)
- **Post-hooks**: Run after an action (logging, cleanup, notifications)

**Hook Configuration:**

Create `.github/copilot/hooks.json`:

```json
{
  "hooks": {
    "pre-edit": [
      {
        "name": "backup-file",
        "command": "cp {{file}} {{file}}.bak",
        "description": "Backup file before editing"
      }
    ],
    "post-edit": [
      {
        "name": "run-linter",
        "command": "npm run lint -- {{file}}",
        "description": "Lint file after editing"
      }
    ],
    "pre-commit": [
      {
        "name": "run-tests",
        "command": "npm test",
        "description": "Run tests before committing"
      }
    ]
  }
}
```

**Available Hook Points:**

| Hook | When It Runs |
|------|--------------|
| `pre-edit` | Before modifying a file |
| `post-edit` | After modifying a file |
| `pre-commit` | Before creating a commit |
| `post-commit` | After creating a commit |
| `pre-shell` | Before running a shell command |
| `post-shell` | After running a shell command |

**Hook Variables:**

| Variable | Description |
|----------|-------------|
| `{{file}}` | Current file path |
| `{{files}}` | All affected files |
| `{{message}}` | Commit message |
| `{{command}}` | Shell command being run |

### Exercise 5.1: Create a Validation Hook

Create `.github/copilot/hooks.json`:

```json
{
  "hooks": {
    "pre-commit": [
      {
        "name": "check-branch",
        "command": "git branch --show-current | grep -v '^main$'",
        "description": "Prevent commits directly to main",
        "failOnError": true
      }
    ]
  }
}
```

### Exercise 5.2: Create a Logging Hook

Extend hooks.json to log all edits:

```json
{
  "hooks": {
    "post-edit": [
      {
        "name": "log-edit",
        "command": "echo \"$(date): Edited {{file}}\" >> .copilot-edits.log",
        "description": "Log all file edits"
      }
    ]
  }
}
```

**✅ Success criteria:** You have a working hooks.json with at least one hook.

---

## Module 6: Skills (25 min)

### Goals

- Understand what skills are
- Create a skill file
- Know when to use skills vs agents

**What are Skills?**

Skills are reusable prompts that teach Copilot how to perform specific tasks:
- Stored as `.prompt.md` files
- Can include examples and templates
- Invoked on-demand for specific tasks

**Skills vs Agents:**

| Skills | Agents |
|--------|--------|
| Task-specific prompts | Persistent personas |
| Invoked for one task | Available throughout session |
| No tool configuration | Custom tool permissions |
| Lightweight | Full configuration |

**Skill File Format:**

```markdown
---
name: api-endpoint
description: Generate a REST API endpoint
---

# API Endpoint Generator

When creating a new API endpoint, follow this pattern:

## Template

```python
@app.route('/api/v1/{resource}', methods=['{method}'])
def {function_name}():
    """
    {description}
    
    Returns:
        JSON response with {resource} data
    """
    try:
        # Implementation
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## Checklist
- [ ] Add input validation
- [ ] Include error handling
- [ ] Add appropriate status codes
- [ ] Document with docstring
- [ ] Add to API documentation
```

### Exercise 6.1: Create a Skill

Create `.github/copilot/skills/commit-message.prompt.md`:

```markdown
---
name: commit-message
description: Generate conventional commit messages
---

# Conventional Commit Generator

Generate commit messages following the Conventional Commits specification.

## Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

## Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

## Examples
- `feat(auth): add OAuth 2.0 support`
- `fix(api): handle null response from server`
- `docs(readme): update installation instructions`

## Rules
1. Use imperative mood ("add" not "added")
2. Don't capitalize first letter
3. No period at the end
4. Keep under 72 characters
```

Test it:
```bash
copilot -p "Generate a commit message for my staged changes" --skill commit-message
```

**✅ Success criteria:** You have created and used a skill file.

---

## Module 7: MCP Introduction (30 min)

### Goals

- Understand what MCP (Model Context Protocol) is
- See how MCP extends Copilot CLI capabilities
- Explore a real MCP server implementation

### Key Concepts

**What is MCP?**

MCP (Model Context Protocol) is a standard for connecting AI models to external tools and data:
- **Protocol**: Standardized way for AI to call external tools
- **Servers**: Applications that expose tools via MCP
- **Extensibility**: Add any capability to Copilot

**MCP Architecture:**

```
┌─────────────┐     MCP Protocol     ┌─────────────────┐
│  Copilot    │◄───────────────────►│   MCP Server    │
│    CLI      │                      │                 │
└─────────────┘                      │  ┌───────────┐  │
                                     │  │  Tools    │  │
                                     │  ├───────────┤  │
                                     │  │ Resources │  │
                                     │  ├───────────┤  │
                                     │  │  Prompts  │  │
                                     │  └───────────┘  │
                                     └─────────────────┘
```

**MCP Concepts:**

| Concept | Description | Example |
|---------|-------------|---------|
| **Tools** | Functions the AI can call | `whoami`, `search_database` |
| **Resources** | Data the AI can read | Files, database records |
| **Prompts** | Pre-defined prompt templates | Workflow starters |

**This Repository as Example:**

This workshop repo contains a full MCP server with:
- OAuth 2.1 authentication
- On-Behalf-Of (OBO) flow for Microsoft Graph
- Three demo tools:

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `greet_test` | Simple greeting | No |
| `get_mcp_server_status` | Server status | No |
| `whoami` | User profile from Graph API | Yes |

### Demo: Exploring the MCP Server

```bash
# Look at the server structure
copilot
> "Explain the architecture of the MCP server in src/"
> "What tools does this MCP server expose?"
> "How does the authentication flow work?"
```

### Exercise 7.1: Run the MCP Server Locally

```bash
cd src

# Install dependencies
pip install -r requirements.txt

# Run without auth (for testing)
python server.py --no-auth

# In another terminal, check health
curl http://localhost:8000/health
```

### Exercise 7.2: Explore MCP Tool Implementation

Look at how tools are implemented:

```bash
copilot
> "Show me how the whoami tool is implemented"
> "What's the difference between authenticated and unauthenticated tools?"
```

**✅ Success criteria:** You understand MCP concepts and have explored the server.

---

## Module 8: Security & Best Practices (15 min)

### Goals

- Apply security best practices
- Understand trusted directories
- Manage tool permissions effectively

### Key Concepts

**Trusted Directories:**

Only run Copilot CLI in directories you trust:
- ✅ Your own projects
- ✅ Cloned repos you've reviewed
- ❌ Random downloaded code
- ❌ Untrusted third-party projects

**Tool Permission Levels:**

```bash
# Most restrictive (default)
copilot -p "task"                    # No tools allowed

# Specific tools only
copilot -p "task" --allow-tool 'shell(git)'

# Multiple specific tools
copilot -p "task" --allow-tool 'shell(git)' --allow-tool 'shell(npm)'

# Block dangerous commands
copilot -p "task" --deny-tool 'shell(rm)' --deny-tool 'shell(sudo)'

# Least restrictive (dangerous!)
copilot -p "task" --allow-all-tools  # Only in sandboxes!
```

**Best Practices Checklist:**

- [ ] Never use `--allow-all-tools` outside sandboxes
- [ ] Review AGENTS.md in cloned repositories
- [ ] Use specific tool permissions, not wildcards
- [ ] Block destructive commands (`rm -rf`, `sudo`)
- [ ] Review Copilot's proposed changes before accepting
- [ ] Don't commit secrets or credentials
- [ ] Use conventional commits with co-author attribution

**Security Red Flags:**

Watch for prompts that try to:
- Access credentials or secrets
- Run with elevated privileges
- Delete files or directories
- Make network requests to unknown hosts
- Modify system configurations

---

## Module 9: Wrap-Up & Challenge (15 min)

### Recap

| Topic | Key Takeaway |
|-------|--------------|
| **CLI Modes** | Interactive for exploration, programmatic for automation |
| **AGENTS.md** | Project-specific context and guidelines |
| **Custom Agents** | Specialized personas with tool permissions |
| **Hooks** | Validation and automation at key points |
| **Skills** | Reusable prompts for specific tasks |
| **MCP** | Protocol for extending Copilot with external tools |
| **Security** | Always use minimal permissions |

### Final Challenge 🏆

**Create a complete Copilot CLI customization for a project:**

1. **Create an AGENTS.md** with:
   - Project overview
   - Development commands
   - At least 3 conventions

2. **Create a custom agent** for one of:
   - Code review
   - Documentation
   - Testing

3. **Create a hooks.json** with:
   - At least one pre-hook
   - At least one post-hook

4. **Create a skill** for a common task in your project

5. **Test everything** by using Copilot CLI with your customizations

**Bonus:** Connect an MCP server and use it with Copilot CLI!

### Further Learning

**Documentation:**
- [Copilot CLI Docs](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli)
- [Custom Agents Tutorial](https://docs.github.com/en/copilot/tutorials/customization-library/custom-agents/your-first-custom-agent)
- [Hooks Configuration](https://docs.github.com/en/copilot/reference/hooks-configuration)
- [About Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

**MCP Resources:**
- [MCP Specification](https://modelcontextprotocol.io/)
- [This Repository](https://github.com/jsburckhardt/mcp-obo-aca) - MCP server with OAuth

**Practice:**
- Customize Copilot for your daily projects
- Create agents for your team's workflows
- Explore community MCP servers

---

## Appendix: Quick Reference

### Commands Cheat Sheet

```bash
# Installation
curl -fsSL https://gh.io/copilot-install | bash

# Authentication
copilot auth login
copilot auth status

# Interactive mode
copilot

# Programmatic mode
copilot -p "your prompt here"

# With tools
copilot -p "prompt" --allow-tool 'shell(git)'

# With agent
copilot -p "prompt" --agent my-agent

# With skill
copilot -p "prompt" --skill my-skill

# Help
copilot --help
```

### File Locations

```
project/
├── AGENTS.md                           # Custom instructions
├── .github/
│   ├── copilot-instructions.md         # GitHub-specific instructions
│   └── copilot/
│       ├── agents/
│       │   └── my-agent.md             # Custom agents
│       ├── skills/
│       │   └── my-skill.prompt.md      # Skills
│       └── hooks.json                  # Hooks configuration
```

### AGENTS.md Template

```markdown
# AGENTS Guidelines for [Project]

## Overview
[Brief description]

## Setup
- Install: `[command]`
- Run: `[command]`  
- Test: `[command]`

## Conventions
- [Convention 1]
- [Convention 2]

## Commands
| Command | Purpose |
|---------|---------|
| `...` | ... |

## Rules
- [Rule 1]
- [Rule 2]
```

---

*Workshop created for GitHub Copilot CLI v1.0+*
