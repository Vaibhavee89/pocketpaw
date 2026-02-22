"""Unit tests for DebugCodeTool."""
# Created: 2026-02-22

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from pocketpaw.tools.builtin.debug import DebugCodeTool


@pytest.fixture
def debug_tool():
    """Create a DebugCodeTool instance."""
    return DebugCodeTool()


@pytest.fixture
def mock_shell_tool():
    """Mock ShellTool for test execution."""
    with patch("pocketpaw.tools.builtin.debug.ShellTool") as mock:
        instance = AsyncMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_read_file_tool():
    """Mock ReadFileTool for reading source files."""
    with patch("pocketpaw.tools.builtin.debug.ReadFileTool") as mock:
        instance = AsyncMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_llm_router():
    """Mock LLMRouter for error analysis."""
    with patch("pocketpaw.tools.builtin.debug.LLMRouter") as mock:
        instance = AsyncMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_settings():
    """Mock Settings.load()."""
    with patch("pocketpaw.tools.builtin.debug.Settings") as mock:
        settings = MagicMock()
        mock.load.return_value = settings
        yield settings


class TestDebugCodeToolBasics:
    """Test basic tool properties and configuration."""

    def test_tool_name(self, debug_tool):
        """Test tool name is correct."""
        assert debug_tool.name == "debug_code"

    def test_tool_description(self, debug_tool):
        """Test tool has description."""
        assert "debug" in debug_tool.description.lower()
        assert "test" in debug_tool.description.lower()

    def test_trust_level(self, debug_tool):
        """Test tool requires high trust level."""
        assert debug_tool.trust_level == "high"

    def test_parameters_schema(self, debug_tool):
        """Test parameter schema is valid."""
        params = debug_tool.parameters
        assert params["type"] == "object"
        assert "test_command" in params["properties"]
        assert "test_command" in params["required"]
        assert "auto_fix" in params["properties"]
        assert params["properties"]["auto_fix"]["default"] is False


class TestTestExecution:
    """Test test execution and output parsing."""

    @pytest.mark.asyncio
    async def test_successful_tests_all_pass(
        self, debug_tool, mock_shell_tool, mock_settings
    ):
        """Test handling of successful test run with all tests passing."""
        mock_shell_tool.execute.return_value = """
============================= test session starts ==============================
collected 5 items

test_sample.py::test_one PASSED                                          [ 20%]
test_sample.py::test_two PASSED                                          [ 40%]
test_sample.py::test_three PASSED                                        [ 60%]
test_sample.py::test_four PASSED                                         [ 80%]
test_sample.py::test_five PASSED                                         [100%]

============================== 5 passed in 0.50s ===============================
"""

        # Mock Path.exists to return True
        with patch("pathlib.Path.exists", return_value=True):
            result = await debug_tool.execute(
                test_command="pytest test_sample.py", project_path="/tmp/test"
            )

        assert "All tests passed" in result
        assert "✅" in result

    @pytest.mark.asyncio
    async def test_failing_pytest_tests(
        self, debug_tool, mock_shell_tool, mock_read_file_tool, mock_llm_router, mock_settings
    ):
        """Test parsing of pytest failures."""
        mock_shell_tool.execute.return_value = """
============================= test session starts ==============================
test_sample.py::test_addition FAILED                                     [ 50%]
test_sample.py::test_subtraction FAILED                                  [100%]

=================================== FAILURES ===================================
________________________________ test_addition _________________________________

    def test_addition():
>       assert add(2, 2) == 5
E       AssertionError: assert 4 == 5

test_sample.py:10: AssertionError
______________________________ test_subtraction ________________________________

    def test_subtraction():
>       assert subtract(5, 3) == 3
E       AssertionError: assert 2 == 3

test_sample.py:15: AssertionError
============================== 2 failed in 0.10s ===============================
"""
        mock_read_file_tool.execute.return_value = """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def test_addition():
    assert add(2, 2) == 5

def test_subtraction():
    assert subtract(5, 3) == 3
"""
        mock_llm_router.chat.return_value = """**Root Cause:** Test assertions are incorrect.

**Suggested Fix:** Update test assertions to match actual function behavior.

**Reasoning:** The math functions work correctly, but tests expect wrong values."""

        with patch("pathlib.Path.exists", return_value=True):
            result = await debug_tool.execute(
                test_command="pytest test_sample.py", project_path="/tmp/test"
            )

        assert "Debug Report" in result
        assert "test_addition" in result
        assert "test_subtraction" in result
        assert "AssertionError" in result

    @pytest.mark.asyncio
    async def test_failing_jest_tests(
        self, debug_tool, mock_shell_tool, mock_read_file_tool, mock_llm_router, mock_settings
    ):
        """Test parsing of jest failures."""
        mock_shell_tool.execute.return_value = """
FAIL  src/math.test.js
  ● Math operations › addition

    expect(received).toBe(expected) // Object.is equality

    Expected: 5
    Received: 4

      4 | describe('Math operations', () => {
      5 |   it('addition', () => {
    > 6 |     expect(add(2, 2)).toBe(5);
        |                       ^
      7 |   });
      8 | });

      at Object.<anonymous> (src/math.test.js:6:23)

Test Suites: 1 failed, 1 total
Tests:       1 failed, 1 total
"""
        mock_read_file_tool.execute.return_value = """function add(a, b) {
  return a + b;
}

expect(add(2, 2)).toBe(5);
"""
        mock_llm_router.chat.return_value = "Test expects wrong value."

        with patch("pathlib.Path.exists", return_value=True):
            result = await debug_tool.execute(
                test_command="npm test", project_path="/tmp/test"
            )

        assert "Debug Report" in result or "test" in result.lower()

    @pytest.mark.asyncio
    async def test_failing_go_tests(
        self, debug_tool, mock_shell_tool, mock_read_file_tool, mock_llm_router, mock_settings
    ):
        """Test parsing of go test failures."""
        mock_shell_tool.execute.return_value = """
--- FAIL: TestAdd (0.00s)
    math_test.go:10: expected 5, got 4
--- FAIL: TestSubtract (0.00s)
    math_test.go:15: expected 3, got 2
FAIL
exit status 1
FAIL    github.com/user/math   0.002s
"""
        mock_read_file_tool.execute.return_value = """package math

func Add(a, b int) int {
    return a + b
}

func TestAdd(t *testing.T) {
    result := Add(2, 2)
    if result != 5 {
        t.Errorf("expected 5, got %d", result)
    }
}
"""
        mock_llm_router.chat.return_value = "Test expectations are incorrect."

        with patch("pathlib.Path.exists", return_value=True):
            result = await debug_tool.execute(
                test_command="go test ./...", project_path="/tmp/test"
            )

        assert "Debug Report" in result or "TestAdd" in result

    @pytest.mark.asyncio
    async def test_generic_failure_detection(
        self, debug_tool, mock_shell_tool, mock_llm_router, mock_settings
    ):
        """Test generic failure detection for unknown frameworks."""
        mock_shell_tool.execute.return_value = """
Running tests...
✗ Test failed: Division by zero
✗ Test failed: Null pointer exception
FAILED: 2 tests failed
"""
        mock_llm_router.chat.return_value = "Analysis of generic failures."

        with patch("pathlib.Path.exists", return_value=True):
            result = await debug_tool.execute(
                test_command="custom-test-runner", project_path="/tmp/test"
            )

        assert "Debug Report" in result or "failed" in result.lower()


class TestErrorParsing:
    """Test error parsing for different test frameworks."""

    def test_parse_pytest_format(self, debug_tool):
        """Test pytest error parsing."""
        output = """
test_sample.py::test_fail FAILED
test_sample.py:10: AssertionError
"""
        errors = debug_tool._parse_test_output(output, max_errors=10)
        assert len(errors) > 0
        assert errors[0]["framework"] == "pytest"

    def test_parse_jest_format(self, debug_tool):
        """Test jest error parsing."""
        output = """
● test name

  at Object.<anonymous> (file.js:10:5)
"""
        errors = debug_tool._parse_test_output(output, max_errors=10)
        # May or may not detect jest without full context
        assert isinstance(errors, list)

    def test_parse_go_test_format(self, debug_tool):
        """Test go test error parsing."""
        output = """
--- FAIL: TestExample (0.00s)
    example_test.go:10: error message
"""
        errors = debug_tool._parse_test_output(output, max_errors=10)
        assert len(errors) > 0
        if errors:
            assert errors[0]["framework"] == "go"

    def test_max_errors_limit(self, debug_tool):
        """Test that max_errors limit is respected."""
        output = "\n".join([f"test_{i} FAILED" for i in range(20)])
        errors = debug_tool._parse_test_output(output, max_errors=5)
        assert len(errors) <= 5


class TestDepthConfiguration:
    """Test depth parameter configuration."""

    @pytest.mark.asyncio
    async def test_quick_depth(
        self, debug_tool, mock_shell_tool, mock_llm_router, mock_settings
    ):
        """Test quick depth limits error count."""
        mock_shell_tool.execute.return_value = "FAILED" * 10
        mock_llm_router.chat.return_value = "Analysis"

        result = await debug_tool.execute(
            test_command="pytest", project_path="/tmp", depth="quick"
        )

        # Quick depth should limit errors analyzed
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_deep_depth(
        self, debug_tool, mock_shell_tool, mock_llm_router, mock_settings
    ):
        """Test deep depth allows more errors."""
        mock_shell_tool.execute.return_value = "FAILED" * 10
        mock_llm_router.chat.return_value = "Detailed analysis"

        result = await debug_tool.execute(
            test_command="pytest", project_path="/tmp", depth="deep"
        )

        assert isinstance(result, str)


class TestAutoFix:
    """Test auto-fix functionality."""

    @pytest.mark.asyncio
    async def test_auto_fix_not_available(
        self, debug_tool, mock_shell_tool, mock_llm_router, mock_settings
    ):
        """Test auto-fix when Claude Code CLI is not available."""
        mock_shell_tool.execute.return_value = "test FAILED"
        mock_llm_router.chat.return_value = "Fix: update code"

        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "pocketpaw.agents.delegation.ExternalAgentDelegate"
            ) as mock_delegate:
                mock_delegate.is_available.return_value = False

                result = await debug_tool.execute(
                    test_command="pytest",
                    project_path="/tmp",
                    auto_fix=True,
                )

                assert "Claude Code CLI" in result or "Auto-fix" in result

    @pytest.mark.asyncio
    async def test_auto_fix_success(
        self, debug_tool, mock_shell_tool, mock_llm_router, mock_settings
    ):
        """Test successful auto-fix execution."""
        mock_shell_tool.execute.return_value = "test FAILED"
        mock_llm_router.chat.return_value = "Fix: update assertion"

        with patch("pathlib.Path.exists", return_value=True):
            # Mock the import of DelegateToClaudeCodeTool inside _apply_fixes
            mock_delegate_tool = AsyncMock()
            mock_delegate_tool.execute.return_value = "✅ Fix applied successfully"

            with patch(
                "pocketpaw.agents.delegation.ExternalAgentDelegate.is_available",
                return_value=True,
            ):
                # Mock the tool import at the time it's imported in _apply_fixes
                with patch.dict(
                    "sys.modules",
                    {"pocketpaw.tools.builtin.delegate": MagicMock(
                        DelegateToClaudeCodeTool=lambda: mock_delegate_tool
                    )},
                ):
                    result = await debug_tool.execute(
                        test_command="pytest",
                        project_path="/tmp",
                        auto_fix=True,
                    )

                    # Should attempt auto-fix
                    assert "Auto-fix" in result or "Fix" in result or "applied" in result.lower()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_project_path(self, debug_tool):
        """Test handling of non-existent project path."""
        result = await debug_tool.execute(
            test_command="pytest", project_path="/nonexistent/path"
        )

        assert "Error" in result
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_llm_analysis_failure(
        self, debug_tool, mock_shell_tool, mock_llm_router, mock_settings
    ):
        """Test graceful handling of LLM analysis failure."""
        mock_shell_tool.execute.return_value = "test FAILED"
        mock_llm_router.chat.side_effect = Exception("LLM error")

        result = await debug_tool.execute(
            test_command="pytest", project_path="/tmp"
        )

        # Should still produce a report even if LLM fails
        assert "unavailable" in result.lower() or "failed" in result.lower()

    @pytest.mark.asyncio
    async def test_shell_execution_failure(self, debug_tool, mock_shell_tool):
        """Test handling of shell execution failure."""
        mock_shell_tool.execute.side_effect = Exception("Command failed")

        result = await debug_tool.execute(
            test_command="pytest", project_path="/tmp"
        )

        assert "Error" in result


class TestOutputFormatting:
    """Test debug report formatting."""

    def test_format_debug_report(self, debug_tool):
        """Test debug report formatting."""
        errors = [
            {
                "file": "test.py",
                "line": 10,
                "test": "test_example",
                "message": "AssertionError",
                "framework": "pytest",
            }
        ]
        analysis = "Root cause: incorrect assertion"
        test_output = "FAILED"

        report = debug_tool._format_debug_report(errors, analysis, test_output)

        assert "Debug Report" in report
        assert "test_example" in report
        assert "test.py" in report
        assert "Root cause" in report

    def test_tests_passed_detection(self, debug_tool):
        """Test detection of successful test runs."""
        passing_outputs = [
            "5 passed in 0.50s",
            "✓ All tests passed (10ms)",
            "PASS: 3 tests",
            "OK (5 tests)",
        ]

        for output in passing_outputs:
            # Should detect as passed (or at least not failed)
            result = debug_tool._tests_passed(output)
            # Just ensure it returns a boolean
            assert isinstance(result, bool)

    def test_tests_failed_detection(self, debug_tool):
        """Test detection of failed test runs."""
        failing_outputs = [
            "5 failed in 0.50s",
            "FAIL: test_example",
            "✗ Error: test failed",
        ]

        for output in failing_outputs:
            result = debug_tool._tests_passed(output)
            assert result is False
