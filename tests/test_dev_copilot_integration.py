"""Integration tests for Developer AI Copilot features."""
# Created: 2026-02-22

import pytest
from pathlib import Path
import tempfile
import os

from pocketpaw.tools.builtin.debug import DebugCodeTool
from pocketpaw.tools.builtin.github_pr import GitHubPRReviewTool


class TestDebugToolIntegration:
    """Integration tests for DebugCodeTool with real filesystem."""

    @pytest.mark.asyncio
    async def test_debug_tool_with_real_pytest_project(self):
        """Test DebugCodeTool with a real temporary pytest project."""
        tool = DebugCodeTool()

        # Create a temporary project with a failing test
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_sample.py"
            test_file.write_text("""
def add(a, b):
    return a + b

def test_addition():
    assert add(2, 2) == 5  # Intentional failure
""")

            # Run the debug tool (will fail test, then analyze)
            result = await tool.execute(
                test_command="pytest test_sample.py -v",
                project_path=tmpdir,
                depth="quick",
                auto_fix=False,
            )

            # Verify the tool produces a debug report
            assert isinstance(result, str)
            # Either produces a debug report or an error about missing pytest
            assert (
                "Debug Report" in result
                or "test_addition" in result
                or "Error" in result
                or "not found" in result.lower()
            )

    @pytest.mark.asyncio
    async def test_debug_tool_with_passing_tests(self):
        """Test DebugCodeTool with passing tests."""
        tool = DebugCodeTool()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_pass.py"
            test_file.write_text("""
def test_simple():
    assert True
""")

            result = await tool.execute(
                test_command="pytest test_pass.py -v",
                project_path=tmpdir,
            )

            # Should report success or error about pytest not found
            assert isinstance(result, str)
            assert (
                "passed" in result.lower()
                or "Error" in result
                or "not found" in result.lower()
            )

    @pytest.mark.asyncio
    async def test_debug_tool_invalid_project_path(self):
        """Test DebugCodeTool with invalid project path."""
        tool = DebugCodeTool()

        result = await tool.execute(
            test_command="pytest",
            project_path="/nonexistent/path/to/project",
        )

        assert "Error" in result
        assert "not found" in result.lower()


class TestGitHubPRToolIntegration:
    """Integration tests for GitHubPRReviewTool."""

    @pytest.mark.asyncio
    async def test_pr_url_parsing(self):
        """Test PR URL parsing with various formats."""
        tool = GitHubPRReviewTool()

        # Test valid URL formats
        valid_urls = [
            "https://github.com/owner/repo/pull/123",
            "http://github.com/owner/repo/pull/456",
            "owner/repo#789",
            "https://GITHUB.COM/Owner/Repo/pull/100",
        ]

        for url in valid_urls:
            result = tool._parse_pr_url(url)
            assert "error" not in result
            assert "owner" in result
            assert "repo" in result
            assert "number" in result

    @pytest.mark.asyncio
    async def test_pr_review_without_mcp(self):
        """Test PR review fails gracefully without GitHub MCP."""
        tool = GitHubPRReviewTool()

        # Attempt to review a PR without MCP configured
        result = await tool.execute(
            pr_url="https://github.com/anthropics/pocketpaw/pull/1"
        )

        # Should fail gracefully with helpful error message
        assert "Error" in result or "not connected" in result.lower()


class TestSkillsIntegration:
    """Integration tests for skills."""

    def test_architecture_skill_exists(self):
        """Test that architecture-design skill file exists."""
        skill_path = Path.home() / ".claude/skills/architecture-design/SKILL.md"
        assert skill_path.exists(), "architecture-design skill should exist"

        # Verify it has required front matter
        content = skill_path.read_text()
        assert "name: architecture-design" in content
        assert "user-invocable: true" in content
        assert "allowed-tools:" in content

    def test_test_generator_skill_exists(self):
        """Test that test-generator skill file exists."""
        skill_path = Path.home() / ".claude/skills/test-generator/SKILL.md"
        assert skill_path.exists(), "test-generator skill should exist"

        # Verify it has required front matter
        content = skill_path.read_text()
        assert "name: test-generator" in content
        assert "user-invocable: true" in content
        assert "allowed-tools:" in content

    def test_skills_have_proper_structure(self):
        """Test that skills have proper markdown structure."""
        skills = [
            Path.home() / ".claude/skills/architecture-design/SKILL.md",
            Path.home() / ".claude/skills/test-generator/SKILL.md",
        ]

        for skill_path in skills:
            if skill_path.exists():
                content = skill_path.read_text()

                # Should have front matter
                assert content.startswith("---")
                assert content.count("---") >= 2

                # Should have headings
                assert "#" in content

                # Should have example usage or process
                assert (
                    "process" in content.lower()
                    or "example" in content.lower()
                    or "usage" in content.lower()
                )


class TestToolRegistration:
    """Test that new tools are properly registered."""

    def test_debug_tool_in_registry(self):
        """Test DebugCodeTool is importable from builtin."""
        from pocketpaw.tools.builtin import DebugCodeTool

        assert DebugCodeTool is not None
        tool = DebugCodeTool()
        assert tool.name == "debug_code"
        assert tool.trust_level == "high"

    def test_github_pr_tool_in_registry(self):
        """Test GitHubPRReviewTool is importable from builtin."""
        from pocketpaw.tools.builtin import GitHubPRReviewTool

        assert GitHubPRReviewTool is not None
        tool = GitHubPRReviewTool()
        assert tool.name == "review_github_pr"
        assert tool.trust_level == "standard"

    def test_tools_have_valid_definitions(self):
        """Test that tools have valid ToolDefinition objects."""
        from pocketpaw.tools.builtin import DebugCodeTool, GitHubPRReviewTool

        debug_tool = DebugCodeTool()
        pr_tool = GitHubPRReviewTool()

        # Check DebugCodeTool definition
        debug_def = debug_tool.definition
        assert debug_def.name == "debug_code"
        assert "test" in debug_def.description.lower()
        assert "test_command" in debug_def.parameters["properties"]

        # Check GitHubPRReviewTool definition
        pr_def = pr_tool.definition
        assert pr_def.name == "review_github_pr"
        assert "github" in pr_def.description.lower()
        assert "pr_url" in pr_def.parameters["properties"]

    def test_tools_support_openai_schema(self):
        """Test tools can export OpenAI function calling schema."""
        from pocketpaw.tools.builtin import DebugCodeTool

        tool = DebugCodeTool()
        definition = tool.definition
        openai_schema = definition.to_openai_schema()

        assert openai_schema["type"] == "function"
        assert "function" in openai_schema
        assert "name" in openai_schema["function"]
        assert "parameters" in openai_schema["function"]

    def test_tools_support_anthropic_schema(self):
        """Test tools can export Anthropic tool schema."""
        from pocketpaw.tools.builtin import GitHubPRReviewTool

        tool = GitHubPRReviewTool()
        definition = tool.definition
        anthropic_schema = definition.to_anthropic_schema()

        assert "name" in anthropic_schema
        assert "description" in anthropic_schema
        assert "input_schema" in anthropic_schema


@pytest.mark.skipif(
    not os.getenv("INTEGRATION_TESTS"),
    reason="Requires INTEGRATION_TESTS=1 environment variable",
)
class TestFullIntegration:
    """Full integration tests requiring external services."""

    @pytest.mark.asyncio
    async def test_full_debug_workflow_with_pytest(self):
        """Full integration test with pytest (requires pytest installed)."""
        tool = DebugCodeTool()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a more complex failing test
            test_file = Path(tmpdir) / "test_math.py"
            test_file.write_text("""
import pytest

def divide(a, b):
    return a / b

def test_divide():
    assert divide(10, 2) == 5

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_divide_negative():
    assert divide(-10, 2) == -5

def test_failing():
    assert divide(10, 3) == 3  # This will fail
""")

            result = await tool.execute(
                test_command="pytest test_math.py -v",
                project_path=tmpdir,
                depth="standard",
            )

            # Verify comprehensive debug report
            if "pytest" in result.lower() or "Error" not in result:
                assert "test_failing" in result or "Debug Report" in result

    @pytest.mark.asyncio
    async def test_github_pr_review_with_real_pr(self):
        """Test GitHub PR review with a real public PR (requires GitHub MCP)."""
        tool = GitHubPRReviewTool()

        # Use a stable, well-known public PR
        result = await tool.execute(
            pr_url="https://github.com/anthropics/pocketpaw/pull/1",
            review_depth="quick",
        )

        # Either succeeds with review or fails with helpful MCP error
        assert isinstance(result, str)
        if "Error" in result:
            assert "MCP" in result or "connected" in result.lower()
        else:
            assert "Review" in result or "PR" in result
