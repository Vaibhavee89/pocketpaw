# DebugCodeTool

**Tool Name:** `debug_code`
**Trust Level:** `high` (executes shell commands)
**Created:** 2026-02-22

## Overview

The DebugCodeTool is an AI-powered debugging assistant that runs tests, analyzes failures, and provides intelligent debugging guidance. It supports multiple test frameworks (pytest, jest, go test) and can optionally apply fixes automatically.

## Features

- **Multi-framework Support**: Automatically detects and parses output from pytest, jest, go test, and generic test frameworks
- **LLM-Powered Analysis**: Uses LLM to analyze errors and provide root cause analysis with fix suggestions
- **Configurable Depth**: Quick, standard, or deep analysis modes
- **Auto-fix Capability**: Optional automatic fix application via Claude Code CLI delegation
- **Context-Aware**: Gathers source code context around error locations
- **Safe Execution**: Protected by Guardian security layer

## Parameters

### Required

- **`test_command`** (string): Command to run tests
  - Examples: `"pytest"`, `"npm test"`, `"go test ./..."`

### Optional

- **`project_path`** (string): Working directory for tests
  - Default: `"."` (current directory)
  - Example: `"/path/to/project"`

- **`depth`** (string): Analysis depth level
  - Options: `"quick"`, `"standard"`, `"deep"`
  - Default: `"standard"`
  - **Quick**: Analyzes up to 3 errors with 5 lines of context
  - **Standard**: Analyzes up to 10 errors with 10 lines of context
  - **Deep**: Analyzes up to 20 errors with 20 lines of context

- **`auto_fix`** (boolean): Attempt automatic fix application
  - Default: `false`
  - Requires: Claude Code CLI installed
  - **Important**: Always re-runs tests after applying fixes for verification

## Usage Examples

### Basic Usage

```python
from pocketpaw.tools.builtin import DebugCodeTool

tool = DebugCodeTool()

# Run pytest and analyze failures
result = await tool.execute(
    test_command="pytest tests/",
    project_path="/path/to/project"
)

print(result)
```

### With Depth Configuration

```python
# Quick analysis for rapid feedback
result = await tool.execute(
    test_command="npm test",
    depth="quick"
)

# Deep analysis for complex issues
result = await tool.execute(
    test_command="pytest",
    depth="deep"
)
```

### With Auto-Fix

```python
# Attempt automatic fix (requires Claude Code CLI)
result = await tool.execute(
    test_command="pytest test_sample.py",
    auto_fix=True
)
```

### Via Agent Conversation

```
User: Run the tests and help me debug the failures

Agent: I'll use the debug_code tool to run your tests and analyze any failures.
[Uses DebugCodeTool with test_command="pytest"]

Agent: I found 3 test failures. Here's the debug report:

# 🐛 Debug Report

**Errors Found:** 3

## Errors

### 1. test_addition
- **File:** `test_math.py`
- **Line:** 10
- **Framework:** pytest
- **Message:** AssertionError: assert 4 == 5

...

## Analysis

**Root Cause:** The test expects an incorrect value...
```

## Output Format

The tool produces a structured debug report:

```markdown
# 🐛 Debug Report

**Errors Found:** N

## Errors

### 1. [Test Name]
- **File:** `path/to/file`
- **Line:** 42
- **Framework:** pytest
- **Message:** Error details

### 2. [Another Test]
...

## Analysis

**Root Cause:** [LLM analysis of what's causing failures]

**Suggested Fix:** [Specific code changes to fix issues]

**Reasoning:** [Why these fixes should work]

## Raw Test Output

```
[Truncated test output for reference]
```
```

## Supported Test Frameworks

### pytest (Python)

```bash
# Detects patterns like:
# test_file.py::test_name FAILED
# test_file.py:10: AssertionError
```

Example:
```python
result = await tool.execute(
    test_command="pytest tests/ -v",
    project_path="/my/python/project"
)
```

### Jest (JavaScript/TypeScript)

```bash
# Detects patterns like:
# ● test_name
# at Object.<anonymous> (file.js:10:5)
```

Example:
```python
result = await tool.execute(
    test_command="npm test",
    project_path="/my/js/project"
)
```

### Go Test

```bash
# Detects patterns like:
# --- FAIL: TestName (0.00s)
#     file_test.go:10: error message
```

Example:
```python
result = await tool.execute(
    test_command="go test ./...",
    project_path="/my/go/project"
)
```

### Generic Fallback

Detects any output containing `FAILED`, `ERROR`, `FAIL:`, or `✗` markers.

## Security Considerations

### Trust Level: High

This tool executes shell commands and requires `high` trust level:

- Commands are validated by Guardian AI before execution
- Dangerous command patterns are blocked (e.g., `rm -rf`, `sudo`)
- Respects `file_jail_path` for file access
- All executions are logged to audit trail

### Auto-Fix Safety

When `auto_fix=True`:

1. Delegates to Claude Code CLI (requires explicit installation)
2. Creates new commits, never amends (preserves git history)
3. Always re-runs tests after applying fixes
4. Fails safely if fixes don't resolve issues
5. Provides detailed logs of all changes

## Dependencies

### Required

- **ShellTool**: For test execution
- **ReadFileTool**: For reading source code context
- **LLMRouter**: For error analysis

### Optional

- **DelegateToClaudeCodeTool**: For auto-fix capability
  - Requires: `npm install -g @anthropic-ai/claude-code`

## Error Handling

### Project Path Not Found

```python
# Error: Project path not found: /invalid/path
```

**Solution**: Verify the project path exists

### Tests Pass (No Errors)

```python
# ✅ All tests passed!
```

**Result**: Success message with test output

### LLM Analysis Unavailable

```python
# LLM analysis unavailable. Review the errors manually.
```

**Fallback**: Returns raw error information without AI analysis

### Auto-Fix Not Available

```python
# ⚠️ Auto-fix requires Claude Code CLI
# Install with: npm install -g @anthropic-ai/claude-code
```

**Solution**: Install Claude Code CLI or set `auto_fix=False`

## Performance Characteristics

- **Test Execution**: Depends on test suite size (typically 1-60 seconds)
- **Error Parsing**: <1 second for most test outputs
- **LLM Analysis**: 2-10 seconds depending on context size
- **Auto-Fix**: 30-180 seconds (includes re-running tests)

**Depth Impact**:
- **Quick**: Fastest, analyzes fewer errors
- **Standard**: Balanced speed/thoroughness
- **Deep**: Slowest, most comprehensive

## Configuration

### Global Settings

In `.pocketpaw/config.json`:

```json
{
  "tools": {
    "debug_code": {
      "default_depth": "standard",
      "max_errors": 10,
      "timeout": 120
    }
  }
}
```

### Environment Variables

- `POCKETPAW_FILE_JAIL_PATH`: Restricts file access to this directory
- `ANTHROPIC_API_KEY`: Required for LLM analysis (if using Anthropic provider)

## Best Practices

### 1. Start with Quick Depth

```python
# Get rapid feedback first
result = await tool.execute(
    test_command="pytest",
    depth="quick"
)
```

### 2. Use Standard Depth for Most Cases

```python
# Balanced analysis for typical debugging
result = await tool.execute(
    test_command="npm test",
    depth="standard"  # Default
)
```

### 3. Reserve Deep Depth for Complex Issues

```python
# Comprehensive analysis for difficult bugs
result = await tool.execute(
    test_command="go test ./...",
    depth="deep"
)
```

### 4. Disable Auto-Fix by Default

```python
# Manual review before applying fixes
result = await tool.execute(
    test_command="pytest",
    auto_fix=False  # Default, safer
)
```

### 5. Enable Auto-Fix for Simple Fixes

```python
# Safe for obvious issues like typos
result = await tool.execute(
    test_command="pytest test_simple.py",
    auto_fix=True
)
```

## Limitations

1. **Test Framework Detection**: Best with pytest, jest, go test; generic fallback for others
2. **Context Window**: Very large test suites may exceed LLM context limits
3. **Auto-Fix Reliability**: Complex multi-file bugs may require manual fixes
4. **Language Support**: Parsing optimized for Python, JavaScript, Go
5. **Private Functions**: Limited context for private/internal functions

## Troubleshooting

### Issue: "Command not found"

**Cause**: Test command not in PATH
**Solution**: Use full path or ensure test tool is installed

```python
# Use full path
result = await tool.execute(
    test_command="/usr/local/bin/pytest"
)
```

### Issue: "Permission denied"

**Cause**: File jail restriction
**Solution**: Project must be within `file_jail_path`

### Issue: "LLM analysis unavailable"

**Cause**: LLM provider not configured
**Solution**: Set `ANTHROPIC_API_KEY` or configure Ollama

### Issue: Auto-fix fails silently

**Cause**: Claude Code CLI not installed or tests still fail
**Solution**: Check Claude Code CLI installation, review fix suggestions manually

## Related Tools

- **DelegateToClaudeCodeTool**: For complex multi-file fixes
- **ShellTool**: For manual command execution
- **test-generator** (skill): For creating new test cases

## Examples from Real Projects

### Python Project with pytest

```python
result = await tool.execute(
    test_command="pytest tests/ -v --cov=src",
    project_path="/projects/myapp",
    depth="standard"
)

# Output:
# 🐛 Debug Report
# Errors Found: 2
# 1. test_api.py::test_user_creation FAILED
#    Root Cause: Database connection not mocked
#    Suggested Fix: Add @pytest.fixture for db mock
```

### JavaScript Project with Jest

```python
result = await tool.execute(
    test_command="npm test -- --coverage",
    project_path="/projects/webapp",
    depth="quick"
)

# Output:
# 🐛 Debug Report
# Errors Found: 1
# 1. Math operations › addition
#    Root Cause: Incorrect expected value in assertion
#    Suggested Fix: Change toBe(5) to toBe(4)
```

### Go Project

```python
result = await tool.execute(
    test_command="go test -v ./...",
    project_path="/projects/server",
    depth="deep"
)

# Output:
# 🐛 Debug Report
# Errors Found: 3
# Comprehensive analysis of failures across multiple packages
```

## Future Enhancements

Planned improvements:

- **Watch Mode**: Continuous testing on file changes
- **Coverage Reports**: HTML coverage report generation
- **Performance Profiling**: Integrate with py-spy/flamegraph
- **Multi-Language**: Better support for Rust, Ruby, Java
- **Smart Retry**: Re-run only failed tests
- **Parallel Execution**: Faster analysis for large suites

## Support

For issues or questions:

- GitHub Issues: [pocketpaw/issues](https://github.com/anthropics/pocketpaw/issues)
- Documentation: [pocketpaw/docs](https://github.com/anthropics/pocketpaw/tree/main/docs)
