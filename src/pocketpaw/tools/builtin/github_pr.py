# GitHub Pull Request Review tool — fetches and analyzes PRs using GitHub MCP.
# Created: 2026-02-22
# Part of Developer AI Copilot

import logging
import re
from typing import Any

from pocketpaw.config import Settings
from pocketpaw.llm.router import LLMRouter
from pocketpaw.mcp.manager import MCPManager
from pocketpaw.tools.protocol import BaseTool

logger = logging.getLogger(__name__)

# Review depth: controls analysis scope
_DEPTH_CONFIG = {
    "quick": {"focus_lines": 100, "context": "changed lines only"},
    "standard": {"focus_lines": 500, "context": "changed lines + function context"},
    "deep": {"focus_lines": 2000, "context": "full file context"},
}


class GitHubPRReviewTool(BaseTool):
    """GitHub PR reviewer: fetches PR data and provides LLM-based code review."""

    @property
    def name(self) -> str:
        return "review_github_pr"

    @property
    def description(self) -> str:
        return (
            "Review a GitHub pull request with AI-powered code analysis. "
            "Fetches PR metadata and diff via GitHub MCP, analyzes changes with LLM, "
            "and produces a structured code review with suggestions. "
            "Supports focus areas: security, performance, style, tests, docs. "
            "Requires GitHub MCP server configured via Dashboard > MCP Servers."
        )

    @property
    def trust_level(self) -> str:
        return "standard"  # Read-only GitHub access

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pr_url": {
                    "type": "string",
                    "description": (
                        "GitHub PR URL or 'owner/repo#123' format "
                        "(e.g., 'https://github.com/owner/repo/pull/123' or 'owner/repo#123')"
                    ),
                },
                "review_depth": {
                    "type": "string",
                    "description": (
                        "Review depth: 'quick' (changed lines only), "
                        "'standard' (with function context), or 'deep' (full file context)"
                    ),
                    "enum": ["quick", "standard", "deep"],
                    "default": "standard",
                },
                "focus_areas": {
                    "type": "array",
                    "description": (
                        "Specific areas to focus on during review. "
                        "Options: 'security', 'performance', 'style', 'tests', 'docs'"
                    ),
                    "items": {
                        "type": "string",
                        "enum": ["security", "performance", "style", "tests", "docs"],
                    },
                    "default": ["security", "performance"],
                },
            },
            "required": ["pr_url"],
        }

    async def execute(
        self,
        pr_url: str,
        review_depth: str = "standard",
        focus_areas: list[str] | None = None,
    ) -> str:
        if focus_areas is None:
            focus_areas = ["security", "performance"]

        depth_config = _DEPTH_CONFIG.get(review_depth, _DEPTH_CONFIG["standard"])

        try:
            # Step 1: Parse PR URL
            logger.info("Parsing PR URL: %s", pr_url)
            pr_info = self._parse_pr_url(pr_url)
            if "error" in pr_info:
                return self._error(pr_info["error"])

            # Step 2: Check GitHub MCP connection
            logger.info("Checking GitHub MCP connection")
            mcp_manager = self._get_mcp_manager()
            if not await self._check_github_mcp(mcp_manager):
                return self._error(
                    "GitHub MCP not connected. Configure it via Dashboard > MCP Servers.\n\n"
                    "Instructions:\n"
                    "1. Open PocketPaw Dashboard\n"
                    "2. Go to Settings > MCP Servers\n"
                    "3. Enable GitHub MCP server\n"
                    "4. Complete OAuth authorization\n"
                    "5. Retry this command"
                )

            # Step 3: Fetch PR metadata
            logger.info(
                "Fetching PR #%s from %s/%s",
                pr_info["number"],
                pr_info["owner"],
                pr_info["repo"],
            )
            pr_data = await self._fetch_pr_metadata(mcp_manager, pr_info)
            if pr_data.startswith("Error"):
                return self._error(f"Failed to fetch PR: {pr_data}")

            # Step 4: Fetch PR diff
            logger.info("Fetching PR diff")
            pr_diff = await self._fetch_pr_diff(mcp_manager, pr_info)
            if pr_diff.startswith("Error"):
                return self._error(f"Failed to fetch diff: {pr_diff}")

            # Truncate large diffs
            if len(pr_diff) > depth_config["focus_lines"] * 10:
                pr_diff = pr_diff[: depth_config["focus_lines"] * 10] + "\n\n...(truncated)"

            # Step 5: LLM Analysis
            logger.info("Analyzing PR with LLM")
            review = await self._analyze_pr_with_llm(
                pr_info, pr_data, pr_diff, focus_areas, depth_config
            )

            # Step 6: Format review
            formatted_review = self._format_review(pr_info, pr_data, review)

            return formatted_review

        except Exception as e:
            logger.exception("GitHub PR review failed")
            return self._error(f"Review failed: {e}")

    def _parse_pr_url(self, pr_url: str) -> dict[str, Any]:
        """Parse GitHub PR URL or owner/repo#number format."""
        # Try URL format first: https://github.com/owner/repo/pull/123
        url_pattern = re.compile(
            r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", re.IGNORECASE
        )
        match = url_pattern.search(pr_url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "number": int(match.group(3)),
            }

        # Try owner/repo#number format
        short_pattern = re.compile(r"^([^/]+)/([^/#]+)#(\d+)$")
        match = short_pattern.search(pr_url.strip())
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "number": int(match.group(3)),
            }

        return {
            "error": (
                f"Invalid PR URL format: {pr_url}\n\n"
                "Supported formats:\n"
                "• https://github.com/owner/repo/pull/123\n"
                "• owner/repo#123"
            )
        }

    def _get_mcp_manager(self) -> MCPManager:
        """Get the global MCP manager instance."""
        from pocketpaw.mcp.manager import MCPManager

        # Try to get singleton instance if it exists
        # For testing, we can inject a mock
        if hasattr(self, "_mcp_manager_override"):
            return self._mcp_manager_override

        # In production, create new instance
        # The real singleton pattern is managed at app level
        return MCPManager()

    async def _check_github_mcp(self, mcp_manager: MCPManager) -> bool:
        """Check if GitHub MCP is connected and available."""
        try:
            status = mcp_manager.get_server_status()
            github_status = status.get("github", {})

            return github_status.get("connected", False) and github_status.get(
                "enabled", False
            )

        except Exception as e:
            logger.warning("Failed to check GitHub MCP status: %s", e)
            return False

    async def _fetch_pr_metadata(
        self, mcp_manager: MCPManager, pr_info: dict
    ) -> str:
        """Fetch PR metadata via GitHub MCP."""
        try:
            result = await mcp_manager.call_tool(
                server_name="github",
                tool_name="get_pull_request",
                arguments={
                    "owner": pr_info["owner"],
                    "repo": pr_info["repo"],
                    "pull_number": pr_info["number"],
                },
            )
            return result

        except Exception as e:
            logger.error("Failed to fetch PR metadata: %s", e)
            return f"Error: {e}"

    async def _fetch_pr_diff(self, mcp_manager: MCPManager, pr_info: dict) -> str:
        """Fetch PR diff via GitHub MCP."""
        try:
            # Try get_pull_request_diff first
            result = await mcp_manager.call_tool(
                server_name="github",
                tool_name="get_pull_request_diff",
                arguments={
                    "owner": pr_info["owner"],
                    "repo": pr_info["repo"],
                    "pull_number": pr_info["number"],
                },
            )

            if not result.startswith("Error"):
                return result

            # Fallback: try list_pull_request_files
            logger.info("Falling back to list_pull_request_files")
            files_result = await mcp_manager.call_tool(
                server_name="github",
                tool_name="list_pull_request_files",
                arguments={
                    "owner": pr_info["owner"],
                    "repo": pr_info["repo"],
                    "pull_number": pr_info["number"],
                },
            )

            if files_result.startswith("Error"):
                return files_result

            return f"Files changed:\n{files_result}\n\n(Full diff not available)"

        except Exception as e:
            logger.error("Failed to fetch PR diff: %s", e)
            return f"Error: {e}"

    async def _analyze_pr_with_llm(
        self,
        pr_info: dict,
        pr_data: str,
        pr_diff: str,
        focus_areas: list[str],
        depth_config: dict,
    ) -> str:
        """Use LLM to analyze PR and generate code review."""
        try:
            settings = Settings.load()
            router = LLMRouter(settings)

            # Build review prompt
            focus_desc = ", ".join(focus_areas)
            prompt = f"""Review this GitHub pull request with focus on: {focus_desc}

**PR Information:**
{pr_data[:1500]}

**Diff/Changes:**
```diff
{pr_diff[:depth_config['focus_lines'] * 5]}
```

**Review Context:** {depth_config['context']}

Please provide a structured code review with:

1. **Summary**: Overall assessment of the PR (2-3 sentences)
2. **Strengths**: What's well done in this PR
3. **Issues**: Problems that should be addressed (categorized by severity: critical, major, minor)
4. **Suggestions**: Specific improvements with code examples where helpful
5. **Security**: Any security concerns (if applicable)
6. **Testing**: Assessment of test coverage and quality

Focus specifically on: {focus_desc}

Format your response with clear markdown sections."""

            review = await router.chat(prompt)
            return review

        except Exception as e:
            logger.warning("LLM review analysis failed: %s", e)
            return (
                "LLM analysis unavailable. Here's the raw PR data:\n\n"
                f"{pr_data[:1000]}\n\n"
                "Manual review recommended."
            )

    def _format_review(self, pr_info: dict, pr_data: str, review: str) -> str:
        """Format the final review output."""
        pr_url = f"https://github.com/{pr_info['owner']}/{pr_info['repo']}/pull/{pr_info['number']}"

        output = f"""# 🔍 GitHub PR Review

**Repository:** `{pr_info['owner']}/{pr_info['repo']}`
**PR Number:** #{pr_info['number']}
**URL:** {pr_url}

---

{review}

---

*Review generated by PocketPaw Developer Copilot*
"""
        return output
