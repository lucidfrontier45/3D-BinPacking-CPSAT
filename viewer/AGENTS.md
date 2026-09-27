# AGENTS.md

Frontend viewer for 3D bin packing solutions. React + Three.js + Vite.

## Commands

| Task | Command |
| --- | --- |
| Dev server | `bun run dev` |
| Build (type check + bundle) | `bun run build` |
| Lint | `bun run lint` |

## Layout

- `src/` — source
- `public/` — static assets
- `index.html` — entry point
- `vite.config.ts` — Vite config

## Style

- TypeScript strict mode; type hints on every signature.
- React function components with hooks (React Compiler enabled — no manual `memo`/`useMemo` unless needed).
- Functional, immutable updates.

## Boundaries

- Use `bun` for all package management — never `npm` or `yarn`.
- Run `bun run lint` and `bun run build` before finishing any task that edits source files.
