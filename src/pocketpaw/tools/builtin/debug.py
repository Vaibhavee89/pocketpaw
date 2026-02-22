# Code Debugging Agent tool — orchestrates test execution, error analysis, and auto-fix.
# Created: 2026-02-22
# Part of Developer AI Copilot

import logging
import re
from pathlib import Path
from typing import Any

from pocketpaw.config import Settings
from pocketpaw.llm.router import LLMRouter
from pocketpaw.tools.builtin.filesystem import ReadFileTool
from pocketpaw.tools.builtin.shell import ShellTool
from pocketpaw.tools.protocol import BaseTool

logger = logging.getLogger(__name__)

# Depth levels: controls error analysis depth
_DEPTH_LIMITS = {
    "quick": {"max_errors": 3, "context_lines": 5},
    "standard": {"max_errors": 10, "context_lines": 10},
    "deep": {"max_errors": 20, "context_lines": 20},
}


class DebugCodeTool(BaseTool):
    """Code debugging agent: runs tests, analyzes errors, suggests fixes."""

    @property
    def name(self) -> str:
        return "debug_code"

    @property
    def description(self) -> str:
        return (
            "Run tests and analyze failures with LLM-powered debugging. "
            "Executes test command, parses errors (pytest/jest/go), gathers code context, "
            "and produces debug report with root cause analysis and fix suggestions. "
            "Optionally applies fixes automatically and re-runs tests. "
            "Depth levels: quick (3 errors), standard (10), deep (20)."
        )

    @property
    def trust_level(self) -> str:
        return "high"  # Executes shell commands

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "test_command": {
                    "type": "string",
                    "description": (
                        "Command to run tests (e.g., 'pytest', 'npm test', 'go test ./...')"
                    ),
                },
                "project_path": {
                    "type": "string",
                    "description": "Working directory for tests (default: current directory)",
                    "default": ".",
                },
                "depth": {
                    "type": "string",
                    "description": (
                        "Analysis depth: 'quick', 'standard', or 'deep' (default: standard)"
                    ),
                    "enum": ["quick", "standard", "deep"],
                    "default": "standard",
                },
                "auto_fix": {
                    "type": "boolean",
                    "description": (
                        "Attempt to apply suggested fixes automatically (default: false)"
                    ),
                    "default": False,
                },
            },
            "required": ["test_command"],
        }

    async def execute(
        self,
        test_command: str,
        project_path: str = ".",
        depth: str = "standard",
        auto_fix: bool = False,
    ) -> str:
        limits = _DEPTH_LIMITS.get(depth, _DEPTH_LIMITS["standard"])
        project_dir = Path(project_path).expanduser().resolve()

        if not project_dir.exists():
            return self._error(f"Project path not found: {project_path}")

        try:
            # Step 1: Run tests
            logger.info("Running tests: %s in %s", test_command, project_dir)
            shell = ShellTool(working_dir=str(project_dir))
            test_output = await shell.execute(command=test_command)

            # Check if tests passed
            if self._tests_passed(test_output):
                return f"✅ **All tests passed!**\n\n```\n{test_output[:1000]}\n```"

            # Step 2: Parse errors
            logger.info("Parsing test errors")
            errors = self._parse_test_output(test_output, limits["max_errors"])

            if not errors:
                return (
                    f"⚠️ **Tests failed but no errors detected**\n\n"
                    f"```\n{test_output[:2000]}\n```"
                )

            # Step 3: Gather file contexts
            logger.info("Gathering file contexts for %d errors", len(errors))
            contexts = await self._gather_file_contexts(
                errors, project_dir, limits["context_lines"]
            )

            # Step 4: LLM Analysis
            logger.info("Analyzing errors with LLM")
            analysis = await self._analyze_with_llm(
                test_command, test_output, errors, contexts
            )

            # Step 5: Format report
            report = self._format_debug_report(errors, analysis, test_output)

            # Step 6: Auto-fix if requested
            if auto_fix:
                logger.info("Attempting auto-fix")
                fix_result = await self._apply_fixes(analysis, project_dir, test_command)
                report += f"\n\n---\n\n{fix_result}"

            return report

        except Exception as e:
            logger.exception("Debug tool failed")
            return self._error(f"Debug failed: {e}")

    def _tests_passed(self, output: str) -> bool:
        """Check if tests passed based on common success indicators."""
        success_patterns = [
            r"(\d+) passed",  # pytest
            r"✓ .* \(\d+ms\)",  # jest
            r"PASS.*\d+ tests?",  # go test
            r"OK \(\d+ tests?\)",  # generic
        ]
        fail_patterns = [
            r"(\d+) failed",
            r"FAIL",
            r"✗",
            r"Error:",
        ]

        # Check for failure indicators first
        for pattern in fail_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return False

        # Then check for success indicators
        for pattern in success_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return True

        # If exit code indicates success
        if "Exit code: 0" in output or "exit code: 0" in output.lower():
            return True

        return False

    def _parse_test_output(self, output: str, max_errors: int) -> list[dict[str, Any]]:
        """Parse test output to extract error information."""
        errors = []

        # Try pytest format first
        errors.extend(self._parse_pytest(output))

        # Try jest format
        if not errors:
            errors.extend(self._parse_jest(output))

        # Try go test format
        if not errors:
            errors.extend(self._parse_go_test(output))

        # Generic fallback: look for FAILED/ERROR lines
        if not errors:
            errors.extend(self._parse_generic(output))

        return errors[:max_errors]

    def _parse_pytest(self, output: str) -> list[dict[str, Any]]:
        """Parse pytest output format."""
        errors = []
        # Pattern: test_file.py::test_name FAILED
        # Followed by file:line and error message
        failed_pattern = re.compile(r"(.+?)::(.+?) (FAILED|ERROR)")
        location_pattern = re.compile(r"(.+?):(\d+):")

        lines = output.split("\n")
        i = 0
        while i < len(lines):
            match = failed_pattern.search(lines[i])
            if match:
                file_path = match.group(1).strip()
                test_name = match.group(2).strip()

                # Look ahead for error details
                error_msg = []
                line_num = None

                for j in range(i + 1, min(i + 20, len(lines))):
                    loc_match = location_pattern.search(lines[j])
                    if loc_match and not line_num:
                        line_num = int(loc_match.group(2))

                    if lines[j].strip() and not lines[j].startswith("_"):
                        error_msg.append(lines[j].strip())

                    if "AssertionError" in lines[j] or "Error:" in lines[j]:
                        break

                errors.append(
                    {
                        "file": file_path,
                        "line": line_num,
                        "test": test_name,
                        "message": "\n".join(error_msg[:5]),
                        "framework": "pytest",
                    }
                )

            i += 1

        return errors

    def _parse_jest(self, output: str) -> list[dict[str, Any]]:
        """Parse jest output format."""
        errors = []
        # Pattern: ● test_name
        # at Object.<anonymous> (file:line:col)
        test_pattern = re.compile(r"● (.+)")
        location_pattern = re.compile(r"at .+ \((.+):(\d+):(\d+)\)")

        lines = output.split("\n")
        i = 0
        while i < len(lines):
            match = test_pattern.search(lines[i])
            if match:
                test_name = match.group(1).strip()
                error_msg = []
                file_path = None
                line_num = None

                # Look ahead for location and error
                for j in range(i + 1, min(i + 15, len(lines))):
                    loc_match = location_pattern.search(lines[j])
                    if loc_match:
                        file_path = loc_match.group(1)
                        line_num = int(loc_match.group(2))

                    if lines[j].strip():
                        error_msg.append(lines[j].strip())

                if file_path:
                    errors.append(
                        {
                            "file": file_path,
                            "line": line_num,
                            "test": test_name,
                            "message": "\n".join(error_msg[:5]),
                            "framework": "jest",
                        }
                    )

            i += 1

        return errors

    def _parse_go_test(self, output: str) -> list[dict[str, Any]]:
        """Parse go test output format."""
        errors = []
        # Pattern: --- FAIL: TestName (0.00s)
        #    file_test.go:123: error message
        fail_pattern = re.compile(r"--- FAIL: (\w+) ")
        location_pattern = re.compile(r"(.+_test\.go):(\d+): (.+)")

        lines = output.split("\n")
        i = 0
        while i < len(lines):
            match = fail_pattern.search(lines[i])
            if match:
                test_name = match.group(1)

                # Look ahead for location and error
                for j in range(i + 1, min(i + 10, len(lines))):
                    loc_match = location_pattern.search(lines[j])
                    if loc_match:
                        errors.append(
                            {
                                "file": loc_match.group(1),
                                "line": int(loc_match.group(2)),
                                "test": test_name,
                                "message": loc_match.group(3),
                                "framework": "go",
                            }
                        )
                        break

            i += 1

        return errors

    def _parse_generic(self, output: str) -> list[dict[str, Any]]:
        """Generic parser for unrecognized test frameworks."""
        errors = []
        lines = output.split("\n")

        for line in lines:
            if any(
                keyword in line.upper() for keyword in ["FAILED", "ERROR", "FAIL:", "✗"]
            ):
                errors.append(
                    {
                        "file": None,
                        "line": None,
                        "test": "unknown",
                        "message": line.strip(),
                        "framework": "unknown",
                    }
                )

        return errors[:5]

    async def _gather_file_contexts(
        self, errors: list[dict], project_dir: Path, context_lines: int
    ) -> dict[str, str]:
        """Gather source code context around error locations."""
        contexts = {}
        read_tool = ReadFileTool()

        for error in errors:
            if not error.get("file"):
                continue

            file_path = project_dir / error["file"]
            if not file_path.exists():
                # Try as absolute path
                file_path = Path(error["file"])

            if not file_path.exists():
                continue

            try:
                content = await read_tool.execute(path=str(file_path))
                if content.startswith("Error:"):
                    continue

                # Extract relevant lines if line number available
                if error.get("line"):
                    lines = content.split("\n")
                    start = max(0, error["line"] - context_lines - 1)
                    end = min(len(lines), error["line"] + context_lines)
                    context = "\n".join(
                        f"{i + 1:4d} | {line}" for i, line in enumerate(lines[start:end], start)
                    )
                else:
                    # Include first 50 lines if no line number
                    lines = content.split("\n")[:50]
                    context = "\n".join(f"{i + 1:4d} | {line}" for i, line in enumerate(lines))

                contexts[str(file_path)] = context

            except Exception as e:
                logger.warning("Failed to read context for %s: %s", file_path, e)

        return contexts

    async def _analyze_with_llm(
        self,
        test_command: str,
        test_output: str,
        errors: list[dict],
        contexts: dict[str, str],
    ) -> str:
        """Use LLM to analyze errors and suggest fixes."""
        try:
            settings = Settings.load()
            router = LLMRouter(settings)

            # Build analysis prompt
            prompt = f"""Analyze these test failures and provide debugging guidance.

**Test Command:** `{test_command}`

**Test Output:**
```
{test_output[:3000]}
```

**Errors Detected:** {len(errors)}
"""

            for i, error in enumerate(errors[:5], 1):
                prompt += f"\n\n**Error {i}:**\n"
                prompt += f"- File: {error.get('file', 'unknown')}\n"
                prompt += f"- Line: {error.get('line', 'unknown')}\n"
                prompt += f"- Test: {error.get('test', 'unknown')}\n"
                prompt += f"- Message: {error.get('message', 'No message')[:200]}\n"

                # Add source context if available
                file_key = str(Path(error.get("file", "")))
                if file_key in contexts:
                    prompt += f"\n**Source Context:**\n```\n{contexts[file_key][:1000]}\n```\n"

            prompt += """

Please provide:
1. **Root Cause**: What's causing each failure?
2. **Suggested Fix**: Specific code changes to fix each issue
3. **Reasoning**: Why these fixes should work

Format your response with clear sections."""

            analysis = await router.chat(prompt)
            return analysis

        except Exception as e:
            logger.warning("LLM analysis failed: %s", e)
            return "LLM analysis unavailable. Review the errors manually."

    def _format_debug_report(
        self, errors: list[dict], analysis: str, test_output: str
    ) -> str:
        """Format the debug report for display."""
        report = "# 🐛 Debug Report\n\n"

        # Summary
        report += f"**Errors Found:** {len(errors)}\n\n"

        # Error details
        report += "## Errors\n\n"
        for i, error in enumerate(errors, 1):
            report += f"### {i}. {error.get('test', 'Unknown Test')}\n\n"
            report += f"- **File:** `{error.get('file', 'unknown')}`\n"
            if error.get("line"):
                report += f"- **Line:** {error['line']}\n"
            report += f"- **Framework:** {error.get('framework', 'unknown')}\n"
            report += f"- **Message:**\n```\n{error.get('message', 'No message')[:300]}\n```\n\n"

        # LLM Analysis
        report += "## Analysis\n\n"
        report += analysis
        report += "\n\n"

        # Raw output (truncated)
        report += "## Raw Test Output\n\n"
        report += f"```\n{test_output[:2000]}\n"
        if len(test_output) > 2000:
            report += "...(truncated)\n"
        report += "```\n"

        return report

    async def _apply_fixes(
        self, analysis: str, project_dir: Path, test_command: str
    ) -> str:
        """Attempt to apply suggested fixes (experimental)."""
        # For now, delegate complex multi-file fixes to Claude Code
        try:
            from pocketpaw.tools.builtin.delegate import DelegateToClaudeCodeTool

            delegate = DelegateToClaudeCodeTool()

            # Check if available
            from pocketpaw.agents.delegation import ExternalAgentDelegate

            if not ExternalAgentDelegate.is_available("claude"):
                return (
                    "⚠️ **Auto-fix requires Claude Code CLI**\n\n"
                    "Install with: `npm install -g @anthropic-ai/claude-code`\n\n"
                    "Manual fix recommended: Review the analysis above and apply changes manually."
                )

            # Delegate fix task
            task = f"""Fix the test failures in {project_dir}.

Test command: {test_command}

Analysis:
{analysis[:2000]}

Instructions:
1. Apply the suggested fixes from the analysis
2. Re-run the tests to verify
3. Report the results
"""

            result = await delegate.execute(task=task, timeout=180)

            if result.startswith("Error:"):
                return f"⚠️ **Auto-fix failed**\n\n{result}"

            return f"✅ **Auto-fix attempted**\n\n{result}"

        except Exception as e:
            logger.warning("Auto-fix failed: %s", e)
            return (
                f"⚠️ **Auto-fix error:** {e}\n\n"
                "Manual fix recommended: Review the analysis above."
            )
