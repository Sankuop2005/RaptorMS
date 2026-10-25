#!/usr/bin/env python3
"""
Raptor Esports Portal — Documentation & Governance Verification Script
=======================================================================
Verifies the completeness, structural integrity, and accuracy of all
governance assets, technical documentation, issue templates, and configuration
references in accordance with Milestone M4 acceptance criteria.

Standard Library only: sys, os, re, pathlib
Exit code 0 on all checks passing, non-zero on any failure.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Configure stdout to utf-8 if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ANSI Color formatting
USE_COLOR = sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def green(text: str) -> str:
    return _c(text, "32")

def red(text: str) -> str:
    return _c(text, "31")

def yellow(text: str) -> str:
    return _c(text, "33")

def cyan(text: str) -> str:
    return _c(text, "36")

def bold(text: str) -> str:
    return _c(text, "1")

PASS_MARK = "[PASS]"
FAIL_MARK = "[FAIL]"


# Target 12 required documentation files
REQUIRED_DOCS: List[str] = [
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/API.md",
    "docs/DESIGN_SYSTEM.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/pull_request_template.md",
]

# Required sections for each document
REQUIRED_SECTIONS: Dict[str, List[str]] = {
    "LICENSE": [
        "MIT License",
        "Copyright (c) 2026 Raptor Esports",
    ],
    "CONTRIBUTING.md": [
        "Code of Conduct",
        "Project Overview",
        "Development Environment Setup",
        "Running the Application",
        "Running the Test Suite",
        "Branching & Commit Conventions",
        "Code Quality & Architecture Standards",
        "Submitting Pull Requests",
    ],
    "CODE_OF_CONDUCT.md": [
        "Our Pledge",
        "Our Standards",
        "Enforcement Responsibilities",
        "Scope",
        "Enforcement",
        "Enforcement Guidelines",
        "Attribution",
    ],
    "SECURITY.md": [
        "Supported Versions",
        "Reporting a Vulnerability",
        "Service Level Agreements (SLA) & Timeline",
        "Core Security Architecture & Safeguards",
        "Safe Harbor & Responsible Disclosure",
    ],
    "CHANGELOG.md": [
        "1.0.0",
        "Added",
        "Changed",
        "Fixed",
        "Security",
    ],
    "README.md": [
        "Executive Summary & Feature Highlights",
        "System Architecture",
        "Role-Based Access Control (RBAC)",
        "REST API Reference",
        "Configuration & Environment Variables",
        "Local Development & Verification",
        "Production Deployment Guide",
        "Repository Structure",
        "Governance & Documentation Links",
    ],
    "docs/ARCHITECTURE.md": [
        "System Overview & Component Topology",
        "HTTP & Routing Engine",
        "Session & Security Subsystem",
        "SQLite Concurrency Model & Data Architecture",
        "AI Assistant Gateway",
    ],
    "docs/API.md": [
        "Global API Architecture & Protocol Invariants",
        "Authentication & Session Endpoints",
        "Chat & Assistant Endpoints",
        "Analytics & Dashboard Endpoints",
        "Staff & Coach Assignment Endpoints",
        "Generic Entity CRUD Engine",
    ],
    "docs/DESIGN_SYSTEM.md": [
        "Design Philosophy",
        "CSS Architecture & Modular Organization",
        "Color Palette & Design Tokens",
        "Typography Hierarchy",
        "UI Component Specifications",
        "Responsive Breakpoints",
    ],
    ".github/ISSUE_TEMPLATE/bug_report.md": [
        "Description",
        "Steps to Reproduce",
        "Expected Behavior",
        "Observed Behavior & Error Messages",
        "Environment Information",
        "Additional Context",
    ],
    ".github/ISSUE_TEMPLATE/feature_request.md": [
        "Summary",
        "Problem Statement",
        "Proposed Solution",
        "Alternative Approaches",
        "Role & RBAC Impact",
        "Technical Considerations",
        "Additional Context",
    ],
    ".github/pull_request_template.md": [
        "Summary of Changes",
        "Motivation & Context",
        "Type of Change",
        "RBAC & Security Impact",
        "Testing & Verification",
        "Contributor Checklist",
    ],
}

# Regex patterns that indicate unfilled placeholder tokens or bracketed templates
PLACEHOLDER_PATTERNS: List[Tuple[str, str]] = [
    (r"\bTODO\b", "TODO token"),
    (r"\bTBD\b", "TBD token"),
    (r"\bFIXME\b", "FIXME token"),
    (r"\bXXX\b", "XXX token"),
    (r"\[insert[^\]]*\]", "Bracketed insert template"),
    (r"\[your[^\]]*\]", "Bracketed 'your ...' template"),
    (r"\[email\]", "Bracketed email placeholder"),
    (r"\[name\]", "Bracketed name placeholder"),
    (r"\[username\]", "Bracketed username placeholder"),
    (r"\[placeholder[^\]]*\]", "Bracketed placeholder template"),
    (r"\[replace[^\]]*\]", "Bracketed replace template"),
    (r"<insert[^>]*>", "Angle-bracketed insert template"),
    (r"<your[^>]*>", "Angle-bracketed 'your ...' template"),
    (r"<placeholder[^>]*>", "Angle-bracketed placeholder template"),
    (r"\{\{insert[^}]*\}\}", "Jinja/Mustache insert placeholder"),
    (r"\{\{your[^}]*\}\}", "Jinja/Mustache 'your ...' placeholder"),
    (r"\{\{placeholder[^}]*\}\}", "Jinja/Mustache placeholder template"),
]

# Issue templates with required YAML frontmatter
ISSUE_TEMPLATES: List[str] = [
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
]

REQUIRED_YAML_KEYS: List[str] = ["name", "about", "title", "labels"]


def find_repo_root() -> Path:
    """Locate workspace root from current script path or working directory."""
    candidate = Path(__file__).resolve().parent.parent
    if (candidate / "server.py").is_file():
        return candidate
    cwd = Path.cwd().resolve()
    if (cwd / "server.py").is_file():
        return cwd
    return candidate


def parse_yaml_frontmatter(content: str) -> Optional[Dict[str, object]]:
    """
    Parses simple YAML frontmatter delimited by '---' at file start.
    Standard library implementation supporting string scalars and simple lists.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    fm_lines: List[str] = []
    found_end = False
    for line in lines[1:]:
        if line.strip() == "---":
            found_end = True
            break
        fm_lines.append(line)

    if not found_end:
        return None

    parsed: Dict[str, object] = {}
    current_key: Optional[str] = None

    for raw_line in fm_lines:
        line = raw_line.rstrip()
        if not line or line.startswith("#"):
            continue

        # Check for list element: "  - item"
        list_match = re.match(r"^\s*-\s+(.*)$", line)
        if list_match and current_key:
            val = list_match.group(1).strip().strip("\"'")
            if not isinstance(parsed.get(current_key), list):
                parsed[current_key] = []
            parsed[current_key].append(val)  # type: ignore[union-attr]
            continue

        # Check for key: value
        kv_match = re.match(r"^([a-zA-Z0-9_-]+)\s*:\s*(.*)$", line)
        if kv_match:
            key = kv_match.group(1).strip()
            val_str = kv_match.group(2).strip()
            current_key = key
            if val_str == "":
                parsed[key] = []
            else:
                if (val_str.startswith('"') and val_str.endswith('"')) or (
                    val_str.startswith("'") and val_str.endswith("'")
                ):
                    val_str = val_str[1:-1]
                parsed[key] = val_str
            continue

    return parsed


class DocVerifier:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0
        self.failures: List[str] = []

    def record_pass(self, description: str) -> None:
        self.total_checks += 1
        self.passed_checks += 1
        print(f"  {green(PASS_MARK)} {description}")

    def record_fail(self, description: str, error_detail: str) -> None:
        self.total_checks += 1
        self.failed_checks += 1
        msg = f"  {red(FAIL_MARK)} {description}: {error_detail}"
        print(msg)
        self.failures.append(f"{description} -> {error_detail}")

    def verify_file_existence_and_size(self) -> None:
        print(cyan(bold("\n[1/5] Verifying Document Existence and Non-Emptiness")))
        for rel_path in REQUIRED_DOCS:
            doc_path = self.root / rel_path
            if not doc_path.exists():
                self.record_fail(rel_path, "File does not exist")
                continue
            if not doc_path.is_file():
                self.record_fail(rel_path, "Path exists but is not a file")
                continue
            size = doc_path.stat().st_size
            if size == 0:
                self.record_fail(rel_path, "File is empty (0 bytes)")
                continue

            content = doc_path.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                self.record_fail(rel_path, "File contains only whitespace")
                continue

            self.record_pass(f"{rel_path} ({size:,} bytes)")

    def verify_required_sections(self) -> None:
        print(cyan(bold("\n[2/5] Verifying Required Sections in Documents")))
        for rel_path, sections in REQUIRED_SECTIONS.items():
            doc_path = self.root / rel_path
            if not doc_path.is_file():
                continue

            content = doc_path.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()

            for section in sections:
                desc = f"{rel_path} -> section '{section}'"
                if section.lower() in content_lower:
                    self.record_pass(desc)
                else:
                    self.record_fail(desc, f"Required section '{section}' not found in document")

    def verify_no_placeholder_tokens(self) -> None:
        print(cyan(bold("\n[3/5] Scanning for Placeholder Tokens & Bracketed Templates")))
        for rel_path in REQUIRED_DOCS:
            doc_path = self.root / rel_path
            if not doc_path.is_file():
                continue

            content = doc_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            found_placeholders: List[str] = []
            for line_idx, line in enumerate(lines, start=1):
                for pattern, name in PLACEHOLDER_PATTERNS:
                    matches = list(re.finditer(pattern, line, re.IGNORECASE))
                    for m in matches:
                        found_placeholders.append(
                            f"L{line_idx}: matched '{m.group(0)}' ({name})"
                        )

            if found_placeholders:
                self.record_fail(
                    f"{rel_path} zero-placeholder check",
                    f"Found {len(found_placeholders)} placeholder(s): "
                    + "; ".join(found_placeholders[:5]),
                )
            else:
                self.record_pass(f"{rel_path} contains 0 placeholder tokens")

    def verify_yaml_frontmatter(self) -> None:
        print(cyan(bold("\n[4/5] Verifying Issue Template YAML Frontmatter")))
        for rel_path in ISSUE_TEMPLATES:
            doc_path = self.root / rel_path
            if not doc_path.is_file():
                self.record_fail(rel_path, "Issue template not found")
                continue

            content = doc_path.read_text(encoding="utf-8", errors="replace")
            frontmatter = parse_yaml_frontmatter(content)
            if frontmatter is None:
                self.record_fail(rel_path, "Missing or malformed YAML frontmatter between '---' markers")
                continue

            missing_keys = [k for k in REQUIRED_YAML_KEYS if k not in frontmatter]
            if missing_keys:
                self.record_fail(
                    rel_path,
                    f"YAML frontmatter missing required keys: {', '.join(missing_keys)}",
                )
                continue

            # Validate non-emptiness of required fields
            empty_keys = []
            for k in ["name", "about", "title"]:
                val = frontmatter.get(k)
                if not isinstance(val, str) or not val.strip():
                    empty_keys.append(k)

            labels = frontmatter.get("labels")
            if not isinstance(labels, list) or len(labels) == 0:
                empty_keys.append("labels (must be non-empty list)")

            if empty_keys:
                self.record_fail(
                    rel_path,
                    f"YAML frontmatter contains empty/invalid values for: {', '.join(empty_keys)}",
                )
            else:
                self.record_pass(
                    f"{rel_path} valid YAML frontmatter (name='{frontmatter['name']}', labels={labels})"
                )

    def verify_port_and_demo_credentials(self) -> None:
        print(cyan(bold("\n[5/5] Verifying Port 5050 & Demo Credentials in README and CONTRIBUTING")))
        targets = ["README.md", "CONTRIBUTING.md"]
        required_literals = [
            ("5050", "Port 5050 specification"),
            ("admin@raptor.local", "Admin email 'admin@raptor.local'"),
            ("Raptor@2026", "Default demo password 'Raptor@2026'"),
        ]

        for rel_path in targets:
            doc_path = self.root / rel_path
            if not doc_path.is_file():
                self.record_fail(rel_path, "File not found")
                continue

            content = doc_path.read_text(encoding="utf-8", errors="replace")
            for literal, label in required_literals:
                desc = f"{rel_path} -> {label}"
                if literal in content:
                    self.record_pass(desc)
                else:
                    self.record_fail(desc, f"Literal '{literal}' not found in {rel_path}")

    def run(self) -> int:
        print(bold(f"\n========================================================"))
        print(bold(f"  Raptor Esports Portal -- Documentation Verification"))
        print(bold(f"========================================================"))
        print(f"Workspace Root: {self.root}\n")

        self.verify_file_existence_and_size()
        self.verify_required_sections()
        self.verify_no_placeholder_tokens()
        self.verify_yaml_frontmatter()
        self.verify_port_and_demo_credentials()

        print(bold(f"\n--------------------------------------------------------"))
        print(bold(f"  Verification Summary"))
        print(bold(f"--------------------------------------------------------"))
        print(f"Total Checks  : {self.total_checks}")
        print(f"Passed Checks : {green(str(self.passed_checks))}")
        print(f"Failed Checks : {red(str(self.failed_checks)) if self.failed_checks else '0'}")

        if self.failed_checks == 0:
            print(green(bold("\n[RESULT: SUCCESS] All documentation checks passed cleanly.\n")))
            return 0
        else:
            print(red(bold(f"\n[RESULT: FAILED] {self.failed_checks} check(s) failed:\n")))
            for failure in self.failures:
                print(f"  - {red(failure)}")
            print()
            return 1


def main() -> None:
    root = find_repo_root()
    verifier = DocVerifier(root)
    exit_code = verifier.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
