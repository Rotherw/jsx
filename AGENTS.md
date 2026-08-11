# AGENTS

## Repository at a glance
- Root project is the JSX specification source.
- `spec.emu` is the source of truth for the spec text.
- `index.html` is generated from `spec.emu` via `ecmarkup`.
- `workshop3d_publisher/` is a separate Python project with its own runtime and tests.

## Key files and directories
- `/home/runner/work/jsx/jsx/spec.emu` — main JSX spec source.
- `/home/runner/work/jsx/jsx/index.html` — generated spec output.
- `/home/runner/work/jsx/jsx/AST.md` — JSX AST extension reference.
- `/home/runner/work/jsx/jsx/.github/workflows/build.yml` — CI build workflow.
- `/home/runner/work/jsx/jsx/workshop3d_publisher/src/workshop3d/` — Python app code.
- `/home/runner/work/jsx/jsx/workshop3d_publisher/tests/` — Python test suite.

## Build and test commands

### JSX spec (repo root)
- Install deps: `npm install`
- Build spec: `npm run build`
- Watch mode: `npm run start`

### WorkShop3D publisher
- Working directory: `/home/runner/work/jsx/jsx/workshop3d_publisher`
- Install deps: `pip install -r requirements.txt`
- Run tests: `python -m pytest`

## Change guidelines for agents
- Keep changes minimal and scoped to the task.
- If `spec.emu` changes, rebuild `index.html` with `npm run build`.
- Do not commit secrets; use environment variables for credentials.
- Prefer updating existing docs (`README.md`, `CONTRIBUTING.md`, `AST.md`) instead of duplicating guidance.
