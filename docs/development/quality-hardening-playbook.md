# Quality Hardening Playbook

## Purpose

This playbook defines how Kotaemon keeps quality, compatibility and security controls healthy while dependencies and infrastructure evolve.

## 1. Controlled major-upgrade strategy

Target components for staged upgrades:

- `gradio`
- `langchain` family
- `llama-index` family
- `pypdf`

Upgrade policy:

1. Upgrade one family at a time in dedicated PRs.
2. Keep behavioral changes isolated from refactoring in separate commits.
3. Require green checks for:
   - `pre-commit`
   - `libs/kotaemon/tests`
   - `libs/ktem/ktem_tests`
   - smoke imports (`app`, PromptUI paths)
4. If a major upgrade requires code migration, add temporary compatibility notes in docs and remove them after migration completes.

Rollback policy:

- Revert only the specific upgrade PR.
- Keep CI/security workflow changes if they are backward compatible.

## 2. Linting and typing policy

Current stack contains both `ruff` and `flake8`. To avoid duplicated diagnostics:

- Use `ruff` for fast rules and autofix.
- Keep `flake8` only for rules not yet covered by the chosen `ruff` profile.
- Revisit rule overlap every dependency refresh cycle and remove duplicates.

Typing policy:

- `mypy` runs in CI and locally through pre-commit/dev tooling.
- New modules should avoid introducing untyped public interfaces where practical.

## 3. Security baseline

Mandatory controls:

- Dependency audit (`pip-audit`) in CI.
- Container image scanning (Trivy) before publishing images.

Recommended controls:

- Add SAST baseline (`bandit` and/or `semgrep` or `CodeQL`) as a follow-up hardening step.
- Keep a documented waiver process for unavoidable vulnerabilities:
  - issue id
  - risk assessment
  - mitigation
  - expiry/review date

## 4. Regular maintenance cycle

For every cycle:

1. Review outdated dependencies and categorize into patch/minor/major.
2. Triage vulnerability report and create prioritized fixes.
3. Re-run compatibility matrix checks (Python, OS, runtime imports, tests).
4. Update contributor docs if CI or local workflows changed.

## 5. Definition of done for hardening changes

A hardening change is considered complete when:

- CI checks are enforced (not informational only).
- At least one regression test or smoke check protects the changed behavior.
- Documentation reflects the new workflow.
