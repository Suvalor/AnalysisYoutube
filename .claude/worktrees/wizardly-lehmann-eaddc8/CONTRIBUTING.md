# Contributing to YouTube Compass

Thank you for your interest in contributing to YouTube Compass! This document covers the basics to get you started.

## Quick Summary

1. Fork the repository
2. Create a feature branch (`feat/your-feature` or `fix/your-fix`)
3. Make your changes
4. Submit a Pull Request

## Fork & Branch Workflow

```shell
# 1. Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/youtube-compass.git
cd youtube-compass

# 2. Add upstream remote
git remote add upstream https://github.com/original-org/youtube-compass.git

# 3. Create a feature branch
git checkout -b feat/your-feature

# 4. Make changes, commit, and push
git add -A
git commit -m "feat: add your feature"
git push origin feat/your-feature

# 5. Open a Pull Request on GitHub
```

### Branch Naming

| Type | Prefix | Example |
|------|--------|---------|
| Feature | `feat/` | `feat/blue-ocean-filter` |
| Bug fix | `fix/` | `fix/radar-crash-on-empty` |
| Documentation | `docs/` | `docs/api-usage` |
| Refactoring | `refactor/` | `refactor/extract-theme-hook` |

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body> (optional)
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

**Examples**:
- `feat(radar): add category filter to blue ocean scan`
- `fix(auth): handle expired JWT token gracefully`
- `docs: update environment variable table`

## Code Style

This project does not use an automated linter. Follow these conventions:

### General

- Match the existing code style in the file you are editing
- Do not reformat or restyle code outside your change scope
- Remove unused imports and variables you introduce

### Frontend (TypeScript / React)

- Use TypeScript strict mode; avoid `any` and `@ts-ignore`
- Functional components with explicit props interfaces
- Use `const` for variables and arrow functions
- Follow existing Tailwind class ordering in the file

### Backend (Python / FastAPI)

- Python 3.11+ syntax
- Use `async/await` throughout the service and CRUD layers
- Pydantic v2 schemas for request/response validation
- Follow existing naming: routers -> services -> CRUD

## Pull Request Guidelines

1. **One PR per concern** -- do not mix unrelated changes
2. **Describe the change** -- what and why, not just how
3. **Link related issues** -- `Fixes #123` or `Related to #456`
4. **Verify locally** before submitting:
   - Backend: `cd backend && python -m pytest` (if tests exist for your change)
   - Frontend: `cd frontend && npm run build` (must pass without errors)
5. **Keep PRs small** -- under 400 lines of diff is ideal

## Issue Template

When filing an issue, include:

1. **Description** -- What happened vs. what you expected
2. **Steps to reproduce** -- Minimal, ordered list
3. **Environment** -- OS, Node/Python version, Docker version
4. **Screenshots / logs** -- If applicable

## License Agreement

By submitting a contribution to YouTube Compass, you agree that your contribution will be licensed under the [Business Source License 1.1](./LICENSE) under the same terms as the rest of the project. You confirm that you have the right to grant this license.
