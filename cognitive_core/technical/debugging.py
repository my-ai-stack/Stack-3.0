"""
Debugging Assistant Module

Provides debugging assistance and error analysis.
"""

from typing import Dict, List, Optional, Any, Tuple
import re


class DebuggingAssistant:
    """Helps debug code and analyze errors."""

    # Common error patterns and their explanations
    ERROR_PATTERNS = {
        "python": {
            "SyntaxError": {
                "description": "Python syntax is invalid",
                "common_causes": [
                    "Missing colon after if/for/while/function definitions",
                    "Mismatched parentheses or brackets",
                    "Incorrect indentation",
                    "Using Python 2 syntax in Python 3",
                ],
            },
            "NameError": {
                "description": "A variable or function name is not defined",
                "common_causes": [
                    "Typo in variable name",
                    "Variable used before assignment",
                    "Import statement missing",
                    "Scope issue - variable not accessible",
                ],
            },
            "TypeError": {
                "description": "Operation applied to wrong type",
                "common_causes": [
                    "Trying to concatenate incompatible types",
                    "Calling a non-callable as a function",
                    "Passing wrong number of arguments",
                    "Operation not supported for type",
                ],
            },
            "IndexError": {
                "description": "List index out of range",
                "common_causes": [
                    "Accessing index that doesn't exist",
                    "Empty list access",
                    "Off-by-one error",
                ],
            },
            "KeyError": {
                "description": "Dictionary key not found",
                "common_causes": [
                    "Accessing non-existent key",
                    "Typo in key name",
                    "Case sensitivity issue",
                ],
            },
            "AttributeError": {
                "description": "Object has no attribute",
                "common_causes": [
                    "Typo in attribute name",
                    "Object is None when trying to access attribute",
                    "Wrong type for this operation",
                ],
            },
            "ImportError": {
                "description": "Cannot import module",
                "common_causes": [
                    "Module not installed",
                    "Circular import",
                    "Module name typo",
                    "Missing __init__.py in package",
                ],
            },
            "ZeroDivisionError": {
                "description": "Division by zero",
                "common_causes": [
                    "Dividing by variable that could be zero",
                    "Modulo by zero",
                ],
            },
            "ValueError": {
                "description": "Value is inappropriate",
                "common_causes": [
                    "Invalid argument to function",
                    "Conversion failed (e.g., int('abc'))",
                    "Empty sequence in function expecting content",
                ],
            },
            "IndentationError": {
                "description": "Incorrect indentation",
                "common_causes": [
                    "Mixing tabs and spaces",
                    "Inconsistent indentation levels",
                    "Code not aligned properly",
                ],
            },
        },
        "javascript": {
            "ReferenceError": {
                "description": "Variable not defined",
                "common_causes": [
                    "Typo in variable name",
                    "Using let/const before declaration",
                ],
            },
            "TypeError": {
                "description": "Type operation failed",
                "common_causes": [
                    "Calling non-function",
                    "Cannot read property of undefined/null",
                ],
            },
            "SyntaxError": {
                "description": "Invalid syntax",
                "common_causes": [
                    "Missing closing bracket/parenthesis",
                    "Invalid string quotes",
                ],
            },
        },
    }

    def __init__(self):
        """Initialize debugging assistant."""
        pass

    def analyze_error(
        self,
        error_message: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Analyze an error message and provide debugging help.

        Args:
            error_message: The error message
            language: Programming language

        Returns:
            Dictionary with error analysis and suggestions
        """
        # Extract error type
        error_type = self._extract_error_type(error_message, language)

        # Get error info
        error_info = self.ERROR_PATTERNS.get(language, {}).get(error_type, {
            "description": "Unknown error",
            "common_causes": ["Check the error message for clues"],
        })

        # Generate debugging steps
        steps = self._generate_debug_steps(error_type, error_message, language)

        # Suggest fixes
        fixes = self._suggest_fixes(error_type, error_message, language)

        return {
            "error_type": error_type,
            "description": error_info["description"],
            "common_causes": error_info["common_causes"],
            "debug_steps": steps,
            "suggested_fixes": fixes,
        }

    def _extract_error_type(self, error_message: str, language: str) -> str:
        """Extract error type from error message."""
        # Look for common error patterns
        patterns = {
            "python": [
                (r"(\w+Error):", 1),
                (r"(\w+Exception):", 1),
            ],
            "javascript": [
                (r"(\w+Error):", 1),
                (r"(\w+TypeError):", 1),
            ],
        }

        for pattern, group in patterns.get(language, []):
            match = re.search(pattern, error_message)
            if match:
                return match.group(group)

        return "UnknownError"

    def _generate_debug_steps(
        self,
        error_type: str,
        error_message: str,
        language: str,
    ) -> List[str]:
        """Generate debugging steps for the error."""
        steps = [
            "1. Read the error message carefully - it tells you what went wrong",
            "2. Check the line number in the traceback",
            "3. Look at the context around that line",
        ]

        if error_type == "NameError":
            steps.extend([
                "4. Check if the variable is spelled correctly",
                "5. Verify the variable is defined before use",
                "6. Check if you need to import the module",
            ])
        elif error_type == "TypeError":
            steps.extend([
                "4. Check the types of variables involved",
                "5. Use print() or logging to debug values",
                "6. Use type() to check variable types",
            ])
        elif error_type == "IndexError":
            steps.extend([
                "4. Check the list length before accessing",
                "5. Consider using try/except for bounds",
                "6. Check if the list is empty",
            ])
        elif error_type == "ImportError":
            steps.extend([
                "4. Verify the package is installed (pip list / npm list)",
                "5. Check the package name is correct",
                "6. Try reinstalling the package",
            ])

        return steps

    def _suggest_fixes(
        self,
        error_type: str,
        error_message: str,
        language: str,
    ) -> List[str]:
        """Suggest fixes for the error."""
        fixes = []

        if error_type == "NameError":
            fixes.append("Check spelling of all variable/function names")
            fixes.append("Ensure variable is defined before use")
            fixes.append("Add necessary import statements")
        elif error_type == "TypeError":
            fixes.append("Convert types explicitly if needed")
            fixes.append("Check you're using the right operators")
            fixes.append("Verify function accepts the arguments given")
        elif error_type == "IndexError":
            fixes.append("Add bounds checking before access")
            fixes.append("Use .get() for dictionaries")
            fixes.append("Check if list is empty first")
        elif error_type == "SyntaxError":
            fixes.append("Check for missing colons, brackets, quotes")
            fixes.append("Verify indentation is consistent")
            fixes.append("Run a linter to find issues")

        return fixes

    def analyze_traceback(self, traceback: str) -> Dict[str, Any]:
        """
        Analyze a full traceback.

        Args:
            traceback: The full error traceback

        Returns:
            Dictionary with traceback analysis
        """
        lines = traceback.split('\n')

        # Extract file and line numbers
        file_lines = []
        for line in lines:
            if 'File "' in line or 'line ' in line:
                file_lines.append(line.strip())

        # Get the main error
        error_line = ""
        for line in lines:
            if 'Error:' in line or 'Exception:' in line:
                error_line = line.strip()
                break

        return {
            "files_involved": file_lines,
            "main_error": error_line,
            "frames": len([l for l in lines if 'File "' in l]),
        }

    def generate_debug_code(
        self,
        error_type: str,
        code_snippet: str,
    ) -> str:
        """Generate debugging code for the error."""
        debug_templates = {
            "NameError": f"""# Debug NameError
# Add debugging print statements
print(f"Variable value: {{variable_name}}")

# Check if defined
try:
    result = {code_snippet}
except NameError as e:
    print(f"NameError: {{e}}")""",

            "TypeError": f"""# Debug TypeError
# Add type checking
print(f"Type of variable: {{type(variable_name)}}")

# Add type hints for clarity
def debug_function(variable_name):
    print(f"Value: {{variable_name}}, Type: {{type(variable_name)}}")
    return variable_name""",

            "IndexError": f"""# Debug IndexError
# Add bounds checking
my_list = []

if len(my_list) > 0:
    print(f"List has {{len(my_list)}} items")
    # Access with safety
    result = my_list[0] if my_list else None""",

            "default": """# General debug approach
import traceback

try:
    # Your code here
    pass
except Exception as e:
    print(f"Error: {{e}}")
    traceback.print_exc()
    # Add your debugging here"""
        }

        return debug_templates.get(error_type, debug_templates["default"])

    def suggest_logging(self, code: str) -> str:
        """Suggest where to add logging statements."""
        suggestions = []

        # Suggest logging for function calls
        functions = re.findall(r'def\s+(\w+)\s*\(', code)
        for func in functions[:3]:  # Limit to 3
            suggestions.append(f"Add logging at start/end of function '{func}()'")

        # Suggest logging for error handling
        if "except" in code:
            suggestions.append("Add logging in exception handlers")

        # Suggest logging for loops
        if "for " in code:
            suggestions.append("Add logging in loops to track iterations")

        return suggestions if suggestions else ["Code looks simple, minimal logging needed"]

    def __repr__(self) -> str:
        return "DebuggingAssistant()"
