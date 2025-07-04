"""
Base Generator Class
Foundation for all code generators in the system
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape
import inflection
import re
from datetime import datetime

from ..utils.code_formatter import CodeFormatter
from ..utils.naming_conventions import NamingConventions
from ..config.settings import Settings


class GeneratedFile:
    """Represents a generated file with metadata."""

    def __init__(self, path: str, content: str, file_type: str = 'python',
                 executable: bool = False, append: bool = False):
        self.path = path
        self.content = content
        self.file_type = file_type
        self.executable = executable
        self.append = append
        self.metadata = {
            'generated_at': datetime.now(),
            'generator': None,
            'template': None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'path': self.path,
            'content': self.content,
            'file_type': self.file_type,
            'executable': self.executable,
            'append': self.append,
            'metadata': self.metadata
        }


class BaseGenerator(ABC):
    """
    Abstract base class for all generators.

    Provides common functionality for:
    - Template rendering with Jinja2
    - Code formatting
    - File generation
    - Naming conventions
    """

    # Generator metadata
    name: str = "BaseGenerator"
    description: str = "Base generator class"
    version: str = "1.0.0"

    # Generator configuration
    requires: Set[str] = set()  # Required features/generators
    provides: Set[str] = set()  # Features this generator provides
    order: int = 100  # Execution order (lower = earlier)

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.formatter = CodeFormatter(self.settings)
        self.naming = NamingConventions()
        self._setup_template_environment()
        self.generated_files: List[GeneratedFile] = []

    def _setup_template_environment(self) -> None:
        """Setup Jinja2 template environment."""
        # Get template directories
        template_dirs = [
            Path(__file__).parent.parent / 'templates',
            ]

        # Add custom template directories from settings
        if self.settings.get('template_dirs'):
            template_dirs.extend([Path(d) for d in self.settings.get('template_dirs')])

        # Create Jinja2 environment
        self.template_env = Environment(
            loader=FileSystemLoader([str(d) for d in template_dirs if d.exists()]),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Add custom filters
        self._register_template_filters()

        # Add custom globals
        self._register_template_globals()

    def _register_template_filters(self) -> None:
        """Register custom Jinja2 filters."""
        filters = {
            # String manipulation
            'snake_case': self.naming.to_snake_case,
            'camel_case': self.naming.to_camel_case,
            'pascal_case': self.naming.to_pascal_case,
            'kebab_case': self.naming.to_kebab_case,
            'title_case': self.naming.to_title_case,
            'plural': inflection.pluralize,
            'singular': inflection.singularize,
            'humanize': inflection.humanize,

            # Django specific
            'model_name': lambda x: self.naming.to_pascal_case(inflection.singularize(x)),
            'app_label': lambda x: self.naming.to_snake_case(x),
            'verbose_name': lambda x: inflection.humanize(inflection.underscore(x)),
            'db_table': lambda x: self.naming.to_snake_case(inflection.pluralize(x)),

            # Type conversions
            'python_type': self._get_python_type,
            'django_field': self._get_django_field_type,
            'graphql_type': self._get_graphql_type,

            # Formatting
            'indent': lambda text, spaces=4: '\n'.join(' ' * spaces + line for line in text.split('\n')),
            'comment': lambda text: '\n'.join('# ' + line for line in text.split('\n')),
            'docstring': self._format_docstring,

            # Collections
            'unique': lambda x: list(dict.fromkeys(x)) if isinstance(x, list) else x,
            'sort_by': lambda x, key: sorted(x, key=lambda item: item.get(key, '')),
        }

        self.template_env.filters.update(filters)

    def _register_template_globals(self) -> None:
        """Register global variables available in all templates."""
        globals_dict = {
            'now': datetime.now,
            'generator_name': self.name,
            'generator_version': self.version,
            'python_version': self.settings.get('python_version', '3.11'),
            'django_version': self.settings.get('django_version', '4.2'),
        }

        self.template_env.globals.update(globals_dict)

    @abstractmethod
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """
        Check if this generator can handle the given schema.

        Args:
            schema: Parsed schema dictionary

        Returns:
            True if generator can handle schema, False otherwise
        """
        pass

    @abstractmethod
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """
        Generate files based on schema.

        Args:
            schema: Parsed schema dictionary
            context: Additional context for generation

        Returns:
            List of generated files
        """
        pass

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with context.

        Args:
            template_name: Name of template file
            context: Context dictionary for template

        Returns:
            Rendered template string
        """
        try:
            template = self.template_env.get_template(template_name)
            rendered = template.render(**context)

            # Format based on file type
            if template_name.endswith('.py.j2'):
                rendered = self.formatter.format_python(rendered)
            elif template_name.endswith(('.yml.j2', '.yaml.j2')):
                rendered = self.formatter.format_yaml(rendered)
            elif template_name.endswith('.json.j2'):
                rendered = self.formatter.format_json(rendered)

            return rendered

        except jinja2.TemplateNotFound:
            raise ValueError(f"Template not found: {template_name}")
        except jinja2.TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error in {template_name}: {e}")

    def create_file(self, path: str, content: str, **kwargs) -> GeneratedFile:
        """
        Create a generated file object.

        Args:
            path: File path relative to output directory
            content: File content
            **kwargs: Additional file metadata

        Returns:
            GeneratedFile object
        """
        # Determine file type from extension
        file_type = self._get_file_type(path)

        # Create file object
        generated_file = GeneratedFile(
            path=path,
            content=content,
            file_type=file_type,
            **kwargs
        )

        # Add metadata
        generated_file.metadata['generator'] = self.name

        # Add to tracked files
        self.generated_files.append(generated_file)

        return generated_file

    def create_file_from_template(self, template_name: str, output_path: str,
                                  context: Dict[str, Any], **kwargs) -> GeneratedFile:
        """
        Create a file from a template.

        Args:
            template_name: Template file name
            output_path: Output file path
            context: Template context
            **kwargs: Additional file metadata

        Returns:
            GeneratedFile object
        """
        content = self.render_template(template_name, context)
        generated_file = self.create_file(output_path, content, **kwargs)
        generated_file.metadata['template'] = template_name
        return generated_file

    # Helper methods

    def _get_file_type(self, path: str) -> str:
        """Determine file type from path."""
        ext_mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.md': 'markdown',
            '.txt': 'text',
            '.sh': 'shell',
            '.dockerfile': 'dockerfile',
            'Dockerfile': 'dockerfile',
        }

        path_obj = Path(path)
        ext = path_obj.suffix.lower()

        # Check full filename first (for Dockerfile, etc.)
        if path_obj.name in ext_mapping:
            return ext_mapping[path_obj.name]

        return ext_mapping.get(ext, 'text')

    def _get_python_type(self, django_field_type: str) -> str:
        """Convert Django field type to Python type hint."""
        type_mapping = {
            'CharField': 'str',
            'TextField': 'str',
            'EmailField': 'str',
            'URLField': 'str',
            'SlugField': 'str',
            'IntegerField': 'int',
            'BigIntegerField': 'int',
            'SmallIntegerField': 'int',
            'PositiveIntegerField': 'int',
            'FloatField': 'float',
            'DecimalField': 'Decimal',
            'BooleanField': 'bool',
            'DateField': 'date',
            'DateTimeField': 'datetime',
            'TimeField': 'time',
            'DurationField': 'timedelta',
            'FileField': 'str',
            'ImageField': 'str',
            'JSONField': 'Dict[str, Any]',
            'ArrayField': 'List[Any]',
            'UUIDField': 'UUID',
        }

        # Handle relationship fields
        if django_field_type in ['ForeignKey', 'OneToOneField']:
            return 'Optional[int]'  # FK stores ID
        elif django_field_type == 'ManyToManyField':
            return 'List[int]'  # M2M stores list of IDs

        return type_mapping.get(django_field_type, 'Any')

    def _get_django_field_type(self, field_config: Dict[str, Any]) -> str:
        """Get full Django field type with options."""
        field_type = field_config['type']
        options = []

        # Common options
        if field_config.get('max_length'):
            options.append(f"max_length={field_config['max_length']}")
        if field_config.get('null'):
            options.append("null=True")
        if field_config.get('blank'):
            options.append("blank=True")
        if field_config.get('default') is not None:
            default = field_config['default']
            if isinstance(default, str):
                options.append(f"default='{default}'")
            else:
                options.append(f"default={default}")
        if field_config.get('unique'):
            options.append("unique=True")
        if field_config.get('db_index'):
            options.append("db_index=True")

        # Field-specific options
        if field_type == 'DecimalField':
            if field_config.get('max_digits'):
                options.append(f"max_digits={field_config['max_digits']}")
            if field_config.get('decimal_places'):
                options.append(f"decimal_places={field_config['decimal_places']}")

        # Relationship fields
        if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
            to_model = field_config.get('to', 'self')
            on_delete = field_config.get('on_delete', 'CASCADE')
            related_name = field_config.get('related_name')

            if field_type != 'ManyToManyField':
                options.insert(0, f"on_delete=models.{on_delete}")
            if related_name:
                options.append(f"related_name='{related_name}'")

            options_str = ', '.join(options)
            return f"models.{field_type}('{to_model}', {options_str})"

        # Auto fields
        if field_config.get('auto_now'):
            options.append("auto_now=True")
        if field_config.get('auto_now_add'):
            options.append("auto_now_add=True")

        options_str = ', '.join(options)
        if options_str:
            return f"models.{field_type}({options_str})"
        else:
            return f"models.{field_type}()"

    def _get_graphql_type(self, django_field_type: str) -> str:
        """Convert Django field type to GraphQL type."""
        type_mapping = {
            'CharField': 'String',
            'TextField': 'String',
            'EmailField': 'String',
            'URLField': 'String',
            'SlugField': 'String',
            'IntegerField': 'Int',
            'BigIntegerField': 'Int',
            'SmallIntegerField': 'Int',
            'PositiveIntegerField': 'Int',
            'FloatField': 'Float',
            'DecimalField': 'Float',
            'BooleanField': 'Boolean',
            'DateField': 'Date',
            'DateTimeField': 'DateTime',
            'TimeField': 'Time',
            'JSONField': 'JSONString',
            'UUIDField': 'UUID',
        }

        return type_mapping.get(django_field_type, 'String')

    def _format_docstring(self, text: str, indent: int = 4) -> str:
        """Format text as a Python docstring."""
        lines = text.strip().split('\n')
        if len(lines) == 1:
            return f'"""{lines[0]}"""'

        result = ['"""']
        result.extend(lines)
        result.append('"""')

        indentation = ' ' * indent
        return '\n'.join(indentation + line if i > 0 else line
                         for i, line in enumerate(result))

    def validate_schema(self, schema: Dict[str, Any]) -> None:
        """
        Validate schema for this generator.
        Override in subclasses for specific validation.
        """
        pass

    def get_dependencies(self) -> Set[str]:
        """Get generator dependencies."""
        return self.requires

    def get_provides(self) -> Set[str]:
        """Get features this generator provides."""
        return self.provides