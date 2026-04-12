"""
Code quality evaluation for Stack 3.0
Assesses syntactic correctness, style compliance, complexity, and bug potential
"""

import os
import ast
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple
import radon
from radon.complexity import cc_visit, cc_rank
from radon.raw import analyze
from radon.metrics import h_visit, h_visit_ast

class CodeQualityEvaluator:
    def __init__(self, code_directory: str = "."):
        self.code_directory = Path(code_directory)
        self.results = {}
        self.issues = []
    
    def evaluate_directory(self) -> Dict[str, Any]:
        """Evaluate all Python files in a directory"""
        print(f"Evaluating code quality in {self.code_directory}...")
        
        python_files = list(self.code_directory.rglob("*.py"))
        print(f"Found {len(python_files)} Python files")
        
        for file_path in python_files:
            self._evaluate_file(file_path)
        
        return {
            "summary": self._generate_summary(),
            "detailed_results": self.results,
            "issues": self.issues
        }
    
    def _evaluate_file(self, file_path: Path) -> None:
        """Evaluate a single Python file"""
        print(f"Evaluating {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self._log_issue(file_path, f"Error reading file: {e}")
            return
        
        # Syntactic correctness
        syntax_result = self._check_syntax(content, file_path)
        
        # Style compliance (PEP8)
        style_result = self._check_style(file_path)
        
        # Complexity metrics
        complexity_result = self._analyze_complexity(content, file_path)
        
        # Bug potential analysis
        bug_result = self._analyze_bugs(content, file_path)
        
        self.results[str(file_path)] = {
            "syntax": syntax_result,
            "style": style_result,
            "complexity": complexity_result,
            "bug_potential": bug_result
        }
    
    def _check_syntax(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Check syntactic correctness"""
        try:
            ast.parse(content)
            return {
                "valid": True,
                "errors": []
            }
        except SyntaxError as e:
            self._log_issue(file_path, f"Syntax error: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "line": e.lineno,
                "offset": e.offset
            }
        except Exception as e:
            self._log_issue(file_path, f"Unexpected error: {e}")
            return {
                "valid": False,
                "errors": [str(e)]
            }
    
    def _check_style(self, file_path: Path) -> Dict[str, Any]:
        """Check style compliance using pycodestyle"""
        try:
            # Run pycodestyle
            result = subprocess.run([
                "pycodestyle", 
                str(file_path),
                "--ignore=E501,W503"  # Ignore line length and operator issues
            ], capture_output=True, text=True)
            
            errors = result.stdout.strip().split('\n') if result.stdout else []
            error_count = len(errors)
            
            return {
                "compliant": error_count == 0,
                "errors": errors,
                "error_count": error_count,
                "total_warnings": len([e for e in errors if 'warning' in e.lower()]),
                "total_errors": len([e for e in errors if 'error' in e.lower()])
            }
            
        except FileNotFoundError:
            self._log_issue(file_path, "pycodestyle not found")
            return {
                "compliant": False,
                "errors": ["pycodestyle not installed"],
                "error_count": 1
            }
        except Exception as e:
            self._log_issue(file_path, f"Style check error: {e}")
            return {
                "compliant": False,
                "errors": [str(e)],
                "error_count": 1
            }
    
    def _analyze_complexity(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Analyze code complexity using radon"""
        try:
            # Cyclomatic complexity
            cc_results = cc_visit(content)
            
            # Halstead metrics
            h_results = h_visit(content)
            
            # Raw metrics
            raw_results = analyze(content)
            
            return {
                "cyclomatic_complexity": {
                    "average": sum(cc.rank for cc in cc_results) / len(cc_results) if cc_results else 0,
                    "max": max(cc.rank for cc in cc_results) if cc_results else 0,
                    "functions": [{
                        "name": cc.name,
                        "complexity": cc.rank,
                        "lineno": cc.lineno
                    } for cc in cc_results]
                },
                "halstead": {
                    "effort": h_results.effort,
                    "volume": h_results.volume,
                    "difficulty": h_results.difficulty
                },
                "raw": {
                    "loc": raw_results.loc,
                    "lloc": raw_results.lloc,
                    "sloc": raw_results.sloc,
                    "comments": raw_results.comments
                }
            }
            
        except Exception as e:
            self._log_issue(file_path, f"Complexity analysis error: {e}")
            return {
                "error": str(e)
            }
    
    def _analyze_bugs(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Analyze potential bugs"""
        issues = []
        
        # Check for common bug patterns
        tree = ast.parse(content)
        
        # Check for bare except statements
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({
                    "type": "bare_except",
                    "lineno": node.lineno,
                    "message": "Bare except clause found"
                })
        
        # Check for mutable default arguments
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append({
                            "type": "mutable_default",
                            "lineno": default.lineno,
                            "message": "Mutable default argument found"
                        })
        
        return {
            "potential_issues": issues,
            "issue_count": len(issues)
        }
    
    def _log_issue(self, file_path: Path, message: str) -> None:
        """Log an issue"""
        self.issues.append({
            "file": str(file_path),
            "message": message
        })
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        total_files = len(self.results)
        
        syntax_errors = sum(1 for r in self.results.values() if not r["syntax"]["valid"])
        style_errors = sum(r["style"]["error_count"] for r in self.results.values())
        
        return {
            "total_files": total_files,
            "syntax_errors": syntax_errors,
            "style_errors": style_errors,
            "average_complexity": self._calculate_average_complexity(),
            "total_issues": len(self.issues)
        }
    
    def _calculate_average_complexity(self) -> float:
        """Calculate average cyclomatic complexity"""
        complexities = []
        for result in self.results.values():
            if "complexity" in result and "cyclomatic_complexity" in result["complexity"]:
                complexities.append(result["complexity"]["cyclomatic_complexity"]["average"])
        
        return sum(complexities) / len(complexities) if complexities else 0
    
    def generate_report(self) -> str:
        """Generate markdown report"""
        summary = self._generate_summary()
        
        report = f"""# Code Quality Evaluation Report

## Summary
Evaluation of code quality for Stack 3.0.

## Overall Statistics

| Metric | Value |
|--------|-------|
| Total Files Evaluated | {summary[\"total_files\"]} |
| Files with Syntax Errors | {summary[\"syntax_errors\"]} |
| Total Style Issues | {summary[\"style_errors\"]} |
| Average Cyclomatic Complexity | {summary[\"average_complexity"]:.2f} |
| Total Issues Found | {summary[\"total_issues\"]} |

## Detailed Results

"""
        
        for file_path, result in self.results.items():
            report += f"""### {file_path}

- **Syntax**: {\"Valid\" if result[\"syntax\"][\"valid\"] else \"Invalid\"}
- **Style Issues**: {result[\"style\"][\"error_count\"]}
- **Cyclomatic Complexity**: {result[\"complexity\"][\"cyclomatic_complexity\"][\"average\"]:.2f}
- **Bug Potential Issues**: {result[\"bug_potential\"][\"issue_count\"]}

"""
        
        if self.issues:
            report += """## Issues

"""
            for issue in self.issues:
                report += f"""- **{issue[\"file\"]}** {issue[\"message\"]}

"""
        
        return report


if __name__ == "__main__":
    evaluator = CodeQualityEvaluator()
    results = evaluator.evaluate_directory()
    
    print("Code Quality Evaluation Complete!")
    print(json.dumps(results, indent=2))
    
    report = evaluator.generate_report()
    print(report)
    
    # Save results
    with open("results/code_quality_evaluation.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    with open("results/code_quality_report.md", 'w') as f:
        f.write(report)