#!/usr/bin/env python3
"""
Tool Use Evaluation for Stack 3.0 [DEPRECATED]
==============================================

⚠️  WARNING: This evaluation script is DEPRECATED and the methodology is INVALID.

This evaluator uses a naive keyword-matching simulation, not actual model inference.
There is no proper benchmark implementation for tool calling. The claimed 94.1%
score is unverifiable and misleading.

A proper tool use benchmark needs to be built with 500+ realistic test cases and
actual model calls. This script remains only as a placeholder.

See EVALUATION.md for the full audit report.
"""

import argparse
import json
import os
import random
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Tool categories and test cases
TOOL_CATEGORIES = {
    "file_operations": {
        "description": "File read, write, edit, and glob operations",
        "tools": ["FileReadTool", "FileWriteTool", "FileEditTool", "GlobTool"],
        "test_cases": [
            # FileReadTool tests
            {"task": "Read the contents of /etc/hostname", "expected_tool": "FileReadTool", "expected_params": {"path": "/etc/hostname"}},
            {"task": "Show me what's in README.md", "expected_tool": "FileReadTool", "expected_params": {"path": "README.md"}},
            {"task": "Display the contents of config.json", "expected_tool": "FileReadTool", "expected_params": {"path": "config.json"}},
            {"task": "Cat the file /tmp/test.txt", "expected_tool": "FileReadTool", "expected_params": {"path": "/tmp/test.txt"}},
            {"task": "View the python file main.py", "expected_tool": "FileReadTool", "expected_params": {"path": "main.py"}},
            {"task": "Show me the contents of the src directory", "expected_tool": "GlobTool", "expected_params": {"pattern": "src/**/*"}},
            {"task": "Find all Python files in the project", "expected_tool": "GlobTool", "expected_params": {"pattern": "**/*.py"}},
            {"task": "List all JSON files", "expected_tool": "GlobTool", "expected_params": {"pattern": "**/*.json"}},
            {"task": "Find all markdown files", "expected_tool": "GlobTool", "expected_params": {"pattern": "**/*.md"}},
            {"task": "Show all files in the current directory", "expected_tool": "GlobTool", "expected_params": {"pattern": "*"}},
            # FileWriteTool tests
            {"task": "Create a file called hello.txt with content 'Hello World'", "expected_tool": "FileWriteTool", "expected_params": {"path": "hello.txt", "content": "Hello World"}},
            {"task": "Write 'export PATH=/usr/bin' to .bashrc", "expected_tool": "FileWriteTool", "expected_params": {"path": ".bashrc"}},
            {"task": "Save the data to output.json", "expected_tool": "FileWriteTool", "expected_params": {"path": "output.json"}},
            {"task": "Create a new file test.py with shebang", "expected_tool": "FileWriteTool", "expected_params": {"path": "test.py"}},
            {"task": "Write the configuration to config.yaml", "expected_tool": "FileWriteTool", "expected_params": {"path": "config.yaml"}},
            # FileEditTool tests
            {"task": "Replace 'foo' with 'bar' in file.txt", "expected_tool": "FileEditTool", "expected_params": {"path": "file.txt"}},
            {"task": "Add a new line to the end of notes.txt", "expected_tool": "FileEditTool", "expected_params": {"path": "notes.txt"}},
            {"task": "Update the version number in package.json", "expected_tool": "FileEditTool", "expected_params": {"path": "package.json"}},
            {"task": "Remove the debug statement from main.py", "expected_tool": "FileEditTool", "expected_params": {"path": "main.py"}},
            {"task": "Edit the config file to enable debug mode", "expected_tool": "FileEditTool", "expected_params": {"path": "config.json"}},
        ]
    },
    "git_operations": {
        "description": "Git commands for version control",
        "tools": ["BashTool"],
        "test_cases": [
            {"task": "Check the git status", "expected_tool": "BashTool", "expected_params": {"command": "git status"}},
            {"task": "Show me the git log", "expected_tool": "BashTool", "expected_params": {"command": "git log --oneline -10"}},
            {"task": "Create a new branch called feature-x", "expected_tool": "BashTool", "expected_params": {"command": "git checkout -b feature-x"}},
            {"task": "Commit all changes with message 'fix bug'", "expected_tool": "BashTool", "expected_params": {"command": "git add -A && git commit -m 'fix bug'"}},
            {"task": "Show the differences in main.py", "expected_tool": "BashTool", "expected_params": {"command": "git diff main.py"}},
            {"task": "Push to origin main", "expected_tool": "BashTool", "expected_params": {"command": "git push origin main"}},
            {"task": "Pull latest changes from remote", "expected_tool": "BashTool", "expected_params": {"command": "git pull"}},
            {"task": "Show which files changed in last commit", "expected_tool": "BashTool", "expected_params": {"command": "git diff --name-only HEAD~1..HEAD"}},
            {"task": "List all git branches", "expected_tool": "BashTool", "expected_params": {"command": "git branch -a"}},
            {"task": "Show the current git branch", "expected_tool": "BashTool", "expected_params": {"command": "git branch --show-current"}},
            {"task": "Stash current changes", "expected_tool": "BashTool", "expected_params": {"command": "git stash"}},
            {"task": "Apply stashed changes", "expected_tool": "BashTool", "expected_params": {"command": "git stash pop"}},
            {"task": "Show remotes", "expected_tool": "BashTool", "expected_params": {"command": "git remote -v"}},
            {"task": "Merge feature branch into main", "expected_tool": "BashTool", "expected_params": {"command": "git merge feature"}},
            {"task": "Rebase onto latest main", "expected_tool": "BashTool", "expected_params": {"command": "git rebase main"}},
        ]
    },
    "search_operations": {
        "description": "Search and grep operations",
        "tools": ["GrepTool", "WebSearchTool"],
        "test_cases": [
            {"task": "Search for 'TODO' in all Python files", "expected_tool": "GrepTool", "expected_params": {"pattern": "TODO", "files": "**/*.py"}},
            {"task": "Find all occurrences of 'debug' in src/", "expected_tool": "GrepTool", "expected_params": {"pattern": "debug", "files": "src/**/*"}},
            {"task": "Search for function definitions", "expected_tool": "GrepTool", "expected_params": {"pattern": "^def ", "files": "**/*.py"}},
            {"task": "Find imports in main.py", "expected_tool": "GrepTool", "expected_params": {"pattern": "^import |^from ", "files": "main.py"}},
            {"task": "Search for console.log in JavaScript files", "expected_tool": "GrepTool", "expected_params": {"pattern": "console.log", "files": "**/*.js"}},
            {"task": "Find all TODO comments", "expected_tool": "GrepTool", "expected_params": {"pattern": "TODO|FIXME", "files": "**/*"}},
            {"task": "Search the web for Python tutorials", "expected_tool": "WebSearchTool", "expected_params": {"query": "Python tutorials"}},
            {"task": "Search for how to use git rebase", "expected_tool": "WebSearchTool", "expected_params": {"query": "git rebase tutorial"}},
            {"task": "Look up documentation for async/await", "expected_tool": "WebSearchTool", "expected_params": {"query": "async await JavaScript documentation"}},
            {"task": "Find best practices for REST API design", "expected_tool": "WebSearchTool", "expected_params": {"query": "REST API design best practices"}},
        ]
    },
    "execution_operations": {
        "description": "Shell and command execution",
        "tools": ["BashTool"],
        "test_cases": [
            {"task": "List all files in current directory", "expected_tool": "BashTool", "expected_params": {"command": "ls -la"}},
            {"task": "Show current working directory", "expected_tool": "BashTool", "expected_params": {"command": "pwd"}},
            {"task": "Check Python version", "expected_tool": "BashTool", "expected_params": {"command": "python3 --version"}},
            {"task": "Run pytest on tests/", "expected_tool": "BashTool", "expected_params": {"command": "pytest tests/ -v"}},
            {"task": "Install requirements.txt", "expected_tool": "BashTool", "expected_params": {"command": "pip install -r requirements.txt"}},
            {"task": "Check disk usage", "expected_tool": "BashTool", "expected_params": {"command": "df -h"}},
            {"task": "Show memory usage", "expected_tool": "BashTool", "expected_params": {"command": "free -m"}},
            {"task": "Check running processes", "expected_tool": "BashTool", "expected_params": {"command": "ps aux | head -20"}},
            {"task": "Find large files", "expected_tool": "BashTool", "expected_params": {"command": "find . -type f -size +100M"}},
            {"task": "Count lines in Python files", "expected_tool": "BashTool", "expected_params": {"command": "find . -name '*.py' | xargs wc -l"}},
            {"task": "Kill process on port 3000", "expected_tool": "BashTool", "expected_params": {"command": "lsof -ti:3000 | xargs kill"}},
            {"task": "Start a Python HTTP server", "expected_tool": "BashTool", "expected_params": {"command": "python3 -m http.server 8000"}},
            {"task": "Check if port 5432 is open", "expected_tool": "BashTool", "expected_params": {"command": "nc -zv localhost 5432"}},
            {"task": "Show network connections", "expected_tool": "BashTool", "expected_params": {"command": "netstat -tuln"}},
            {"task": "Check DNS for example.com", "expected_tool": "BashTool", "expected_params": {"command": "dig example.com"}},
        ]
    },
    "task_operations": {
        "description": "Task and todo management",
        "tools": ["TaskCreateTool", "TaskListTool", "TaskUpdateTool", "TodoWriteTool"],
        "test_cases": [
            {"task": "Create a task to fix the login bug", "expected_tool": "TaskCreateTool", "expected_params": {"title": "Fix login bug"}},
            {"task": "List all pending tasks", "expected_tool": "TaskListTool", "expected_params": {}},
            {"task": "Mark task #123 as complete", "expected_tool": "TaskUpdateTool", "expected_params": {"task_id": "123", "status": "completed"}},
            {"task": "Add a todo item for code review", "expected_tool": "TodoWriteTool", "expected_params": {"content": "Code review"}},
            {"task": "Show me the task with ID 42", "expected_tool": "TaskGetTool", "expected_params": {"task_id": "42"}},
            {"task": "Stop the currently running task", "expected_tool": "TaskStopTool", "expected_params": {}},
            {"task": "Update task priority", "expected_tool": "TaskUpdateTool", "expected_params": {"task_id": "123", "priority": "high"}},
            {"task": "Create a subtask under task #5", "expected_tool": "TaskCreateTool", "expected_params": {"title": "Subtask", "parent_id": "5"}},
            {"task": "Get output of task #99", "expected_tool": "TaskOutputTool", "expected_params": {"task_id": "99"}},
            {"task": "Delete completed tasks", "expected_tool": "TodoWriteTool", "expected_params": {"filter": "completed", "action": "delete"}},
        ]
    },
    "web_operations": {
        "description": "Web fetch and API operations",
        "tools": ["WebFetchTool", "WebSearchTool"],
        "test_cases": [
            {"task": "Fetch the README from GitHub", "expected_tool": "WebFetchTool", "expected_params": {"url": "https://github.com/example/repo"}},
            {"task": "Get the weather for New York", "expected_tool": "WebSearchTool", "expected_params": {"query": "weather New York"}},
            {"task": "Look up Python documentation", "expected_tool": "WebFetchTool", "expected_params": {"url": "https://docs.python.org/"}},
            {"task": "Search for OpenAI API docs", "expected_tool": "WebSearchTool", "expected_params": {"query": "OpenAI API documentation"}},
            {"task": "Get the latest news about AI", "expected_tool": "WebSearchTool", "expected_params": {"query": "AI news 2024"}},
            {"task": "Fetch content from a URL", "expected_tool": "WebFetchTool", "expected_params": {"url": "https://example.com/api/data"}},
        ]
    },
    "config_operations": {
        "description": "Configuration and settings",
        "tools": ["ConfigTool", "SkillTool"],
        "test_cases": [
            {"task": "Show the current configuration", "expected_tool": "ConfigTool", "expected_params": {}},
            {"task": "List all available skills", "expected_tool": "SkillTool", "expected_params": {"action": "list"}},
            {"task": "Show config for git integration", "expected_tool": "ConfigTool", "expected_params": {"section": "git"}},
            {"task": "Get skill documentation for coding", "expected_tool": "SkillTool", "expected_params": {"skill": "coding", "action": "info"}},
            {"task": "Update the timeout setting", "expected_tool": "ConfigTool", "expected_params": {"key": "timeout", "value": "30"}},
            {"task": "List configured API keys", "expected_tool": "ConfigTool", "expected_params": {"section": "api_keys"}},
        ]
    },
    "agent_operations": {
        "description": "Multi-agent and team operations",
        "tools": ["TeamCreateTool", "TeamDeleteTool", "EnterPlanModeTool", "ExitPlanModeTool"],
        "test_cases": [
            {"task": "Create a team for the project", "expected_tool": "TeamCreateTool", "expected_params": {"name": "project-team"}},
            {"task": "Delete the old team", "expected_tool": "TeamDeleteTool", "expected_params": {"team": "old-team"}},
            {"task": "Enter plan mode to review changes", "expected_tool": "EnterPlanModeTool", "expected_params": {}},
            {"task": "Exit plan mode and continue", "expected_tool": "ExitPlanModeTool", "expected_params": {}},
            {"task": "Enter worktree for feature branch", "expected_tool": "EnterWorktreeTool", "expected_params": {"branch": "feature-x"}},
            {"task": "Exit current worktree", "expected_tool": "ExitWorktreeTool", "expected_params": {}},
        ]
    }
}


@dataclass
class ToolTestCase:
    """Single tool test case."""
    category: str
    task: str
    expected_tool: str
    expected_params: Dict[str, Any]


@dataclass
class ToolEvalResult:
    """Result for a single tool evaluation."""
    category: str
    task: str
    expected_tool: str
    predicted_tool: Optional[str]
    tool_correct: bool
    params_correct: bool
    execution_success: bool
    error: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class ToolEvalSummary:
    """Aggregated tool evaluation summary."""
    model: str
    timestamp: str
    total_cases: int
    tool_selection_accuracy: float
    parameter_accuracy: float
    execution_success_rate: float
    overall_success_rate: float
    category_results: Dict[str, Dict[str, float]]
    results: List[Dict] = field(default_factory=list)


class ToolUseEvaluator:
    """
    Comprehensive Tool Use Evaluation System.
    
    Evaluates tool selection, parameter extraction, and execution success
    across 500+ test cases covering all major tool categories.
    """
    
    def __init__(self, model: str = "stack-3.0"):
        self.model = model
        self.test_cases = self._generate_test_cases()
    
    def _generate_test_cases(self) -> List[ToolTestCase]:
        """Generate all tool test cases."""
        cases = []
        for category, data in TOOL_CATEGORIES.items():
            for tc in data["test_cases"]:
                cases.append(ToolTestCase(
                    category=category,
                    task=tc["task"],
                    expected_tool=tc["expected_tool"],
                    expected_params=tc.get("expected_params", {})
                ))
        
        # Add variations to reach 500+ test cases
        variations = self._generate_variations()
        cases.extend(variations)
        
        return cases
    
    def _generate_variations(self) -> List[ToolTestCase]:
        """Generate additional test case variations."""
        variations = []
        
        # File operation variations
        file_variations = [
            ("file_operations", "Read {path}", "FileReadTool", {"path": "/etc/passwd"}),
            ("file_operations", "Show me {path}", "FileReadTool", {"path": ".env"}),
            ("file_operations", "Display {path}", "FileReadTool", {"path": "docker-compose.yml"}),
            ("file_operations", "Open {path}", "FileReadTool", {"path": "script.py"}),
            ("file_operations", "Find all {ext} files", "GlobTool", {"pattern": "**/*.{ext}"}),
            ("file_operations", "Locate all {ext} files", "GlobTool", {"pattern": "**/*.{ext}"}),
            ("file_operations", "Write 'test' to {path}", "FileWriteTool", {"path": "test.txt", "content": "test"}),
            ("file_operations", "Create {path} with data", "FileWriteTool", {"path": "data.csv"}),
            ("file_operations", "Edit {path} to change X", "FileEditTool", {"path": "config.yml"}),
        ]
        
        # Git variations
        git_variations = [
            ("git_operations", "git {command}", "BashTool", {"command": "git status -sb"}),
            ("git_operations", "Show git {subcommand}", "BashTool", {"command": "git show --stat"}),
            ("git_operations", "Run git {cmd}", "BashTool", {"command": "git log -5 --graph"}),
        ]
        
        # Search variations
        search_variations = [
            ("search_operations", "grep for {pattern} in {files}", "GrepTool", {"pattern": "{pattern}", "files": "{files}"}),
            ("search_operations", "Find {pattern} in codebase", "GrepTool", {"pattern": "{pattern}", "files": "**/*"}),
            ("search_operations", "Search web for {query}", "WebSearchTool", {"query": "{query}"}),
        ]
        
        # Execution variations
        exec_variations = [
            ("execution_operations", "Run {command}", "BashTool", {"command": "{command}"}),
            ("execution_operations", "Execute {command}", "BashTool", {"command": "{command}"}),
            ("execution_operations", "Run shell command {cmd}", "BashTool", {"command": "{cmd}"}),
        ]
        
        all_variations = file_variations + git_variations + search_variations + exec_variations
        
        # Generate concrete variations
        paths = ["src/main.py", "lib/utils.js", "docs/README.md", "tests/test.py", "config/settings.json"]
        extensions = ["py", "js", "ts", "go", "rs", "java", "rb"]
        git_cmds = ["stash list", "tag -l", "reflog", "shortlog -sn", "ls-files"]
        patterns = ["function", "class", "const", "let", "var", "async", "await"]
        
        for category, task, tool, params in all_variations:
            for i in range(5):  # 5 variations each
                path = paths[i % len(paths)]
                ext = extensions[i % len(extensions)]
                git_cmd = git_cmds[i % len(git_cmds)]
                pattern = patterns[i % len(patterns)]
                
                concrete_task = task.format(
                    path=path, ext=ext, command=git_cmd, pattern=pattern,
                    files="**/*.py", query="example query", cmd="ls"
                )
                concrete_params = {}
                for k, v in params.items():
                    concrete_params[k] = v.format(
                        path=path, ext=ext, command=git_cmd, pattern=pattern,
                        files="**/*.py", query="example query", cmd="ls"
                    )
                
                variations.append(ToolTestCase(
                    category=category,
                    task=concrete_task,
                    expected_tool=tool,
                    expected_params=concrete_params
                ))
        
        return variations
    
    def predict_tool(self, task: str) -> tuple[str, Dict[str, Any]]:
        """
        Predict which tool to use for a task.
        In production, this would call the actual model.
        """
        # Simple keyword-based simulation
        task_lower = task.lower()
        
        if any(word in task_lower for word in ['read', 'show', 'display', 'view', 'cat', 'open']):
            if 'pattern' in task_lower or 'find' in task_lower:
                return "GlobTool", {"pattern": "**/*"}
            return "FileReadTool", {"path": "/tmp/file.txt"}
        
        if any(word in task_lower for word in ['write', 'create', 'save', 'make file']):
            return "FileWriteTool", {"path": "output.txt", "content": ""}
        
        if any(word in task_lower for word in ['edit', 'replace', 'update', 'modify', 'change']):
            return "FileEditTool", {"path": "file.txt"}
        
        if 'grep' in task_lower or 'search' in task_lower:
            if 'web' in task_lower or 'internet' in task_lower:
                return "WebSearchTool", {"query": "search"}
            return "GrepTool", {"pattern": "TODO", "files": "**/*.py"}
        
        if any(word in task_lower for word in ['git', 'commit', 'push', 'pull', 'branch']):
            return "BashTool", {"command": "git status"}
        
        if any(word in task_lower for word in ['run', 'execute', 'shell', 'bash', 'command']):
            return "BashTool", {"command": "ls -la"}
        
        if 'task' in task_lower:
            if 'create' in task_lower:
                return "TaskCreateTool", {"title": "New task"}
            if 'list' in task_lower:
                return "TaskListTool", {}
            if 'update' in task_lower:
                return "TaskUpdateTool", {"task_id": "1"}
            return "TaskGetTool", {"task_id": "1"}
        
        if 'todo' in task_lower:
            return "TodoWriteTool", {"content": "New todo"}
        
        if 'fetch' in task_lower or 'url' in task_lower:
            return "WebFetchTool", {"url": "https://example.com"}
        
        if 'config' in task_lower:
            return "ConfigTool", {}
        
        if 'skill' in task_lower:
            return "SkillTool", {"action": "list"}
        
        # Default to bash for unknown tasks
        return "BashTool", {"command": "echo hello"}
    
    def validate_params(self, expected: Dict, predicted: Dict) -> bool:
        """Check if predicted parameters match expected."""
        # For simplicity, check if key parameters are present
        # In production, would use more sophisticated matching
        expected_keys = set(expected.keys())
        predicted_keys = set(predicted.keys())
        
        # Must have at least the key parameters
        return bool(expected_keys & predicted_keys)
    
    def execute_tool(self, tool: str, params: Dict) -> tuple[bool, Optional[str]]:
        """
        Execute a tool with given parameters.
        Returns (success, error_message).
        """
        try:
            if tool == "BashTool":
                cmd = params.get("command", "echo test")
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, timeout=5
                )
                return result.returncode == 0, None
            
            # For other tools, just simulate success
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def evaluate_single(self, test_case: ToolTestCase) -> ToolEvalResult:
        """Evaluate a single test case."""
        start_time = time.time()
        
        try:
            predicted_tool, predicted_params = self.predict_tool(test_case.task)
            
            tool_correct = predicted_tool == test_case.expected_tool
            params_correct = self.validate_params(
                test_case.expected_params, predicted_params
            )
            
            # Try to execute if tool is correct
            execution_success = False
            error = None
            if tool_correct:
                execution_success, error = self.execute_tool(
                    predicted_tool, predicted_params
                )
            
            return ToolEvalResult(
                category=test_case.category,
                task=test_case.task,
                expected_tool=test_case.expected_tool,
                predicted_tool=predicted_tool,
                tool_correct=tool_correct,
                params_correct=params_correct,
                execution_success=execution_success,
                error=error,
                latency_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return ToolEvalResult(
                category=test_case.category,
                task=test_case.task,
                expected_tool=test_case.expected_tool,
                predicted_tool=None,
                tool_correct=False,
                params_correct=False,
                execution_success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    def run_evaluation(self, sample_size: int = None) -> ToolEvalSummary:
        """Run full tool evaluation."""
        print(f"Starting Tool Use Evaluation for {self.model}")
        print(f"Total test cases: {len(self.test_cases)}")
        print("-" * 50)
        
        # Sample if needed for faster evaluation
        cases = self.test_cases
        if sample_size and sample_size < len(cases):
            cases = random.sample(cases, sample_size)
        
        results = []
        category_stats = {}
        
        for i, tc in enumerate(cases):
            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{len(cases)}")
            
            result = self.evaluate_single(tc)
            results.append(result.__dict__)
            
            # Track category stats
            if tc.category not in category_stats:
                category_stats[tc.category] = {
                    "total": 0, "tool_correct": 0, "params_correct": 0, "exec_success": 0
                }
            
            category_stats[tc.category]["total"] += 1
            if result.tool_correct:
                category_stats[tc.category]["tool_correct"] += 1
            if result.params_correct:
                category_stats[tc.category]["params_correct"] += 1
            if result.execution_success:
                category_stats[tc.category]["exec_success"] += 1
        
        # Calculate aggregate metrics
        total = len(results)
        tool_correct = sum(1 for r in results if r["tool_correct"])
        params_correct = sum(1 for r in results if r["params_correct"])
        exec_success = sum(1 for r in results if r["execution_success"])
        
        tool_accuracy = tool_correct / total if total > 0 else 0
        param_accuracy = params_correct / total if total > 0 else 0
        exec_rate = exec_success / total if total > 0 else 0
        overall = (tool_correct + params_correct) / (2 * total) if total > 0 else 0
        
        # Category breakdowns
        category_results = {}
        for cat, stats in category_stats.items():
            category_results[cat] = {
                "tool_selection_accuracy": stats["tool_correct"] / stats["total"],
                "parameter_accuracy": stats["params_correct"] / stats["total"],
                "execution_success_rate": stats["exec_success"] / stats["total"],
                "total_cases": stats["total"]
            }
        
        print(f"\nTotal Cases: {total}")
        print(f"Tool Selection Accuracy: {tool_accuracy:.2%}")
        print(f"Parameter Accuracy: {param_accuracy:.2%}")
        print(f"Execution Success Rate: {exec_rate:.2%}")
        print(f"Overall Success Rate: {overall:.2%}")
        
        return ToolEvalSummary(
            model=self.model,
            timestamp=datetime.now().isoformat(),
            total_cases=total,
            tool_selection_accuracy=tool_accuracy,
            parameter_accuracy=param_accuracy,
            execution_success_rate=exec_rate,
            overall_success_rate=overall,
            category_results=category_results,
            results=results
        )
    
    def save_results(self, summary: ToolEvalSummary, output_dir: str):
        """Save evaluation results."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON
        json_path = output_dir / "tool_use_results.json"
        with open(json_path, 'w') as f:
            json.dump(summary.__dict__, f, indent=2)
        
        # Summary report
        report_path = output_dir / "tool_use_report.md"
        with open(report_path, 'w') as f:
            f.write(f"# Tool Use Evaluation Report\n\n")
            f.write(f"**Model:** {summary.model}\n")
            f.write(f"**Date:** {summary.timestamp}\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"| Metric | Value |\n|--------|-------|\n")
            f.write(f"| Total Cases | {summary.total_cases} |\n")
            f.write(f"| Tool Selection Accuracy | {summary.tool_selection_accuracy:.2%} |\n")
            f.write(f"| Parameter Accuracy | {summary.parameter_accuracy:.2%} |\n")
            f.write(f"| Execution Success Rate | {summary.execution_success_rate:.2%} |\n")
            f.write(f"| **Overall Success Rate** | **{summary.overall_success_rate:.2%}** |\n\n")
            
            f.write(f"## Category Breakdown\n\n")
            f.write(f"| Category | Tool Acc | Param Acc | Exec Rate | Cases |\n")
            f.write(f"|----------|----------|-----------|-----------|-------|\n")
            for cat, stats in summary.category_results.items():
                f.write(f"| {cat} | {stats['tool_selection_accuracy']:.2%} | ")
                f.write(f"{stats['parameter_accuracy']:.2%} | ")
                f.write(f"{stats['execution_success_rate']:.2%} | ")
                f.write(f"{stats['total_cases']} |\n")
        
        print(f"\nResults saved to {output_dir}/")
        return json_path


def main():
    parser = argparse.ArgumentParser(description="Tool Use Evaluation")
    parser.add_argument("--model", default="stack-3.0", help="Model name")
    parser.add_argument("--output", default="./results", help="Output directory")
    parser.add_argument("--sample", type=int, default=None, help="Sample size (default: all)")
    
    args = parser.parse_args()
    
    evaluator = ToolUseEvaluator(model=args.model)
    results = evaluator.run_evaluation(sample_size=args.sample)
    evaluator.save_results(results, args.output)
    
    print("\n" + "=" * 50)
    print("TOOL USE EVALUATION COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()
