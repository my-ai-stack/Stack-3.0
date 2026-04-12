"""
Code Analysis Module

Provides static code analysis and quality checking.
"""

from typing import Dict, List, Optional, Any, Tuple
import re


class CodeAnalyzer:
    """Analyze code for quality, complexity, and issues."""

    def __init__(self):
        """Initialize code analyzer."""
        pass

    def analyze_complexity(self, code: str) -> Dict[str, Any]:
        """
        Analyze code complexity.

        Returns:
            Dictionary with complexity metrics
        """
        lines = code.split('\n')

        # Count functions/methods
        functions = re.findall(r'def\s+(\w+)', code)
        methods = re.findall(r'def\s+(\w+)\(self', code)
        classes = re.findall(r'class\s+(\w+)', code)

        # Count control structures
        if_statements = len(re.findall(r'\bif\s+', code))
        for_loops = len(re.findall(r'\bfor\s+', code))
        while_loops = len(re.findall(r'\bwhile\s+', code))
        try_blocks = len(re.findall(r'\btry\s+', code))

        # Cyclomatic complexity approximation
        complexity = 1 + if_statements + for_loops + while_loops + try_blocks

        # Count lines of code
        loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

        return {
            "lines_of_code": loc,
            "total_lines": len(lines),
            "functions": len(functions),
            "methods": len(methods),
            "classes": len(classes),
            "cyclomatic_complexity": complexity,
            "if_statements": if_statements,
            "for_loops": for_loops,
            "while_loops": while_loops,
        }

    def find_issues(self, code: str, language: str = "python") -> List[Dict[str, Any]]:
        """
        Find potential issues in code.

        Args:
            code: Source code
            language: Programming language

        Returns:
            List of issues found
        """
        issues = []

        # Common issues for Python
        if language == "python":
            issues.extend(self._check_python_issues(code))

        return issues

    def _check_python_issues(self, code: str) -> List[Dict[str, Any]]:
        """Check for Python-specific issues."""
        issues = []

        # Check for TODO/FIXME
        for i, line in enumerate(code.split('\n'), 1):
            if 'TODO' in line.upper() or 'FIXME' in line.upper():
                issues.append({
                    "type": "todo",
                    "severity": "info",
                    "line": i,
                    "message": "TODO/FIXME comment found",
                })

        # Check for empty except
        if re.search(r'except\s*:\s*\n\s*pass', code):
            issues.append({
                "type": "empty_except",
                "severity": "warning",
                "message": "Empty except block - errors are silently ignored",
            })

        # Check for hardcoded credentials
        if re.search(r'password\s*=\s*["\']', code, re.IGNORECASE):
            issues.append({
                "type": "hardcoded_credentials",
                "severity": "error",
                "message": "Potential hardcoded password found",
            })

        # Check for print statements (debugging)
        if re.search(r'\bprint\s*\(', code) and not code.startswith('# debug'):
            issues.append({
                "type": "debug_print",
                "severity": "info",
                "message": "Print statement found - may need removal",
            })

        # Check for long lines
        for i, line in enumerate(code.split('\n'), 1):
            if len(line) > 120:
                issues.append({
                    "type": "long_line",
                    "severity": "info",
                    "line": i,
                    "message": f"Line exceeds 120 characters ({len(line)} chars)",
                })

        # Check for global variables
        if re.search(r'^([A-Z_][A-Z0-9_]*)\s*=\s*', code, re.MULTILINE):
            issues.append({
                "type": "global_variable",
                "severity": "info",
                "message": "Potential global variable found",
            })

        return issues

    def suggest_improvements(self, code: str, language: str = "python") -> List[str]:
        """Suggest code improvements."""
        suggestions = []
        complexity = self.analyze_complexity(code)

        # Complexity suggestions
        if complexity["cyclomatic_complexity"] > 10:
            suggestions.append("High cyclomatic complexity - consider breaking into smaller functions")

        if complexity["lines_of_code"] > 500:
            suggestions.append("Large function - consider splitting into smaller modules")

        # Pattern suggestions
        if "except:" in code:
            suggestions.append("Use specific exception types instead of bare except")

        if "print(" in code:
            suggestions.append("Use logging instead of print statements for production code")

        if "==" in code and "None" in code:
            suggestions.append("Use 'is None' instead of '== None'")

        if re.search(r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(', code):
            suggestions.append("Use enumerate() instead of range(len())")

        return suggestions

    def detect_language(self, code: str) -> str:
        """Detect programming language from code."""
        # Python indicators
        if re.search(r'\bdef\s+\w+\s*\(', code) or re.search(r'\bimport\s+\w+', code):
            return "python"

        # JavaScript/TypeScript
        if re.search(r'\bfunction\s+\w+\s*\(', code) or re.search(r'const\s+\w+\s*=', code):
            return "javascript"

        # Java
        if re.search(r'\bpublic\s+class\s+\w+', code) or re.search(r'\bSystem\.out\.print', code):
            return "java"

        # Go
        if re.search(r'\bpackage\s+main', code) or re.search(r'\bfunc\s+\w+\s*\(', code):
            return "go"

        # Rust
        if re.search(r'\bfn\s+\w+\s*\(', code) or re.search(r'\blet\s+mut\s+', code):
            return "rust"

        # C/C++
        if re.search(r'#include\s*<', code) or re.search(r'\bint\s+main\s*\(', code):
            return "c"

        return "unknown"

    def calculate_maintainability_index(self, code: str) -> float:
        """Calculate maintainability index (0-100)."""
        complexity = self.analyze_complexity(code)
        loc = complexity["lines_of_code"]

        if loc == 0:
            return 100.0

        # Simplified maintainability index
        # Based on lines of code and complexity
        base = 100
        loc_penalty = min(loc / 100, 1) * 20
        complexity_penalty = min(complexity["cyclomatic_complexity"] / 20, 1) * 30

        index = base - loc_penalty - complexity_penalty
        return max(0, min(100, index))

    def get_code_summary(self, code: str) -> Dict[str, Any]:
        """Get comprehensive code summary."""
        language = self.detect_language(code)
        complexity = self.analyze_complexity(code)
        issues = self.find_issues(code, language)
        suggestions = self.suggest_improvements(code, language)
        maintainability = self.calculate_maintainability_index(code)

        return {
            "language": language,
            "complexity": complexity,
            "issues": issues,
            "issue_count": len(issues),
            "suggestions": suggestions,
            "maintainability_index": maintainability,
        }

    def __repr__(self) -> str:
        return "CodeAnalyzer()"
