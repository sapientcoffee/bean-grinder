# Bean-Grinder Agent & Skill Routing Rules

## Subagents (13 Local Specialists)
All local subagents in `agents/*.md` use `kind: local`, `subagent: true`, `mainAgent: false`, `model: inherit`, and normalized tool names (`read_file`, `write_file`, `edit_file`, `run_command`):
- **Discovery Scouts:** `codmod-assessor`, `graphify-scout`, `migration-scout`, `seam-scout`, `spec-recovery-agent`
- **Synthesis & Execution:** `synthesis-agent`, `ast-grinder`, `msbuild`, `runtime-parity-verifier`
- **Adversarial Reviewers:** `reviewer-exec`, `reviewer-engineer`, `reviewer-architect`, `reviewer-pm`
- **Shared Core Arbiter:** `review-arbiter` is provided by `bean-core`.

## Skills
- `assess`: Runs concurrent discovery scouts as isolated `invoke_subagent` calls (never `/teamwork`, keeping Stage 1 discovery unbiased) and invokes `scripts/digest_report.py` to emit `migration_matrix.json` and an OKF-compatible `05_PLAN.md`.
- `synthesize`: Runs `skills/synthesize/scripts/synthesize_runner.py` and optional `@synthesis-agent` customization to emit `05_PLAN.md`.
- `adversarial-review`: Supports Mode A (Hub-and-Spoke `invoke_subagent` dispatch) and Mode B (Antigravity Enterprise `/teamwork` Autonomous Stakeholder Council with `@synthesis-agent`, `@reviewer-exec`, `@reviewer-architect`, `@reviewer-pm`, `@reviewer-engineer`, and `@review-arbiter` debating via `send_message`) plus `scripts/review_loop.py` to harden `05_PLAN.md`.
- `rewrite`: Orchestrates the full 7-phase legacy modernization lifecycle in the Smart Zone by delegating Phases 2–6 to subagents (`@spec-recovery-agent`, `@seam-scout`, `@synthesis-agent`, `@ast-grinder`, `@runtime-parity-verifier`) and recommending `/teamwork` for Phase 5 adversarial plan hardening and Phase 6 parallel slice implementation (`@ast-grinder` + `@runtime-parity-verifier`).
