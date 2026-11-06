# Bean-Grinder Agent & Skill Routing Rules

## Subagents (13 Local Specialists)
All local subagents in `agents/*.md` use `kind: local`, `subagent: true`, `mainAgent: false`, `model: inherit`, and normalized tool names (`read_file`, `write_file`, `edit_file`, `run_command`):
- **Discovery Scouts:** `codmod-assessor`, `graphify-scout`, `migration-scout`, `seam-scout`, `spec-recovery-agent`
- **Synthesis & Execution:** `synthesis-agent`, `ast-grinder`, `msbuild`, `runtime-parity-verifier`
- **Adversarial Reviewers:** `reviewer-exec`, `reviewer-engineer`, `reviewer-architect`, `reviewer-pm`
- **Shared Core Arbiter:** `review-arbiter` is provided by `bean-core`.

## Skills
- `assess`: Runs concurrent discovery scouts and invokes `scripts/digest_report.py` to emit `migration_matrix.json` and an OKF-compatible `05_PLAN.md`.
- `synthesize`: Runs `skills/synthesize/scripts/synthesize_runner.py` and optional `@synthesis-agent` customization to emit `05_PLAN.md`.
- `adversarial-review`: Dispatches the 4 reviewer personas and runs `scripts/review_loop.py` to harden `05_PLAN.md`.
- `rewrite`: Orchestrates the full 7-phase legacy modernization and parity verification lifecycle.
