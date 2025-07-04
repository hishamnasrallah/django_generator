"""
Code Formatter
Formats generated code according to standards
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import json
import yaml
import re
import ast
import textwrap

try:
    import black
    HAS_BLACK = True
except ImportError:
    HAS_BLACK = False

try:
    import isort
    HAS_ISORT = True
except ImportError:
    HAS_ISORT = False

try:
    import autopep8
    HAS_AUTOPEP8 = True
except ImportError:
    HAS_AUTOPEP8 = False


class CodeFormatter:
    """
    Formats code according to configured standards.

    Supports:
    - Python (black, isort, autopep8)
    - JSON
    - YAML
    - JavaScript/TypeScript (prettier if available)
    - HTML/CSS (beautifulsoup if available)
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        self.settings = settings or {}
        self.python_formatter = self.settings.get('python_formatter', 'black')
        self.line_length = self.settings.get('line_length', 88)
        self.indent_size = self.settings.get('indent_size', 4)
        self.use_tabs = self.settings.get('use_tabs', False)

    def format_python(self, code: str) -> str:
        """
        Format Python code.

        Args:
            code: Python code to format

        Returns:
            Formatted Python code
        """
        # First, ensure the code is syntactically valid
        try:
            ast.parse(code)
        except SyntaxError:
            # If not valid, try to fix common issues
            code = self._fix_python_syntax(code)

        # Apply import sorting
        if HAS_ISORT:
            code = self._format_python_imports(code)

        # Apply code formatting
        if self.python_formatter == 'black' and HAS_BLACK:
            code = self._format_python_black(code)
        elif self.python_formatter == 'autopep8' and HAS_AUTOPEP8:
            code = self._format_python_autopep8(code)
        else:
            # Fallback to basic formatting
            code = self._format_python_basic(code)

        return code

    def format_json(self, content: str) -> str:
        """Format JSON content."""
        try:
            # Parse and reformat
            data = json.loads(content)
            return json.dumps(
                data,
                indent=self.indent_size,
                sort_keys=True,
                ensure_ascii=False
            )
        except json.JSONDecodeError:
            # Return original if not valid JSON
            return content

    def format_yaml(self, content: str) -> str:
        """Format YAML content."""
        try:
            # Parse and reformat
            data = yaml.safe_load(content)
            return yaml.dump(
                data,
                default_flow_style=False,
                sort_keys=True,
                indent=self.indent_size,
                allow_unicode=True
            )
        except yaml.YAMLError:
            # Return original if not valid YAML
            return content

    def format_javascript(self, code: str) -> str:
        """Format JavaScript/TypeScript code."""
        # Try to use prettier if available
        prettier_path = self._find_prettier()
        if prettier_path:
            return self._format_with_prettier(code, 'javascript')

        # Fallback to basic formatting
        return self._format_javascript_basic(code)

    def format_html(self, content: str) -> str:
        """Format HTML content."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            return soup.prettify(indent_width=self.indent_size)
        except ImportError:
            # Fallback to basic formatting
            return self._format_html_basic(content)

    def format_css(self, content: str) -> str:
        """Format CSS content."""
        # Try to use prettier if available
        prettier_path = self._find_prettier()
        if prettier_path:
            return self._format_with_prettier(content, 'css')

        # Fallback to basic formatting
        return self._format_css_basic(content)

    def format_file(self, file_path: str, content: str) -> str:
        """Format content based on file extension."""
        path = Path(file_path)
        ext = path.suffix.lower()

        format_map = {
            '.py': self.format_python,
            '.json': self.format_json,
            '.yaml': self.format_yaml,
            '.yml': self.format_yaml,
            '.js': self.format_javascript,
            '.ts': self.format_javascript,
            '.jsx': self.format_javascript,
            '.tsx': self.format_javascript,
            '.html': self.format_html,
            '.htm': self.format_html,
            '.css': self.format_css,
            '.scss': self.format_css,
            '.sass': self.format_css,
        }

        formatter = format_map.get(ext)
        if formatter:
            return formatter(content)

        return content

    def _format_python_black(self, code: str) -> str:
        """Format Python code with black."""
        try:
            return black.format_str(
                code,
                mode=black.Mode(
                    line_length=self.line_length,
                    string_normalization=True,
                    is_pyi=False,
                )
            )
        except Exception:
            # Fallback to basic formatting
            return self._format_python_basic(code)

    def _format_python_autopep8(self, code: str) -> str:
        """Format Python code with autopep8."""
        try:
            return autopep8.fix_code(
                code,
                options={
                    'max_line_length': self.line_length,
                    'aggressive': 1,
                }
            )
        except Exception:
            return self._format_python_basic(code)

    def _format_python_imports(self, code: str) -> str:
        """Sort Python imports with isort."""
        try:
            return isort.code(
                code,
                line_length=self.line_length,
                multi_line_output=3,  # Vertical hanging indent
                include_trailing_comma=True,
                force_grid_wrap=0,
                use_parentheses=True,
                ensure_newline_before_comments=True,
            )
        except Exception:
            return code

    def _format_python_basic(self, code: str) -> str:
        """Basic Python formatting without external tools."""
        # Fix indentation
        lines = code.split('\n')
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()

            # Decrease indent for these keywords
            if stripped.startswith(('elif', 'else:', 'except:', 'finally:', 'case')):
                indent_level = max(0, indent_level - 1)

            # Format the line
            if stripped:
                formatted_lines.append(' ' * (indent_level * self.indent_size) + stripped)
            else:
                formatted_lines.append('')

            # Increase indent after these patterns
            if stripped.endswith(':') and not stripped.startswith('#'):
                indent_level += 1

            # Handle multiline strings and comments
            if stripped.startswith(('"""', "'''")):
                in_multiline = True

        return '\n'.join(formatted_lines)

    def _fix_python_syntax(self, code: str) -> str:
        """Fix common Python syntax issues."""
        # Remove trailing commas in function definitions
        code = re.sub(r',\s*\)', ')', code)

        # Fix missing colons
        code = re.sub(r'^\s*(if|elif|else|for|while|with|def|class|try|except|finally)\s+.*[^:]\s*$',
                      r'\g<0>:', code, flags=re.MULTILINE)

        # Fix inconsistent indentation
        lines = code.split('\n')
        fixed_lines = []

        for line in lines:
            # Convert tabs to spaces
            if '\t' in line:
                line = line.replace('\t', ' ' * self.indent_size)
            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _format_javascript_basic(self, code: str) -> str:
        """Basic JavaScript formatting."""
        # Add semicolons where missing
        code = re.sub(r'([^{};,\s])\s*\n', r'\1;\n', code)

        # Fix indentation (simplified)
        lines = code.split('\n')
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()

            # Decrease indent for closing braces
            if stripped.startswith('}') or stripped.startswith(']'):
                indent_level = max(0, indent_level - 1)

            # Format the line
            if stripped:
                formatted_lines.append(' ' * (indent_level * self.indent_size) + stripped)
            else:
                formatted_lines.append('')

            # Increase indent after opening braces
            if stripped.endswith('{') or stripped.endswith('['):
                indent_level += 1

        return '\n'.join(formatted_lines)

    def _format_html_basic(self, content: str) -> str:
        """Basic HTML formatting."""
        # Simple indentation for HTML
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                formatted_lines.append('')
                continue

            # Decrease indent for closing tags
            if stripped.startswith('</') or stripped == '>':
                indent_level = max(0, indent_level - 1)

            # Format the line
            formatted_lines.append(' ' * (indent_level * self.indent_size) + stripped)

            # Increase indent after opening tags (not self-closing)
            if stripped.startswith('<') and not stripped.startswith('</') and not stripped.endswith('/>'):
                if '>' in stripped and '</' not in stripped:
                    indent_level += 1

        return '\n'.join(formatted_lines)

    def _format_css_basic(self, content: str) -> str:
        """Basic CSS formatting."""
        # Format CSS with proper indentation
        content = re.sub(r'\s*{\s*', ' {\n', content)
        content = re.sub(r';\s*', ';\n', content)
        content = re.sub(r'\s*}\s*', '\n}\n\n', content)

        # Fix indentation
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.endswith('}'):
                indent_level = max(0, indent_level - 1)
                formatted_lines.append(' ' * (indent_level * self.indent_size) + stripped)
            elif stripped.endswith('{'):
                formatted_lines.append(' ' * (indent_level * self.indent_size) + stripped)
                indent_level += 1
            else:
                formatted_lines.append(' ' * (indent_level * self.indent_size) + stripped)

        return '\n'.join(formatted_lines)

    def _find_prettier(self) -> Optional[str]:
        """Find prettier executable."""
        # Check if prettier is available
        try:
            result = subprocess.run(
                ['prettier', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return 'prettier'
        except FileNotFoundError:
            pass

        # Check common locations
        common_paths = [
            'node_modules/.bin/prettier',
            '../node_modules/.bin/prettier',
            '../../node_modules/.bin/prettier',
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return None

    def _format_with_prettier(self, content: str, parser: str) -> str:
        """Format code using prettier."""
        prettier_path = self._find_prettier()
        if not prettier_path:
            return content

        try:
            # Write to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{parser}', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # Run prettier
            result = subprocess.run(
                [prettier_path, '--parser', parser, tmp_path],
                capture_output=True,
                text=True
            )

            # Read formatted content
            if result.returncode == 0:
                with open(tmp_path, 'r') as f:
                    formatted = f.read()
                return formatted

            return content

        except Exception:
            return content
        finally:
            # Clean up
            if 'tmp_path' in locals():
                Path(tmp_path).unlink(missing_ok=True)


class DocstringFormatter:
    """Formats Python docstrings according to conventions."""

    def __init__(self, style: str = "google"):
        self.style = style  # google, numpy, sphinx

    def format_docstring(self, docstring: str, indent: int = 4) -> str:
        """Format a docstring according to the configured style."""
        if not docstring:
            return '""""""'

        lines = docstring.strip().split('\n')
        if len(lines) == 1 and len(lines[0]) < 70:
            # Single line docstring
            return f'"""{lines[0]}"""'

        # Multi-line docstring
        formatted_lines = ['"""']
        formatted_lines.extend(lines)
        formatted_lines.append('"""')

        # Apply indentation
        indent_str = ' ' * indent
        return '\n'.join(
            indent_str + line if i > 0 else line
            for i, line in enumerate(formatted_lines)
        )