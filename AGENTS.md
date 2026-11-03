# Project workflow

- Implement only the phase the user has requested; do not start later phases automatically.
- After each completed and verified phase, commit and push the project changes to
  `https://github.com/SalmanAliAqdas/rumi-library-system.git` on the current project branch.
- Before each push, inspect Git status and the staged changes. Verify that secrets,
  actual `.env` files, local databases, private borrower records and backup exports
  are excluded. `.env.example` may contain placeholders only.
- Preserve existing commits and unrelated work. Never force-push or rewrite history
  to publish a phase. Fetch and inspect remote changes before integrating them.
- Run checks appropriate to the changes and report actual results, including skips
  or unresolved failures. PostgreSQL checks remain required before production.
- Keep `docs/PROJECT_STATUS.md` current so a future session can continue.
- Do not provision infrastructure or deploy unless separately requested.
