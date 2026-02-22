"""Unit tests for GitHubPRReviewTool."""
# Created: 2026-02-22

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pocketpaw.tools.builtin.github_pr import GitHubPRReviewTool


@pytest.fixture
def github_pr_tool():
    """Create a GitHubPRReviewTool instance."""
    return GitHubPRReviewTool()


@pytest.fixture
def mock_mcp_manager():
    """Mock MCPManager."""
    manager = MagicMock()
    manager.get_server_status.return_value = {
        "github": {"connected": True, "enabled": True}
    }
    manager.call_tool = AsyncMock()
    return manager


@pytest.fixture
def mock_llm_router():
    """Mock LLMRouter."""
    with patch("pocketpaw.tools.builtin.github_pr.LLMRouter") as mock:
        instance = AsyncMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_settings():
    """Mock Settings.load()."""
    with patch("pocketpaw.tools.builtin.github_pr.Settings") as mock:
        settings = MagicMock()
        mock.load.return_value = settings
        yield settings


class TestGitHubPRToolBasics:
    """Test basic tool properties and configuration."""

    def test_tool_name(self, github_pr_tool):
        """Test tool name is correct."""
        assert github_pr_tool.name == "review_github_pr"

    def test_tool_description(self, github_pr_tool):
        """Test tool has description."""
        assert "github" in github_pr_tool.description.lower()
        assert "review" in github_pr_tool.description.lower()

    def test_trust_level(self, github_pr_tool):
        """Test tool uses standard trust level."""
        assert github_pr_tool.trust_level == "standard"

    def test_parameters_schema(self, github_pr_tool):
        """Test parameter schema is valid."""
        params = github_pr_tool.parameters
        assert params["type"] == "object"
        assert "pr_url" in params["properties"]
        assert "pr_url" in params["required"]
        assert "review_depth" in params["properties"]
        assert "focus_areas" in params["properties"]


class TestPRURLParsing:
    """Test PR URL parsing logic."""

    def test_parse_full_github_url(self, github_pr_tool):
        """Test parsing of full GitHub PR URL."""
        url = "https://github.com/anthropics/pocketpaw/pull/123"
        result = github_pr_tool._parse_pr_url(url)

        assert "error" not in result
        assert result["owner"] == "anthropics"
        assert result["repo"] == "pocketpaw"
        assert result["number"] == 123

    def test_parse_short_format(self, github_pr_tool):
        """Test parsing of owner/repo#number format."""
        url = "anthropics/pocketpaw#123"
        result = github_pr_tool._parse_pr_url(url)

        assert "error" not in result
        assert result["owner"] == "anthropics"
        assert result["repo"] == "pocketpaw"
        assert result["number"] == 123

    def test_parse_url_case_insensitive(self, github_pr_tool):
        """Test URL parsing is case insensitive."""
        url = "https://GITHUB.COM/Anthropics/PocketPaw/pull/123"
        result = github_pr_tool._parse_pr_url(url)

        assert "error" not in result
        assert result["owner"] == "Anthropics"
        assert result["repo"] == "PocketPaw"

    def test_parse_invalid_url(self, github_pr_tool):
        """Test handling of invalid URL format."""
        invalid_urls = [
            "not-a-url",
            "https://github.com/owner/repo",  # Missing pull number
            "owner/repo",  # Missing # and number
            "github.com/owner/repo/issues/123",  # Issues, not PR
        ]

        for url in invalid_urls:
            result = github_pr_tool._parse_pr_url(url)
            assert "error" in result

    def test_parse_with_http(self, github_pr_tool):
        """Test parsing URL with http (not https)."""
        url = "http://github.com/owner/repo/pull/456"
        result = github_pr_tool._parse_pr_url(url)

        assert "error" not in result
        assert result["number"] == 456


class TestMCPIntegration:
    """Test GitHub MCP integration."""

    @pytest.mark.asyncio
    async def test_check_github_mcp_connected(self, github_pr_tool, mock_mcp_manager):
        """Test checking GitHub MCP connection status."""
        is_connected = await github_pr_tool._check_github_mcp(mock_mcp_manager)
        assert is_connected is True

    @pytest.mark.asyncio
    async def test_check_github_mcp_not_connected(self, github_pr_tool):
        """Test handling when GitHub MCP is not connected."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.return_value = {
            "github": {"connected": False, "enabled": True}
        }

        is_connected = await github_pr_tool._check_github_mcp(mock_manager)
        assert is_connected is False

    @pytest.mark.asyncio
    async def test_check_github_mcp_disabled(self, github_pr_tool):
        """Test handling when GitHub MCP is disabled."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.return_value = {
            "github": {"connected": True, "enabled": False}
        }

        is_connected = await github_pr_tool._check_github_mcp(mock_manager)
        assert is_connected is False

    @pytest.mark.asyncio
    async def test_check_github_mcp_not_in_status(self, github_pr_tool):
        """Test handling when GitHub is not in MCP status."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.return_value = {}

        is_connected = await github_pr_tool._check_github_mcp(mock_manager)
        assert is_connected is False


class TestPRDataFetching:
    """Test PR metadata and diff fetching."""

    @pytest.mark.asyncio
    async def test_fetch_pr_metadata_success(self, github_pr_tool, mock_mcp_manager):
        """Test successful PR metadata fetch."""
        pr_info = {"owner": "owner", "repo": "repo", "number": 123}
        mock_mcp_manager.call_tool.return_value = (
            "PR #123: Add new feature\nAuthor: user\nStatus: Open"
        )

        result = await github_pr_tool._fetch_pr_metadata(mock_mcp_manager, pr_info)

        assert "PR #123" in result
        assert not result.startswith("Error")
        mock_mcp_manager.call_tool.assert_called_once_with(
            server_name="github",
            tool_name="get_pull_request",
            arguments={"owner": "owner", "repo": "repo", "pull_number": 123},
        )

    @pytest.mark.asyncio
    async def test_fetch_pr_metadata_failure(self, github_pr_tool):
        """Test handling of PR metadata fetch failure."""
        pr_info = {"owner": "owner", "repo": "repo", "number": 123}
        mock_manager = MagicMock()
        mock_manager.call_tool = AsyncMock(side_effect=Exception("API error"))

        result = await github_pr_tool._fetch_pr_metadata(mock_manager, pr_info)

        assert result.startswith("Error")

    @pytest.mark.asyncio
    async def test_fetch_pr_diff_success(self, github_pr_tool, mock_mcp_manager):
        """Test successful PR diff fetch."""
        pr_info = {"owner": "owner", "repo": "repo", "number": 123}
        mock_mcp_manager.call_tool.return_value = """diff --git a/file.py b/file.py
index 123..456 789
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
+    print("Hello, World!")
     pass
"""

        result = await github_pr_tool._fetch_pr_diff(mock_mcp_manager, pr_info)

        assert "diff --git" in result
        assert not result.startswith("Error")

    @pytest.mark.asyncio
    async def test_fetch_pr_diff_fallback_to_files_list(self, github_pr_tool):
        """Test fallback to list_pull_request_files when diff fails."""
        pr_info = {"owner": "owner", "repo": "repo", "number": 123}
        mock_manager = MagicMock()
        mock_manager.call_tool = AsyncMock(
            side_effect=[
                "Error: Diff too large",
                "file1.py\nfile2.py\nfile3.js",
            ]
        )

        result = await github_pr_tool._fetch_pr_diff(mock_manager, pr_info)

        assert "Files changed" in result
        assert "file1.py" in result
        assert mock_manager.call_tool.call_count == 2


class TestPRReviewExecution:
    """Test full PR review execution flow."""

    @pytest.mark.asyncio
    async def test_review_pr_success(
        self, github_pr_tool, mock_llm_router, mock_settings
    ):
        """Test successful PR review execution."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.return_value = {
            "github": {"connected": True, "enabled": True}
        }
        mock_manager.call_tool = AsyncMock(
            side_effect=[
                "PR #123: Add feature\nAuthor: dev",
                "diff --git a/file.py\n+new code",
            ]
        )

        # Inject mock manager
        github_pr_tool._mcp_manager_override = mock_manager

        mock_llm_router.chat.return_value = """**Summary:** Good PR overall.

**Strengths:** Clean code, good tests.

**Issues:** None critical.

**Suggestions:** Consider adding more comments."""

        result = await github_pr_tool.execute(
            pr_url="https://github.com/owner/repo/pull/123"
        )

        assert "GitHub PR Review" in result
        assert "owner/repo" in result
        assert "#123" in result
        assert "Summary" in result

    @pytest.mark.asyncio
    async def test_review_pr_mcp_not_connected(self, github_pr_tool, mock_settings):
        """Test handling when GitHub MCP is not connected."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.return_value = {
            "github": {"connected": False, "enabled": True}
        }
        github_pr_tool._mcp_manager_override = mock_manager

        result = await github_pr_tool.execute(
            pr_url="https://github.com/owner/repo/pull/123"
        )

        assert "Error" in result
        assert "not connected" in result
        assert "Dashboard" in result  # Should provide setup instructions

    @pytest.mark.asyncio
    async def test_review_pr_invalid_url(self, github_pr_tool):
        """Test handling of invalid PR URL."""
        result = await github_pr_tool.execute(pr_url="not-a-valid-url")

        assert "Error" in result
        assert "Invalid" in result or "format" in result.lower()

    @pytest.mark.asyncio
    async def test_review_with_focus_areas(
        self, github_pr_tool, mock_llm_router, mock_settings
    ):
        """Test PR review with specific focus areas."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.return_value = {
            "github": {"connected": True, "enabled": True}
        }
        mock_manager.call_tool = AsyncMock(
            side_effect=[
                "PR #123",
                "diff --git a/file.py",
            ]
        )
        github_pr_tool._mcp_manager_override = mock_manager

        mock_llm_router.chat.return_value = "Security review complete."

        result = await github_pr_tool.execute(
            pr_url="owner/repo#123",
            focus_areas=["security", "performance"],
        )

        # Check that LLM was called with focus areas
        assert mock_llm_router.chat.called
        call_args = mock_llm_router.chat.call_args[0][0]
        assert "security" in call_args.lower()
        assert "performance" in call_args.lower()

    @pytest.mark.asyncio
    async def test_review_with_different_depths(
        self, github_pr_tool, mock_llm_router, mock_settings
    ):
        """Test PR review with different depth levels."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.return_value = {
            "github": {"connected": True, "enabled": True}
        }
        mock_manager.call_tool = AsyncMock(
            side_effect=[
                "PR #123",
                "diff --git" + ("line\n" * 1000),  # Large diff
            ]
        )
        github_pr_tool._mcp_manager_override = mock_manager
        mock_llm_router.chat.return_value = "Review"

        # Test quick depth
        result_quick = await github_pr_tool.execute(
            pr_url="owner/repo#123", review_depth="quick"
        )
        assert isinstance(result_quick, str)

        # Reset mock
        mock_manager.call_tool = AsyncMock(
            side_effect=[
                "PR #123",
                "diff --git" + ("line\n" * 1000),
            ]
        )

        # Test deep depth
        result_deep = await github_pr_tool.execute(
            pr_url="owner/repo#123", review_depth="deep"
        )
        assert isinstance(result_deep, str)


class TestLLMAnalysis:
    """Test LLM-based PR analysis."""

    @pytest.mark.asyncio
    async def test_analyze_pr_with_llm_success(
        self, github_pr_tool, mock_llm_router, mock_settings
    ):
        """Test successful LLM analysis."""
        pr_info = {"owner": "owner", "repo": "repo", "number": 123}
        pr_data = "PR #123: Add feature"
        pr_diff = "diff --git a/file.py"
        focus_areas = ["security"]
        depth_config = {"focus_lines": 500, "context": "standard"}

        mock_llm_router.chat.return_value = "**Analysis:** Code looks good."

        result = await github_pr_tool._analyze_pr_with_llm(
            pr_info, pr_data, pr_diff, focus_areas, depth_config
        )

        assert "Analysis" in result
        mock_llm_router.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_pr_llm_failure_fallback(
        self, github_pr_tool, mock_llm_router, mock_settings
    ):
        """Test fallback when LLM analysis fails."""
        pr_info = {"owner": "owner", "repo": "repo", "number": 123}
        pr_data = "PR #123"
        pr_diff = "diff"
        focus_areas = ["security"]
        depth_config = {"focus_lines": 500, "context": "standard"}

        mock_llm_router.chat.side_effect = Exception("LLM error")

        result = await github_pr_tool._analyze_pr_with_llm(
            pr_info, pr_data, pr_diff, focus_areas, depth_config
        )

        assert "unavailable" in result.lower() or "raw" in result.lower()
        assert "Manual review" in result


class TestOutputFormatting:
    """Test review output formatting."""

    def test_format_review_output(self, github_pr_tool):
        """Test formatting of review output."""
        pr_info = {"owner": "owner", "repo": "repo", "number": 123}
        pr_data = "PR metadata"
        review = "**Summary:** Good PR\n\n**Issues:** None"

        result = github_pr_tool._format_review(pr_info, pr_data, review)

        assert "GitHub PR Review" in result
        assert "owner/repo" in result
        assert "#123" in result
        assert "https://github.com/owner/repo/pull/123" in result
        assert "Summary" in result
        assert "PocketPaw" in result


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_exception_during_review(self, github_pr_tool):
        """Test handling of unexpected exceptions."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.side_effect = Exception("Unexpected error")
        github_pr_tool._mcp_manager_override = mock_manager

        result = await github_pr_tool.execute(
            pr_url="https://github.com/owner/repo/pull/123"
        )

        assert "Error" in result

    @pytest.mark.asyncio
    async def test_very_large_diff_truncation(
        self, github_pr_tool, mock_llm_router, mock_settings
    ):
        """Test truncation of very large diffs."""
        mock_manager = MagicMock()
        mock_manager.get_server_status.return_value = {
            "github": {"connected": True, "enabled": True}
        }
        # Create a very large diff
        huge_diff = "+" * 100000
        mock_manager.call_tool = AsyncMock(side_effect=["PR #123", huge_diff])
        github_pr_tool._mcp_manager_override = mock_manager
        mock_llm_router.chat.return_value = "Review"

        result = await github_pr_tool.execute(pr_url="owner/repo#123")

        # Should not fail, should truncate
        assert isinstance(result, str)
        # LLM should be called with truncated diff
        assert mock_llm_router.chat.called
