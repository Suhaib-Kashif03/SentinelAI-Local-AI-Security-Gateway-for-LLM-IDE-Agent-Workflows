# Problem Statement

AI coding assistants and local LLM agents are increasingly used to generate code, terminal commands, configuration files, and security-sensitive workflows. While these tools improve productivity, they can also produce unsafe outputs or follow malicious instructions.

A developer may unknowingly copy and execute AI-generated commands that delete files, expose credentials, install malicious scripts, or weaken system security. Prompt injection attacks can manipulate the behavior of LLM-based assistants, causing them to ignore instructions, reveal sensitive information, or misuse connected tools.

SentinelAI addresses this problem by acting as a local security gateway between the user and the AI assistant. It scans prompts, LLM responses, generated code, and terminal commands before execution. The system classifies each input as ALLOW, WARN, BLOCK, or REQUIRE_APPROVAL based on configurable security policies.

The goal is to help developers, students, and small organizations use local AI assistants more safely without relying on cloud-based monitoring tools.