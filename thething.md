
<install>
curl -fsSL https://gh.io/copilot-install | bash
</install>


<topics_to_research>
- custom agents - https://docs.github.com/en/copilot/tutorials/customization-library/custom-agents/your-first-custom-agent
- hooks https://docs.github.com/en/copilot/reference/hooks-configuration
- skills https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
- mcp
- custome instructions and agents.md https://docs.github.com/en/copilot/tutorials/coding-agent/get-the-best-results#adding-custom-instructions-to-your-repository
-
</topics_to_research>

<sample_workshop>
🛠 Workshop: Getting Started with GitHub Copilot CLI

1. Introduction

Goal: Help participants understand and experiment with GitHub Copilot CLI.

Audience: Developers familiar with GitHub and the terminal, but new to Copilot CLI.

Outcome: By the end, participants will be able to run Copilot CLI commands, interact with projects, and automate GitHub tasks.

2. Setup & Installation

Requirements:

GitHub Copilot Pro, Business, or Enterprise plan.

Linux, macOS, or Windows (via WSL or experimental PowerShell support).

Steps:

Install Copilot CLI following GitHub Docs.

Authenticate with GitHub.

Verify installation:

copilot --help

3. Modes of Use

Mode

How to Start

Example

Interactive

copilot

Start a session, ask questions, iterate.

Programmatic

copilot -p "..."

One-off commands, e.g.: copilot -p "Summarize this week’s commits" --allow-tool 'shell(git)'

4. Hands-On Exercises

Exercise A: Interactive Mode Basics

Run copilot.

Ask: “What does this repo do?”

Follow up: “Suggest improvements to README.”

Exercise B: Programmatic Mode

Run:

copilot -p "Show me the last 5 changes in CHANGELOG.md"

Discuss how Copilot finds and summarizes changes.

Exercise C: Local Project Tasks

Prompt Copilot to:

Change CSS background color of <h1> headings.

Commit changes with:

copilot -p "Commit the changes to this repo" --allow-tool 'shell(git)'

Exercise D: GitHub.com Integration

Ask Copilot to:

List open PRs:

copilot -p "List my open PRs"

Create a new issue:

copilot -p "Raise an improvement issue in OWNER/REPO"

5. Customization

Custom Instructions: Tailor Copilot to your project’s build/test workflow.

Agents: Create specialized versions (e.g., frontend expert).

Hooks: Add validation or logging at key points.

Skills: Extend Copilot with scripts/resources.

6. Security Considerations

Trusted directories: Only launch Copilot CLI in safe project folders.

Tool approvals:

--allow-tool 'shell(git)' → allow specific commands.

--deny-tool 'shell(rm)' → block risky commands.

Best practice: Avoid --allow-all-tools unless in a sandbox environment.

7. Wrap-Up & Next Steps

Recap: Copilot CLI helps you code, manage repos, and automate tasks directly from the terminal.

Challenge: Ask participants to create a small Next.js app with Tailwind CSS using Copilot CLI, then run and view it.

Further exploration: Try customizing agents and experimenting with MCP servers.

Key takeaway: GitHub Copilot CLI brings AI assistance directly into your terminal, making it easy to iterate on code, manage GitHub tasks, and automate workflows—all without leaving the command line.

Would you like me to design this workshop as a step-by-step agenda with timing (e.g., 15 min intro, 30 min exercises), so it’s ready to deliver live?

References (1)

About GitHub Copilot CLI. https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli
</sample_workshop>
