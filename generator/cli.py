#!/usr/bin/env python
"""
Django Enhanced Generator CLI
Advanced code generation for production-ready Django applications
"""
import sys
import click
import yaml
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from .core.schema_parser import SchemaParser, SchemaValidationError
from .core.project_analyzer import ProjectAnalyzer
from .core.generator_registry import GeneratorRegistry
from .utils.file_system import FileSystemManager
from .config.settings import Settings

console = Console()

@click.group()
@click.version_option(version='1.0.0', prog_name='Django Enhanced Generator')
@click.pass_context
def cli(ctx):
    """
    Django Enhanced Generator - Generate production-ready Django code.

    This tool helps you create complete Django applications with:
    • Models, APIs, and Admin interfaces
    • Authentication and Authorization
    • Testing infrastructure
    • Docker and Kubernetes deployment
    • Performance optimization
    • Business logic frameworks
    """
    ctx.ensure_object(dict)
    ctx.obj['settings'] = Settings()
    ctx.obj['console'] = console

@cli.command()
@click.argument('schema_file', type=click.Path(exists=True))
@click.option('--output-dir', '-o', default='.', help='Output directory for generated code')
@click.option('--config', '-c', type=click.Path(), help='Configuration file (YAML/JSON)')
@click.option('--dry-run', is_flag=True, help='Show what would be generated without creating files')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing files without prompting')
@click.option('--features', '-F', multiple=True, help='Enable specific features (e.g., -F graphql -F websockets)')
@click.option('--exclude', '-E', multiple=True, help='Exclude specific components (e.g., -E tests -E docker)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.pass_context
def generate(ctx, schema_file, output_dir, config, dry_run, force, features, exclude, verbose):
    """Generate Django project from schema file."""
    console = ctx.obj['console']
    settings = ctx.obj['settings']

    # Show banner
    console.print(Panel.fit(
        "[bold blue]Django Enhanced Generator[/bold blue]\n"
        "Generating production-ready Django code...",
        border_style="blue"
    ))

    try:
        # Load schema
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:
            # Load schema file
            task = progress.add_task("Loading schema...", total=None)
            schema = _load_schema_file(schema_file)
            progress.update(task, completed=True)

            # Load configuration
            if config:
                task = progress.add_task("Loading configuration...", total=None)
                config_data = _load_config_file(config)
                settings.update(config_data)
                progress.update(task, completed=True)

            # Parse and validate schema
            task = progress.add_task("Validating schema...", total=None)
            parser = SchemaParser(settings)
            try:
                parsed_schema = parser.parse(schema)
                progress.update(task, completed=True)
            except SchemaValidationError as e:
                console.print(f"[bold red]Schema validation failed:[/bold red] {e}")
                sys.exit(1)

            # Apply feature flags
            if features:
                parsed_schema['features'].update({f: True for f in features})

            # Apply exclusions
            if exclude:
                parsed_schema['exclude'] = list(exclude)

        # Show generation plan
        if verbose or dry_run:
            _show_generation_plan(console, parsed_schema)

        if dry_run:
            console.print("\n[yellow]Dry run mode - no files will be created[/yellow]")
            return

        # Confirm generation
        if not force and Path(output_dir).exists() and any(Path(output_dir).iterdir()):
            if not click.confirm(f"Output directory '{output_dir}' is not empty. Continue?"):
                console.print("[red]Generation cancelled[/red]")
                return

        # Generate code
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:
            task = progress.add_task("Generating code...", total=100)

            # Initialize generator registry
            registry = GeneratorRegistry()
            registry.discover_generators()

            # Get generator chain
            generators = registry.get_generator_chain(parsed_schema)

            # File system manager
            fs_manager = FileSystemManager(output_dir, force=force)

            # Execute generators
            total_files = 0
            for i, generator in enumerate(generators):
                progress.update(task, description=f"Running {generator.name}...")

                # Generate files
                generated_files = generator.generate(parsed_schema, settings)

                # Write files
                for file_info in generated_files:
                    fs_manager.write_file(file_info['path'], file_info['content'])
                    total_files += 1

                progress.update(task, advance=(100 / len(generators)))

            progress.update(task, completed=100)

        # Show summary
        console.print(Panel(
            f"[bold green]✓ Success![/bold green]\n\n"
            f"Generated {total_files} files in '{output_dir}'\n\n"
            f"Next steps:\n"
            f"1. cd {output_dir}\n"
            f"2. pip install -r requirements/base.txt\n"
            f"3. docker-compose up -d\n"
            f"4. python manage.py migrate\n"
            f"5. python manage.py runserver",
            title="Generation Complete",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)

@cli.command()
@click.argument('project_path', type=click.Path(exists=True), default='.')
@click.option('--output', '-o', type=click.Choice(['json', 'yaml', 'table']), default='table', help='Output format')
@click.option('--analyze-performance', '-p', is_flag=True, help='Include performance analysis')
@click.option('--analyze-security', '-s', is_flag=True, help='Include security analysis')
@click.option('--suggest-improvements', '-i', is_flag=True, help='Suggest improvements')
@click.pass_context
def analyze(ctx, project_path, output, analyze_performance, analyze_security, suggest_improvements):
    """Analyze existing Django project and suggest improvements."""
    console = ctx.obj['console']

    console.print(Panel.fit(
        "[bold blue]Project Analysis[/bold blue]\n"
        f"Analyzing: {project_path}",
        border_style="blue"
    ))

    try:
        analyzer = ProjectAnalyzer()

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:
            task = progress.add_task("Analyzing project...", total=None)

            results = analyzer.analyze(
                project_path,
                include_performance=analyze_performance,
                include_security=analyze_security,
                include_suggestions=suggest_improvements
            )

            progress.update(task, completed=True)

        # Display results
        if output == 'table':
            _display_analysis_table(console, results)
        elif output == 'json':
            console.print_json(json.dumps(results, indent=2))
        else:  # yaml
            console.print(yaml.dump(results, default_flow_style=False))

    except Exception as e:
        console.print(f"[bold red]Analysis failed:[/bold red] {e}")
        sys.exit(1)

@cli.command()
@click.argument('schema_file', type=click.Path(exists=True))
@click.option('--strict', is_flag=True, help='Enable strict validation mode')
@click.option('--show-warnings', '-w', is_flag=True, help='Show validation warnings')
@click.pass_context
def validate(ctx, schema_file, strict, show_warnings):
    """Validate schema file for errors and warnings."""
    console = ctx.obj['console']
    settings = ctx.obj['settings']

    try:
        schema = _load_schema_file(schema_file)
        parser = SchemaParser(settings, strict_mode=strict)

        with console.status("Validating schema..."):
            validation_result = parser.validate(schema, return_warnings=True)

        if validation_result['valid']:
            console.print("[bold green]✓ Schema is valid![/bold green]")

            if show_warnings and validation_result.get('warnings'):
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in validation_result['warnings']:
                    console.print(f"  • {warning}")
        else:
            console.print("[bold red]✗ Schema validation failed![/bold red]")
            console.print("\n[red]Errors:[/red]")
            for error in validation_result['errors']:
                console.print(f"  • {error}")
            sys.exit(1)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

@cli.command()
@click.option('--format', '-f', type=click.Choice(['yaml', 'json']), default='yaml', help='Output format')
@click.option('--type', '-t', type=click.Choice(['minimal', 'standard', 'full']), default='standard', help='Example type')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
@click.pass_context
def example(ctx, format, type, output):
    """Generate example schema files."""
    console = ctx.obj['console']

    examples = {
        'minimal': _get_minimal_example(),
        'standard': _get_standard_example(),
        'full': _get_full_example()
    }

    example_data = examples[type]

    if format == 'json':
        content = json.dumps(example_data, indent=2)
    else:
        content = yaml.dump(example_data, default_flow_style=False, sort_keys=False)

    if output:
        Path(output).write_text(content)
        console.print(f"[green]Example schema written to: {output}[/green]")
    else:
        console.print(Panel(
            content,
            title=f"{type.title()} Example Schema",
            border_style="blue"
        ))

@cli.command()
@click.pass_context
def list_features(ctx):
    """List all available features and generators."""
    console = ctx.obj['console']

    # Create features table
    table = Table(title="Available Features", show_header=True, header_style="bold blue")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Feature", style="green")
    table.add_column("Description", style="white")

    features = {
        "Authentication": [
            ("jwt", "JWT token authentication"),
            ("oauth2", "OAuth2 social authentication"),
            ("two_factor", "Two-factor authentication"),
            ("api_keys", "API key management"),
        ],
        "API": [
            ("rest", "Django REST Framework"),
            ("graphql", "GraphQL with Graphene"),
            ("websockets", "WebSocket support with Channels"),
            ("grpc", "gRPC services"),
        ],
        "Database": [
            ("multidb", "Multiple database support"),
            ("read_replica", "Read replica configuration"),
            ("migrations", "Advanced migration strategies"),
            ("partitioning", "Table partitioning"),
        ],
        "Performance": [
            ("caching", "Redis/Memcached caching"),
            ("celery", "Async task processing"),
            ("elasticsearch", "Full-text search"),
            ("cdn", "CDN integration"),
        ],
        "Deployment": [
            ("docker", "Docker containerization"),
            ("kubernetes", "Kubernetes manifests"),
            ("ci_cd", "CI/CD pipelines"),
            ("monitoring", "Monitoring and alerts"),
        ],
        "Enterprise": [
            ("multitenancy", "Multi-tenant architecture"),
            ("audit", "Audit logging"),
            ("compliance", "GDPR/HIPAA compliance"),
            ("backup", "Automated backups"),
        ],
    }

    for category, items in features.items():
        for feature, description in items:
            table.add_row(category, feature, description)

    console.print(table)

# Helper functions

def _load_schema_file(path: str) -> dict:
    """Load schema from YAML or JSON file."""
    path = Path(path)
    content = path.read_text()

    if path.suffix in ['.yaml', '.yml']:
        return yaml.safe_load(content)
    elif path.suffix == '.json':
        return json.loads(content)
    else:
        # Try to parse as YAML first, then JSON
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return json.loads(content)

def _load_config_file(path: str) -> dict:
    """Load configuration from file."""
    return _load_schema_file(path)

def _show_generation_plan(console: Console, schema: dict) -> None:
    """Display what will be generated."""
    table = Table(title="Generation Plan", show_header=True, header_style="bold blue")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Details", style="white")

    # Project info
    table.add_row("Project", schema['project']['name'])
    table.add_row("Python Version", schema['project'].get('python_version', '3.11'))
    table.add_row("Django Version", schema['project'].get('django_version', '4.2'))

    # Apps
    apps = schema.get('apps', [])
    table.add_row("Apps", f"{len(apps)} apps: {', '.join(app['name'] for app in apps)}")

    # Models count
    total_models = sum(len(app.get('models', [])) for app in apps)
    table.add_row("Models", f"{total_models} models")

    # Features
    features = schema.get('features', {})
    enabled_features = [k for k, v in features.items() if v]
    table.add_row("Features", ', '.join(enabled_features))

    console.print(table)

def _display_analysis_table(console: Console, results: dict) -> None:
    """Display analysis results in table format."""
    # Overview table
    overview = Table(title="Project Overview", show_header=True, header_style="bold blue")
    overview.add_column("Metric", style="cyan")
    overview.add_column("Value", style="white")

    overview.add_row("Apps", str(results['metrics']['total_apps']))
    overview.add_row("Models", str(results['metrics']['total_models']))
    overview.add_row("Views", str(results['metrics']['total_views']))
    overview.add_row("URLs", str(results['metrics']['total_urls']))
    overview.add_row("Tests", str(results['metrics']['total_tests']))
    overview.add_row("Test Coverage", f"{results['metrics'].get('test_coverage', 0)}%")

    console.print(overview)

    # Issues table
    if results.get('issues'):
        issues = Table(title="Issues Found", show_header=True, header_style="bold red")
        issues.add_column("Severity", style="red")
        issues.add_column("Type", style="yellow")
        issues.add_column("Description", style="white")

        for issue in results['issues']:
            issues.add_row(issue['severity'], issue['type'], issue['description'])

        console.print(issues)

    # Suggestions table
    if results.get('suggestions'):
        suggestions = Table(title="Improvement Suggestions", show_header=True, header_style="bold green")
        suggestions.add_column("Area", style="cyan")
        suggestions.add_column("Suggestion", style="white")

        for suggestion in results['suggestions']:
            suggestions.add_row(suggestion['area'], suggestion['description'])

        console.print(suggestions)

def _get_minimal_example() -> dict:
    """Get minimal example schema."""
    return {
        'project': {
            'name': 'myproject',
            'description': 'A minimal Django project'
        },
        'apps': [
            {
                'name': 'blog',
                'models': [
                    {
                        'name': 'Post',
                        'fields': [
                            {'name': 'title', 'type': 'CharField', 'max_length': 200},
                            {'name': 'content', 'type': 'TextField'},
                            {'name': 'published', 'type': 'BooleanField', 'default': False}
                        ]
                    }
                ]
            }
        ]
    }

def _get_standard_example() -> dict:
    """Get standard example schema."""
    return {
        'project': {
            'name': 'myapp',
            'description': 'A standard Django application',
            'python_version': '3.11',
            'django_version': '4.2'
        },
        'features': {
            'api': {
                'rest_framework': True,
                'authentication': 'jwt'
            },
            'database': {
                'engine': 'postgresql'
            },
            'deployment': {
                'docker': True
            }
        },
        'apps': [
            {
                'name': 'accounts',
                'models': [
                    {
                        'name': 'Profile',
                        'fields': [
                            {'name': 'user', 'type': 'OneToOneField', 'to': 'auth.User'},
                            {'name': 'bio', 'type': 'TextField', 'blank': True},
                            {'name': 'avatar', 'type': 'ImageField', 'upload_to': 'avatars/', 'blank': True}
                        ]
                    }
                ]
            },
            {
                'name': 'products',
                'models': [
                    {
                        'name': 'Category',
                        'fields': [
                            {'name': 'name', 'type': 'CharField', 'max_length': 100, 'unique': True},
                            {'name': 'slug', 'type': 'SlugField', 'unique': True}
                        ]
                    },
                    {
                        'name': 'Product',
                        'fields': [
                            {'name': 'name', 'type': 'CharField', 'max_length': 200},
                            {'name': 'slug', 'type': 'SlugField', 'unique': True},
                            {'name': 'description', 'type': 'TextField'},
                            {'name': 'price', 'type': 'DecimalField', 'max_digits': 10, 'decimal_places': 2},
                            {'name': 'category', 'type': 'ForeignKey', 'to': 'Category'},
                            {'name': 'created_at', 'type': 'DateTimeField', 'auto_now_add': True}
                        ],
                        'meta': {
                            'ordering': ['-created_at']
                        }
                    }
                ]
            }
        ]
    }

def _get_full_example() -> dict:
    """Get full example schema with all features."""
    # This would be a comprehensive example
    return {
        'project': {
            'name': 'enterprise_app',
            'description': 'A full-featured enterprise Django application',
            'python_version': '3.11',
            'django_version': '4.2'
        },
        'features': {
            'authentication': {
                'jwt': True,
                'oauth2': {
                    'providers': ['google', 'github']
                },
                'two_factor': True
            },
            'api': {
                'rest_framework': True,
                'graphql': True,
                'websockets': True,
                'versioning': 'header'
            },
            'database': {
                'engine': 'postgresql',
                'read_replica': True
            },
            'performance': {
                'caching': {
                    'backend': 'redis',
                    'strategies': ['page', 'api', 'database']
                },
                'celery': True,
                'elasticsearch': True
            },
            'deployment': {
                'docker': True,
                'kubernetes': True,
                'ci_cd': 'github_actions'
            },
            'enterprise': {
                'multitenancy': True,
                'audit': True,
                'compliance': ['gdpr', 'hipaa']
            }
        },
        'apps': [
            {
                'name': 'core',
                'models': [
                    {
                        'name': 'Organization',
                        'fields': [
                            {'name': 'name', 'type': 'CharField', 'max_length': 200},
                            {'name': 'slug', 'type': 'SlugField', 'unique': True},
                            {'name': 'domain', 'type': 'CharField', 'max_length': 100, 'unique': True}
                        ],
                        'features': {
                            'multitenancy': True,
                            'audit': True
                        }
                    }
                ]
            }
        ]
    }

if __name__ == '__main__':
    cli()