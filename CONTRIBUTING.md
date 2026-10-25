# Contributing to Raptor Esports Portal

Thank you for your interest in contributing to the Raptor Esports Portal! We welcome contributions from developers, designers, analysts, and esports enthusiasts. This guide provides instructions on how to set up your development environment, run tests, adhere to coding conventions, and submit contributions.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Project Overview](#project-overview)
3. [Development Environment Setup](#development-environment-setup)
4. [Running the Application](#running-the-application)
5. [Running the Test Suite](#running-the-test-suite)
6. [Branching & Commit Conventions](#branching--commit-conventions)
7. [Code Quality & Architecture Standards](#code-quality--architecture-standards)
8. [Submitting Pull Requests](#submitting-pull-requests)

---

## Code of Conduct

All contributors and maintainers are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to uphold a welcoming, respectful, and harassment-free community.

Instances of abusive, harassing, or otherwise unacceptable behavior can be reported to the governance team at `governance@raptor.local`.

---

## Project Overview

The Raptor Esports Portal is a high-performance web platform designed for competitive esports organizations. It provides:
* **Public Showcase**: Dynamic landing portal featuring team lineups, tournament schedules, interactive roster scrub stage, and video highlights.
* **Workspace Console**: A multi-role administration dashboard for managing teams, rosters, matches, tournaments, performance metrics, and organization finances.
* **Granular RBAC**: 5 distinct roles (`Admin`, `Manager`, `Coach`, `Analyst`, `Player`) with 29 atomic permissions and resource-scoped access.
* **OpenAI-Compatible AI Assistant**: Context-aware assistant supporting OpenAI endpoints, ByNara auto-routing, automatic multi-model fallback, and deterministic local rules.
* **Zero Runtime Dependencies**: Powered entirely by the Python standard library and vanilla frontend technologies.

---

## Development Environment Setup

### Prerequisites
* **Python**: Python 3.10 or higher.
* **Git**: Installed and configured on your system.
* **Web Browser**: Any modern browser (Google Chrome, Mozilla Firefox, Microsoft Edge, or Apple Safari).
* **Package Dependencies**: None. This project has zero external pip package requirements.

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/raptoresports/raptor-portal.git
   cd raptor-portal
   ```

2. **Verify Python version**:
   ```bash
   python --version
   ```
   Confirm the output indicates Python 3.10.0 or later.

3. **Optional AI Configuration**:
   If you wish to test the live AI assistant using an OpenAI or ByNara API key, create a text file named `API key.txt` in the repository root formatted as:
   ```text
   sk-your-api-key-here
   primary-model-name
   fallback-model-name
   https://api.openai.com/v1
   ```
   *(Note: The portal will automatically fall back to deterministic local responses if this file is omitted or if upstream APIs are unreachable).*

---

## Running the Application

Start the local server using standard Python:

```bash
python server.py
```

The application initializes the SQLite database at `data/raptor.sqlite3` on first run, applies any pending migrations, seeds initial demo data, and begins serving requests:

* **Default URL**: `http://127.0.0.1:5050`
* **Default Port**: `5050`
* **Network Binding**: Loopback interface `127.0.0.1`

### Default Demo Accounts

The database seeds 5 default test accounts. All demo accounts use the default password `Raptor@2026`:

| Role | Email | Password | Access Scope |
|------|-------|----------|--------------|
| Admin | `admin@raptor.local` | `Raptor@2026` | Full platform control and user management |
| Manager | `manager@raptor.local` | `Raptor@2026` | Global entity management, coaching assignments, finances |
| Coach | `coach@raptor.local` | `Raptor@2026` | Scoped to assigned teams (Team 1 BGMI by default) |
| Analyst | `analyst@raptor.local` | `Raptor@2026` | Scoped to assigned teams, analytics and reports only |
| Player | `player@raptor.local` | `Raptor@2026` | Scoped to personal roster record and team |

---

## Running the Test Suite

Before submitting any code changes, verify that the complete test suite passes cleanly:

```bash
python -m unittest discover -s tests -v
```

All 48 unit tests must pass with status `OK`:
* `tests/test_rbac.py`: Validates role configurations, permission matrix, and resource scopes.
* `tests/test_rbac_database.py`: Tests SQLite schema initialization, table migrations, and constraint enforcement.
* `tests/test_rbac_routes.py`: Verifies route authorization, authentication checks, and CSRF token enforcement.
* `tests/test_player_avatars.py`: Validates avatar assignment, seeding, and update idempotency.
* `tests/test_chatbot.py`: Covers AI assistant integration, ByNara routing, multi-model fallback, and rate limiting.

To execute a single test file during development:

```bash
python -m unittest tests.test_rbac -v
```

---

## Branching & Commit Conventions

### Branch Naming Conventions

Create focused branches originating from the main branch. Use prefix categories:

* `feature/<short-description>`: New portal capability or feature enhancement (e.g., `feature/scrim-scheduler`).
* `fix/<short-description>`: Bug fix or regression resolution (e.g., `fix/session-expiry-edgecase`).
* `docs/<short-description>`: Documentation, guides, or specifications (e.g., `docs/api-reference`).
* `refactor/<short-description>`: Code restructuring without functional change (e.g., `refactor/db-connection-cleanup`).
* `test/<short-description>`: New tests or test suite improvements (e.g., `test/rate-limiter-concurrency`).

### Commit Message Conventions

We follow the [Conventional Commits v1.0.0](https://www.conventionalcommits.org/) standard. Structure commit messages as follows:

```text
<type>(<optional-scope>): <concise-description-in-imperative-mood>

[optional body explaining motivation and technical decisions]
```

#### Commit Types
* `feat`: A new user-facing or API feature.
* `fix`: A bug fix for existing behavior.
* `docs`: Documentation-only additions or modifications.
* `style`: Code style changes that do not affect logic (formatting, whitespace).
* `refactor`: Code changes that neither fix a bug nor add a feature.
* `perf`: Performance improvements.
* `test`: Adding or correcting tests.
* `chore`: Maintenance tasks, tooling updates, or repository asset changes.

#### Examples
* `feat(auth): add persistent remember-me token handling`
* `fix(server): handle trailing slash in entity routes gracefully`
* `docs(readme): add system architecture mermaid diagram`
* `test(chatbot): assert sliding-window prune on inactive ip addresses`

---

## Code Quality & Architecture Standards

### 1. Python Architecture & Standards
* **Standard Library Only**: Do not introduce third-party pip dependencies. All functionality must rely strictly on modules available in standard Python 3.10+.
* **PEP 8 Compliance**: Follow standard Python conventions (4-space indentation, snake_case functions/variables, PascalCase classes, UPPER_SNAKE constants).
* **Concurrency & Thread Safety**: Handlers run concurrently on `ThreadingHTTPServer`. Ensure any shared state uses locks (`threading.Lock`) and database queries open scoped connections via `db.get_connection()`.
* **Database Practices**: Always use parameterized queries (`?` placeholders). Never format raw values into SQL strings. Maintain foreign key constraints and write migration logic in `db.py` when modifying tables.

### 2. Frontend Standards
* **Vanilla Stack**: Plain HTML5, modular CSS stylesheets located in `assets/css/`, and ES6 JavaScript in `assets/js/`.
* **Design System**: Respect dark palette tokens, responsive breakpoints (mobile, tablet, desktop), and custom typography (General Sans, Raptor Valorant, Sayonara / Raptor Stencil).
* **Client Security**: Transmit `X-CSRF-Token` headers on all mutating (`POST`, `PUT`, `DELETE`) fetch requests.

### 3. Security Requirements
* Never commit secrets, passwords, or production API keys to git.
* Keep `API key.txt` and `data/*.sqlite3` listed in `.gitignore`.
* Enforce RBAC permissions at the server handler layer rather than relying exclusively on UI visibility.

---

## Submitting Pull Requests

1. **Rebase against main**: Ensure your branch is up to date with the latest `main` branch:
   ```bash
   git fetch origin
   git rebase origin/main
   ```
2. **Run tests**: Confirm all 48 tests pass:
   ```bash
   python -m unittest discover -s tests -v
   ```
3. **Verify documentation**: Check that any changed features or APIs are accurately documented.
4. **Open a Pull Request**: Submit your PR targeting `main`. Complete all checklist items outlined in the pull request template.
5. **Review & Merge**: Maintainers will review your submission and provide feedback. Once approved, commits are rebased or squash-merged into `main`.
