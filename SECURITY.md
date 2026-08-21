# Security policy

Unified GUI is an operator console over external authoritative backends. It does not
make those backends safe by itself. Keep the standalone server bound to loopback. The
local-client and Origin checks are a localhost safeguard, not internet-facing
authentication. When the application is mounted into another FastAPI host, that host is
responsible for authentication, session security and transport security.

Write actions can modify permission, ticket, task, decision, prompt, scheduler and agent
state through their adapters. Configure only trusted backend paths and commands, retain
the existing `LOCK.permissions.json` gates and use the least privileged host role.
Credential values do not belong in the repository or Unified GUI configuration; use the
backend credential stores and references.

The JSONL audit log records action metadata and argument names, never argument values or
response bodies. Logging is best effort and is neither an authorization control nor a
tamper-proof ledger. Protect `~/.ellmos/unified-gui/audit.jsonl` with account-local file
permissions and an appropriate retention policy.

Do not report a vulnerability by posting credentials, personal paths, production logs or
backend data in a public issue. Use a private maintainer channel and provide the smallest
synthetic reproduction.
