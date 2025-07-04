"""
Template Engine
Advanced Jinja2-based template rendering with custom filters and functions
"""
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError
import inflection

from ..utils.naming_conventions import NamingConventions, DjangoNamingHelper
from ..config.settings import Settings


class TemplateEngine:
    """
    Advanced template engine with Django-specific filters and functions.
    
    Features:
    - Custom filters for naming conventions
    - Django-specific template functions
    - Template inheritance and includes
    - Context processors
    - Template caching
    - Error handling and debugging
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.naming = NamingConventions()
        self.django_helper = DjangoNamingHelper()
        self.template_dirs = self._get_template_dirs()
        self.env = self._create_environment()
        self._template_cache: Dict[str, Template] = {}
        self._context_processors: List[Callable] = []
        
    def _get_template_dirs(self) -> List[str]:
        """Get template directories from settings and defaults."""
        template_dirs = []
        
        # Add default template directory
        default_dir = Path(__file__).parent.parent / 'templates'
        if default_dir.exists():
            template_dirs.append(str(default_dir))
        
        # Add custom template directories from settings
        custom_dirs = self.settings.get('template_dirs', [])
        for dir_path in custom_dirs:
            path = Path(dir_path)
            if path.exists():
                template_dirs.append(str(path))
        
        return template_dirs
    
    def _create_environment(self) -> Environment:
        """Create and configure Jinja2 environment."""
        env = Environment(
            loader=FileSystemLoader(self.template_dirs),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=jinja2.StrictUndefined,
        )
        
        # Register custom filters
        self._register_filters(env)
        
        # Register custom functions
        self._register_functions(env)
        
        # Register global variables
        self._register_globals(env)
        
        return env
    
    def _register_filters(self, env: Environment) -> None:
        """Register custom Jinja2 filters."""
        filters = {
            # Naming convention filters
            'snake_case': self.naming.to_snake_case,
            'pascal_case': self.naming.to_pascal_case,
            'camel_case': self.naming.to_camel_case,
            'kebab_case': self.naming.to_kebab_case,
            'constant_case': self.naming.to_constant_case,
            'title_case': self.naming.to_title_case,
            'human_readable': self.naming.to_human_readable,
            
            # Pluralization filters
            'plural': inflection.pluralize,
            'singular': inflection.singularize,
            'humanize': inflection.humanize,
            'underscore': inflection.underscore,
            'camelize': inflection.camelize,
            'dasherize': inflection.dasherize,
            
            # Django-specific filters
            'model_name': self.naming.to_django_model_name,
            'field_name': self.naming.to_django_field_name,
            'verbose_name': self.django_helper.get_verbose_name,
            'db_table': lambda app, model: self.django_helper.get_db_table_name(app, model),
            'admin_class': self.django_helper.get_admin_class_name,
            'form_class': self.django_helper.get_form_class_name,
            'serializer_class': self.django_helper.get_serializer_class_name,
            'viewset_class': self.django_helper.get_viewset_class_name,
            
            # Type conversion filters
            'python_type': self._get_python_type,
            'django_field': self._get_django_field_type,
            'graphql_type': self._get_graphql_type,
            'typescript_type': self._get_typescript_type,
            
            # String manipulation filters
            'indent': self._indent_filter,
            'comment': self._comment_filter,
            'docstring': self._docstring_filter,
            'quote': self._quote_filter,
            'escape_quotes': self._escape_quotes_filter,
            
            # Collection filters
            'unique': lambda x: list(dict.fromkeys(x)) if isinstance(x, list) else x,
            'sort_by': lambda x, key: sorted(x, key=lambda item: item.get(key, '')),
            'group_by': self._group_by_filter,
            'chunk': self._chunk_filter,
            
            # Conditional filters
            'default_if_none': lambda value, default: default if value is None else value,
            'yesno': lambda value, arg="yes,no": arg.split(',')[0 if value else 1],
            
            # File and path filters
            'basename': lambda path: os.path.basename(path),
            'dirname': lambda path: os.path.dirname(path),
            'ext': lambda path: os.path.splitext(path)[1],
            'no_ext': lambda path: os.path.splitext(path)[0],
            
            # Date and time filters
            'strftime': lambda dt, fmt='%Y-%m-%d %H:%M:%S': dt.strftime(fmt) if dt else '',
            'timestamp': lambda: datetime.now().timestamp(),
            'isoformat': lambda dt: dt.isoformat() if dt else '',
            
            # Code generation filters
            'imports': self._imports_filter,
            'class_methods': self._class_methods_filter,
            'field_definition': self._field_definition_filter,
        }
        
        env.filters.update(filters)
    
    def _register_functions(self, env: Environment) -> None:
        """Register custom Jinja2 functions."""
        functions = {
            'now': datetime.now,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'set': set,
            'tuple': tuple,
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'round': round,
            
            # Custom functions
            'get_related_name': self._get_related_name,
            'get_field_choices': self._get_field_choices,
            'get_model_permissions': self._get_model_permissions,
            'get_api_endpoint': self._get_api_endpoint,
            'get_url_pattern': self._get_url_pattern,
            'generate_uuid': self._generate_uuid,
            'get_import_statement': self._get_import_statement,
        }
        
        env.globals.update(functions)
    
    def _register_globals(self, env: Environment) -> None:
        """Register global variables."""
        globals_dict = {
            'generator_name': 'Django Enhanced Generator',
            'generator_version': '1.0.0',
            'python_version': self.settings.get('python_version', '3.11'),
            'django_version': self.settings.get('django_version', '4.2'),
            'settings': self.settings,
        }
        
        env.globals.update(globals_dict)
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Context dictionary for template rendering
            
        Returns:
            Rendered template string
            
        Raises:
            TemplateNotFound: If template file is not found
            TemplateSyntaxError: If template has syntax errors
        """
        # Process context with context processors
        processed_context = self._process_context(context)
        
        try:
            # Get template from cache or load it
            template = self._get_template(template_name)
            
            # Render template
            rendered = template.render(**processed_context)
            
            return rendered
            
        except TemplateNotFound:
            raise TemplateNotFound(f"Template '{template_name}' not found in directories: {self.template_dirs}")
        except TemplateSyntaxError as e:
            raise TemplateSyntaxError(f"Syntax error in template '{template_name}': {e}")
    
    def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Render a template string with the given context.
        
        Args:
            template_string: Template string to render
            context: Context dictionary for template rendering
            
        Returns:
            Rendered template string
        """
        # Process context with context processors
        processed_context = self._process_context(context)
        
        # Create template from string
        template = self.env.from_string(template_string)
        
        # Render template
        return template.render(**processed_context)
    
    def add_context_processor(self, processor: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Add a context processor function."""
        self._context_processors.append(processor)
    
    def _get_template(self, template_name: str) -> Template:
        """Get template from cache or load it."""
        if template_name not in self._template_cache:
            self._template_cache[template_name] = self.env.get_template(template_name)
        return self._template_cache[template_name]
    
    def _process_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process context with context processors."""
        processed_context = context.copy()
        
        for processor in self._context_processors:
            processed_context.update(processor(processed_context))
        
        return processed_context
    
    # Filter implementations
    
    def _indent_filter(self, text: str, spaces: int = 4, first_line: bool = False) -> str:
        """Indent text by specified number of spaces."""
        if not text:
            return text
        
        lines = text.split('\n')
        indent = ' ' * spaces
        
        if first_line:
            return '\n'.join(indent + line for line in lines)
        else:
            return lines[0] + '\n' + '\n'.join(indent + line for line in lines[1:])
    
    def _comment_filter(self, text: str, style: str = 'python') -> str:
        """Add comment markers to text."""
        if not text:
            return text
        
        comment_styles = {
            'python': '# ',
            'javascript': '// ',
            'css': '/* ',
            'html': '<!-- ',
            'sql': '-- ',
        }
        
        prefix = comment_styles.get(style, '# ')
        lines = text.split('\n')
        
        if style == 'css':
            return '/* ' + ' */\n/* '.join(lines) + ' */'
        elif style == 'html':
            return '<!-- ' + ' -->\n<!-- '.join(lines) + ' -->'
        else:
            return '\n'.join(prefix + line for line in lines)
    
    def _docstring_filter(self, text: str, style: str = 'google', indent: int = 4) -> str:
        """Format text as a Python docstring."""
        if not text:
            return '""""""'
        
        lines = text.strip().split('\n')
        
        if len(lines) == 1 and len(lines[0]) < 70:
            return f'"""{lines[0]}"""'
        
        # Multi-line docstring
        result = ['"""']
        result.extend(lines)
        result.append('"""')
        
        if indent > 0:
            indent_str = ' ' * indent
            return '\n'.join(indent_str + line if i > 0 else line for i, line in enumerate(result))
        
        return '\n'.join(result)
    
    def _quote_filter(self, text: str, quote_type: str = 'single') -> str:
        """Add quotes around text."""
        if quote_type == 'double':
            return f'"{text}"'
        elif quote_type == 'triple':
            return f'"""{text}"""'
        else:
            return f"'{text}'"
    
    def _escape_quotes_filter(self, text: str, quote_type: str = 'single') -> str:
        """Escape quotes in text."""
        if quote_type == 'double':
            return text.replace('"', '\\"')
        else:
            return text.replace("'", "\\'")
    
    def _group_by_filter(self, items: List[Dict], key: str) -> Dict[str, List]:
        """Group items by a key."""
        groups = {}
        for item in items:
            group_key = item.get(key)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        return groups
    
    def _chunk_filter(self, items: List, size: int) -> List[List]:
        """Split list into chunks of specified size."""
        return [items[i:i + size] for i in range(0, len(items), size)]
    
    def _imports_filter(self, imports: Dict[str, List[str]]) -> str:
        """Format import statements."""
        lines = []
        
        # Standard library imports
        if 'python' in imports:
            lines.extend(imports['python'])
            lines.append('')
        
        # Django imports
        if 'django' in imports:
            lines.extend(imports['django'])
            lines.append('')
        
        # Third-party imports
        if 'third_party' in imports:
            lines.extend(imports['third_party'])
            lines.append('')
        
        # Local imports
        if 'local' in imports:
            lines.extend(imports['local'])
        
        return '\n'.join(lines).strip()
    
    def _class_methods_filter(self, methods: List[Dict[str, Any]]) -> str:
        """Format class methods."""
        method_lines = []
        
        for method in methods:
            # Method signature
            params = ', '.join(method.get('params', []))
            signature = f"def {method['name']}(self{', ' + params if params else ''}):"
            
            # Docstring
            if method.get('description'):
                docstring = f'"""{method["description"]}"""'
                method_lines.extend([signature, f'    {docstring}'])
            else:
                method_lines.append(signature)
            
            # Method body
            body = method.get('body', 'pass')
            for line in body.split('\n'):
                method_lines.append(f'    {line}')
            
            method_lines.append('')  # Empty line between methods
        
        return '\n'.join(method_lines)
    
    def _field_definition_filter(self, field: Dict[str, Any]) -> str:
        """Format Django field definition."""
        field_type = field['type']
        options = []
        
        # Common options
        if field.get('max_length'):
            options.append(f"max_length={field['max_length']}")
        if field.get('null'):
            options.append("null=True")
        if field.get('blank'):
            options.append("blank=True")
        if field.get('default') is not None:
            default = field['default']
            if isinstance(default, str):
                options.append(f"default='{default}'")
            else:
                options.append(f"default={default}")
        if field.get('unique'):
            options.append("unique=True")
        if field.get('db_index'):
            options.append("db_index=True")
        
        # Field-specific options
        if field_type == 'DecimalField':
            if field.get('max_digits'):
                options.append(f"max_digits={field['max_digits']}")
            if field.get('decimal_places'):
                options.append(f"decimal_places={field['decimal_places']}")
        
        # Relationship fields
        if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
            to_model = field.get('to', 'self')
            options.insert(0, f"'{to_model}'")
            
            if field_type != 'ManyToManyField':
                on_delete = field.get('on_delete', 'CASCADE')
                options.append(f"on_delete=models.{on_delete}")
            
            if field.get('related_name'):
                options.append(f"related_name='{field['related_name']}'")
        
        # Auto fields
        if field.get('auto_now'):
            options.append("auto_now=True")
        if field.get('auto_now_add'):
            options.append("auto_now_add=True")
        
        options_str = ', '.join(options)
        return f"models.{field_type}({options_str})"
    
    # Type conversion methods
    
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
            'ForeignKey': 'Optional[int]',
            'OneToOneField': 'Optional[int]',
            'ManyToManyField': 'List[int]',
        }
        
        return type_mapping.get(django_field_type, 'Any')
    
    def _get_django_field_type(self, field_config: Dict[str, Any]) -> str:
        """Get Django field type with options."""
        return self._field_definition_filter(field_config)
    
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
            'ForeignKey': 'ID',
            'OneToOneField': 'ID',
            'ManyToManyField': '[ID]',
        }
        
        return type_mapping.get(django_field_type, 'String')
    
    def _get_typescript_type(self, django_field_type: str) -> str:
        """Convert Django field type to TypeScript type."""
        type_mapping = {
            'CharField': 'string',
            'TextField': 'string',
            'EmailField': 'string',
            'URLField': 'string',
            'SlugField': 'string',
            'IntegerField': 'number',
            'BigIntegerField': 'number',
            'SmallIntegerField': 'number',
            'PositiveIntegerField': 'number',
            'FloatField': 'number',
            'DecimalField': 'number',
            'BooleanField': 'boolean',
            'DateField': 'string',
            'DateTimeField': 'string',
            'TimeField': 'string',
            'JSONField': 'any',
            'UUIDField': 'string',
            'ForeignKey': 'number | null',
            'OneToOneField': 'number | null',
            'ManyToManyField': 'number[]',
        }
        
        return type_mapping.get(django_field_type, 'any')
    
    # Helper functions
    
    def _get_related_name(self, from_model: str, to_model: str, field_name: str) -> str:
        """Generate related_name for Django relationships."""
        return self.naming.to_django_related_name(from_model, to_model, field_name)
    
    def _get_field_choices(self, choices: Union[List, Dict]) -> str:
        """Format field choices for Django."""
        if isinstance(choices, dict):
            choice_list = [(k, v) for k, v in choices.items()]
        else:
            choice_list = choices
        
        formatted_choices = []
        for choice in choice_list:
            if isinstance(choice, (list, tuple)) and len(choice) >= 2:
                formatted_choices.append(f"('{choice[0]}', '{choice[1]}')")
            else:
                formatted_choices.append(f"('{choice}', '{choice}')")
        
        return '[' + ', '.join(formatted_choices) + ']'
    
    def _get_model_permissions(self, model_name: str) -> List[str]:
        """Get default Django model permissions."""
        model_lower = model_name.lower()
        return [
            f"('add_{model_lower}', 'Can add {model_name}')",
            f"('change_{model_lower}', 'Can change {model_name}')",
            f"('delete_{model_lower}', 'Can delete {model_name}')",
            f"('view_{model_lower}', 'Can view {model_name}')",
        ]
    
    def _get_api_endpoint(self, model_name: str, action: str = 'list') -> str:
        """Get API endpoint for model."""
        model_kebab = self.naming.to_kebab_case(model_name)
        model_plural = inflection.pluralize(model_kebab)
        
        if action == 'list':
            return f"/api/v1/{model_plural}/"
        elif action == 'detail':
            return f"/api/v1/{model_plural}/{{id}}/"
        else:
            return f"/api/v1/{model_plural}/{action}/"
    
    def _get_url_pattern(self, model_name: str, action: str = 'list') -> str:
        """Get URL pattern for model views."""
        model_kebab = self.naming.to_kebab_case(model_name)
        model_plural = inflection.pluralize(model_kebab)
        
        if action == 'list':
            return f"{model_plural}/"
        elif action == 'detail':
            return f"{model_plural}/<int:pk>/"
        elif action == 'create':
            return f"{model_plural}/create/"
        elif action == 'update':
            return f"{model_plural}/<int:pk>/update/"
        elif action == 'delete':
            return f"{model_plural}/<int:pk>/delete/"
        else:
            return f"{model_plural}/{action}/"
    
    def _generate_uuid(self) -> str:
        """Generate a UUID string."""
        import uuid
        return str(uuid.uuid4())
    
    def _get_import_statement(self, module: str, items: Union[str, List[str]]) -> str:
        """Generate import statement."""
        if isinstance(items, str):
            return f"from {module} import {items}"
        else:
            return f"from {module} import {', '.join(items)}"