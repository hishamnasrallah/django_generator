#!/usr/bin/env python
"""
Enhanced Django Generator CLI
Advanced command-line interface with rich features
"""
import sys
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.tree import Tree
from rich import print as rprint
import tempfile
import subprocess

from .core.generation_engine import get_engine, GenerationEngine
from .core.enhanced_generator_registry import get_registry
from .core.schema_parser import SchemaParser, SchemaValidationError
from .core.plugin_system import get_plugin_manager
from .config.settings import Settings
from .utils.file_system import FileSystemManager

console = Console()


class CLIContext:
    """CLI context object."""
    
    def __init__(self):
        self.settings = Settings()
        self.engine = get_engine(self.settings)
        self.registry = get_registry(self.settings)
        self.plugin_manager = get_plugin_manager(self.settings)
        self.verbose = False
        self.quiet = False


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-essential output')
@click.option('--config', '-c', type=click.Path(), help='Configuration file')
@click.version_option(version='1.0.0', prog_name='Django Enhanced Generator')
@click.pass_context
def cli(ctx, verbose, quiet, config):
    """
    Django Enhanced Generator - Generate production-ready Django applications.
    
    This tool helps you create complete Django applications with modern features,
    best practices, and production-ready configurations.
    """
    ctx.ensure_object(CLIContext)
    ctx.obj.verbose = verbose
    ctx.obj.quiet = quiet
    
    if config:
        # Load custom configuration
        config_path = Path(config)
        if config_path.exists():
            try:
                if config_path.suffix in ['.yml', '.yaml']:
                    with open(config_path) as f:
                        config_data = yaml.safe_load(f)
                else:
                    with open(config_path) as f:
                        config_data = json.load(f)
                
                ctx.obj.settings.update(config_data)
                if not quiet:
                    console.print(f"[green]Loaded configuration from {config}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to load configuration: {e}[/red]")
                sys.exit(1)


@cli.command()
@click.argument('schema_file', type=click.Path(exists=True))
@click.option('--output', '-o', default='.', help='Output directory')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing files')
@click.option('--dry-run', is_flag=True, help='Show what would be generated without creating files')
@click.option('--generators', '-g', multiple=True, help='Specific generators to use')
@click.option('--exclude', '-e', multiple=True, help='Generators to exclude')
@click.option('--parallel/--sequential', default=True, help='Enable/disable parallel execution')
@click.option('--continue-on-error', is_flag=True, help='Continue generation even if some generators fail')
@click.pass_context
def generate(ctx, schema_file, output, force, dry_run, generators, exclude, parallel, continue_on_error):
    """Generate Django project from schema file."""
    if not ctx.obj.quiet:
        console.print(Panel.fit(
            "[bold blue]Django Enhanced Generator[/bold blue]\n"
            "Generating production-ready Django code...",
            border_style="blue"
        ))
    
    try:
        # Load schema
        schema = _load_schema_file(schema_file)
        
        # Validate schema
        if ctx.obj.verbose:
            console.print("[cyan]Validating schema...[/cyan]")
        
        validation_result = ctx.obj.engine.validate_schema(schema)
        if not validation_result['valid']:
            console.print("[red]Schema validation failed:[/red]")
            for error in validation_result['errors']:
                console.print(f"  • {error}")
            sys.exit(1)
        
        # Get generation plan
        selected_generators = list(generators) if generators else None
        if exclude:
            # Remove excluded generators
            all_generators = [g.name for g in ctx.obj.registry.get_generators_for_schema(schema)]
            selected_generators = [g for g in all_generators if g not in exclude]
        
        plan = ctx.obj.engine.get_generation_plan(schema, selected_generators)
        
        if not plan['valid']:
            console.print(f"[red]Generation plan failed: {plan['error']}[/red]")
            sys.exit(1)
        
        # Show generation plan
        if ctx.obj.verbose or dry_run:
            _show_generation_plan(plan)
        
        if dry_run:
            console.print("\n[yellow]Dry run mode - no files will be created[/yellow]")
            return
        
        # Confirm generation if output directory is not empty
        if not force and Path(output).exists() and any(Path(output).iterdir()):
            if not Confirm.ask(f"Output directory '{output}' is not empty. Continue?"):
                console.print("[red]Generation cancelled[/red]")
                return
        
        # Configure engine
        ctx.obj.engine.parallel_execution = parallel
        ctx.obj.engine.continue_on_error = continue_on_error
        
        # Add progress callback
        if not ctx.obj.quiet:
            progress_bar = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console
            )
            
            def progress_callback(data):
                if hasattr(progress_callback, 'task_id'):
                    progress_bar.update(
                        progress_callback.task_id,
                        description=data['message'],
                        completed=data['current'],
                        total=data['total']
                    )
            
            ctx.obj.engine.add_progress_callback(progress_callback)
        
        # Generate code
        with progress_bar if not ctx.obj.quiet else console.status("Generating..."):
            if not ctx.obj.quiet:
                progress_callback.task_id = progress_bar.add_task(
                    "Starting generation...", 
                    total=len(plan['generators'])
                )
            
            result = ctx.obj.engine.generate(
                schema=schema,
                output_dir=output,
                force=force,
                dry_run=dry_run,
                selected_generators=selected_generators
            )
        
        # Show results
        _show_generation_results(result, ctx.obj.verbose)
        
        if not result['success']:
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj.verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument('schema_file', type=click.Path(exists=True))
@click.option('--strict', is_flag=True, help='Enable strict validation mode')
@click.option('--show-warnings', '-w', is_flag=True, help='Show validation warnings')
@click.option('--output-format', type=click.Choice(['table', 'json', 'yaml']), default='table')
@click.pass_context
def validate(ctx, schema_file, strict, show_warnings, output_format):
    """Validate schema file for errors and warnings."""
    try:
        schema = _load_schema_file(schema_file)
        
        # Create parser with strict mode
        parser = SchemaParser(ctx.obj.settings, strict_mode=strict)
        
        with console.status("Validating schema..."):
            validation_result = parser.validate(schema, return_warnings=True)
        
        if output_format == 'table':
            _show_validation_results_table(validation_result, show_warnings)
        elif output_format == 'json':
            console.print_json(json.dumps(validation_result, indent=2))
        else:  # yaml
            console.print(yaml.dump(validation_result, default_flow_style=False))
        
        if not validation_result['valid']:
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option('--category', '-c', help='Filter by category')
@click.option('--tag', '-t', help='Filter by tag')
@click.option('--output-format', type=click.Choice(['table', 'json', 'yaml']), default='table')
@click.pass_context
def list_generators(ctx, category, tag, output_format):
    """List available generators."""
    generators = ctx.obj.registry.list_generators(category=category, tag=tag)
    
    if output_format == 'table':
        _show_generators_table(generators)
    elif output_format == 'json':
        console.print_json(json.dumps(generators, indent=2))
    else:  # yaml
        console.print(yaml.dump(generators, default_flow_style=False))


@cli.command()
@click.argument('generator_name')
@click.pass_context
def generator_info(ctx, generator_name):
    """Show detailed information about a generator."""
    info = ctx.obj.registry.get_generator_info(generator_name)
    
    if not info:
        console.print(f"[red]Generator '{generator_name}' not found[/red]")
        sys.exit(1)
    
    _show_generator_info(info)


@cli.command()
@click.option('--output-format', type=click.Choice(['table', 'json', 'yaml']), default='table')
@click.pass_context
def list_plugins(ctx, output_format):
    """List available plugins."""
    plugins = ctx.obj.plugin_manager.list_plugins()
    
    if output_format == 'table':
        _show_plugins_table(plugins)
    elif output_format == 'json':
        console.print_json(json.dumps(plugins, indent=2))
    else:  # yaml
        console.print(yaml.dump(plugins, default_flow_style=False))


@cli.command()
@click.argument('plugin_name')
@click.option('--config', type=click.Path(), help='Plugin configuration file')
@click.pass_context
def load_plugin(ctx, plugin_name, config):
    """Load a plugin."""
    plugin_config = None
    if config:
        try:
            with open(config) as f:
                if config.endswith('.json'):
                    plugin_config = json.load(f)
                else:
                    plugin_config = yaml.safe_load(f)
        except Exception as e:
            console.print(f"[red]Failed to load plugin config: {e}[/red]")
            sys.exit(1)
    
    if ctx.obj.plugin_manager.load_plugin(plugin_name, plugin_config):
        console.print(f"[green]Plugin '{plugin_name}' loaded successfully[/green]")
    else:
        console.print(f"[red]Failed to load plugin '{plugin_name}'[/red]")
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['yaml', 'json']), default='yaml')
@click.option('--type', '-t', type=click.Choice(['minimal', 'standard', 'full']), default='standard')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.pass_context
def create_example(ctx, format, type, output):
    """Create example schema files."""
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
            Syntax(content, format, theme="monokai", line_numbers=True),
            title=f"{type.title()} Example Schema",
            border_style="blue"
        ))


@cli.command()
@click.argument('project_path', type=click.Path(exists=True), default='.')
@click.option('--output-format', type=click.Choice(['table', 'json', 'yaml']), default='table')
@click.option('--include-performance', '-p', is_flag=True, help='Include performance analysis')
@click.option('--include-security', '-s', is_flag=True, help='Include security analysis')
@click.option('--suggest-improvements', '-i', is_flag=True, help='Suggest improvements')
@click.pass_context
def analyze(ctx, project_path, output_format, include_performance, include_security, suggest_improvements):
    """Analyze existing Django project."""
    console.print(Panel.fit(
        "[bold blue]Project Analysis[/bold blue]\n"
        f"Analyzing: {project_path}",
        border_style="blue"
    ))
    
    # This would integrate with a project analyzer
    console.print("[yellow]Project analysis feature coming soon![/yellow]")


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive mode for schema creation."""
    console.print(Panel.fit(
        "[bold blue]Interactive Schema Builder[/bold blue]\n"
        "Let's build your Django project schema step by step.",
        border_style="blue"
    ))
    
    schema = _interactive_schema_builder()
    
    # Ask if user wants to save the schema
    if Confirm.ask("Save schema to file?"):
        filename = Prompt.ask("Enter filename", default="schema.yml")
        
        content = yaml.dump(schema, default_flow_style=False, sort_keys=False)
        Path(filename).write_text(content)
        
        console.print(f"[green]Schema saved to {filename}[/green]")
        
        # Ask if user wants to generate immediately
        if Confirm.ask("Generate project now?"):
            output_dir = Prompt.ask("Output directory", default=".")
            
            result = ctx.obj.engine.generate(
                schema=schema,
                output_dir=output_dir,
                force=False,
                dry_run=False
            )
            
            _show_generation_results(result, ctx.obj.verbose)


@cli.command()
@click.pass_context
def doctor(ctx):
    """Check system health and configuration."""
    console.print(Panel.fit(
        "[bold blue]System Health Check[/bold blue]\n"
        "Checking Django Enhanced Generator installation...",
        border_style="blue"
    ))
    
    checks = [
        ("Python Version", _check_python_version),
        ("Dependencies", _check_dependencies),
        ("Template Files", _check_templates),
        ("Plugin System", _check_plugins),
        ("Configuration", _check_configuration),
    ]
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running health checks...", total=len(checks))
        
        for check_name, check_func in checks:
            progress.update(task, description=f"Checking {check_name}...")
            result = check_func(ctx)
            results.append((check_name, result))
            progress.advance(task)
    
    _show_health_check_results(results)


# Helper functions

def _load_schema_file(path: str) -> dict:
    """Load schema from YAML or JSON file."""
    path_obj = Path(path)
    content = path_obj.read_text()
    
    if path_obj.suffix in ['.yaml', '.yml']:
        return yaml.safe_load(content)
    elif path_obj.suffix == '.json':
        return json.loads(content)
    else:
        # Try to parse as YAML first, then JSON
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return json.loads(content)


def _show_generation_plan(plan: Dict[str, Any]) -> None:
    """Display generation plan."""
    table = Table(title="Generation Plan", show_header=True, header_style="bold blue")
    table.add_column("Order", style="cyan", width=6)
    table.add_column("Generator", style="green")
    table.add_column("Description", style="white")
    table.add_column("Dependencies", style="yellow")
    
    for i, generator in enumerate(plan['generators'], 1):
        deps = ', '.join(generator['requires']) if generator['requires'] else 'None'
        table.add_row(
            str(i),
            generator['name'],
            generator['description'][:50] + '...' if len(generator['description']) > 50 else generator['description'],
            deps
        )
    
    console.print(table)
    console.print(f"\n[cyan]Estimated files to generate: {plan['estimated_files']}[/cyan]")


def _show_generation_results(result: Dict[str, Any], verbose: bool) -> None:
    """Display generation results."""
    if result['success']:
        console.print(Panel(
            f"[bold green]✓ Generation completed successfully![/bold green]\n\n"
            f"Files generated: {result['stats']['files_generated']}\n"
            f"Generators executed: {result['stats']['generators_executed']}\n"
            f"Execution time: {result['execution_time']:.2f}s",
            title="Success",
            border_style="green"
        ))
        
        if verbose and result['generated_files']:
            console.print("\n[cyan]Generated files:[/cyan]")
            for file_path in result['generated_files'][:20]:  # Show first 20
                console.print(f"  • {file_path}")
            
            if len(result['generated_files']) > 20:
                console.print(f"  ... and {len(result['generated_files']) - 20} more files")
    
    else:
        console.print(Panel(
            f"[bold red]✗ Generation failed![/bold red]\n\n"
            f"Execution time: {result['execution_time']:.2f}s",
            title="Failed",
            border_style="red"
        ))
    
    # Show warnings
    if result.get('warnings'):
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result['warnings']:
            console.print(f"  • {warning}")
    
    # Show errors
    if result.get('errors'):
        console.print("\n[red]Errors:[/red]")
        for error in result['errors']:
            console.print(f"  • {error}")


def _show_validation_results_table(result: Dict[str, Any], show_warnings: bool) -> None:
    """Show validation results in table format."""
    if result['valid']:
        console.print("[bold green]✓ Schema is valid![/bold green]")
    else:
        console.print("[bold red]✗ Schema validation failed![/bold red]")
    
    if result.get('errors'):
        console.print("\n[red]Errors:[/red]")
        for error in result['errors']:
            console.print(f"  • {error}")
    
    if show_warnings and result.get('warnings'):
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result['warnings']:
            console.print(f"  • {warning}")


def _show_generators_table(generators: List[Dict[str, Any]]) -> None:
    """Show generators in table format."""
    table = Table(title="Available Generators", show_header=True, header_style="bold blue")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Category", style="green")
    table.add_column("Description", style="white")
    table.add_column("Order", style="yellow", width=6)
    table.add_column("Status", style="magenta")
    
    for generator in generators:
        status = "✓ Loaded" if generator['loaded'] else "○ Available"
        table.add_row(
            generator['name'],
            generator['category'],
            generator['description'][:40] + '...' if len(generator['description']) > 40 else generator['description'],
            str(generator['order']),
            status
        )
    
    console.print(table)


def _show_generator_info(info: Dict[str, Any]) -> None:
    """Show detailed generator information."""
    console.print(Panel(
        f"[bold]{info['name']}[/bold] v{info['version']}\n\n"
        f"{info['description']}\n\n"
        f"[cyan]Category:[/cyan] {info['category']}\n"
        f"[cyan]Order:[/cyan] {info['order']}\n"
        f"[cyan]Module:[/cyan] {info['module']}\n"
        f"[cyan]Status:[/cyan] {'Loaded' if info['loaded'] else 'Available'}\n\n"
        f"[cyan]Requires:[/cyan] {', '.join(info['requires']) if info['requires'] else 'None'}\n"
        f"[cyan]Provides:[/cyan] {', '.join(info['provides']) if info['provides'] else 'None'}\n"
        f"[cyan]Tags:[/cyan] {', '.join(info['tags']) if info['tags'] else 'None'}",
        title="Generator Information",
        border_style="blue"
    ))
    
    if info['dependencies']:
        console.print("\n[cyan]Dependencies:[/cyan]")
        for dep in info['dependencies']:
            console.print(f"  • {dep}")
    
    if info['dependents']:
        console.print("\n[cyan]Dependents:[/cyan]")
        for dep in info['dependents']:
            console.print(f"  • {dep}")


def _show_plugins_table(plugins: List[Dict[str, Any]]) -> None:
    """Show plugins in table format."""
    table = Table(title="Available Plugins", show_header=True, header_style="bold blue")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="green")
    table.add_column("Description", style="white")
    table.add_column("Author", style="yellow")
    table.add_column("Status", style="magenta")
    
    for plugin in plugins:
        status = "✓ Loaded" if plugin['loaded'] else "○ Available"
        table.add_row(
            plugin['name'],
            plugin['version'],
            plugin['description'][:40] + '...' if len(plugin['description']) > 40 else plugin['description'],
            plugin['author'],
            status
        )
    
    console.print(table)


def _interactive_schema_builder() -> Dict[str, Any]:
    """Interactive schema builder."""
    schema = {
        'project': {},
        'features': {},
        'apps': []
    }
    
    # Project information
    console.print("\n[bold cyan]Project Information[/bold cyan]")
    schema['project']['name'] = Prompt.ask("Project name")
    schema['project']['description'] = Prompt.ask("Project description", default="")
    schema['project']['python_version'] = Prompt.ask("Python version", default="3.11")
    schema['project']['django_version'] = Prompt.ask("Django version", default="4.2")
    
    # Features
    console.print("\n[bold cyan]Features[/bold cyan]")
    
    # API features
    if Confirm.ask("Enable REST API?"):
        schema['features']['api'] = {'rest_framework': True}
        
        if Confirm.ask("Enable GraphQL?"):
            schema['features']['api']['graphql'] = True
        
        if Confirm.ask("Enable WebSockets?"):
            schema['features']['api']['websockets'] = True
    
    # Database features
    db_engine = Prompt.ask(
        "Database engine",
        choices=['postgresql', 'mysql', 'sqlite'],
        default='postgresql'
    )
    schema['features']['database'] = {'engine': db_engine}
    
    # Performance features
    if Confirm.ask("Enable caching?"):
        cache_backend = Prompt.ask(
            "Cache backend",
            choices=['redis', 'memcached'],
            default='redis'
        )
        schema['features']['performance'] = {'caching': {'backend': cache_backend}}
        
        if Confirm.ask("Enable Celery for async tasks?"):
            schema['features']['performance']['celery'] = True
    
    # Deployment features
    if Confirm.ask("Enable Docker?"):
        schema['features']['deployment'] = {'docker': True}
        
        if Confirm.ask("Enable Kubernetes?"):
            schema['features']['deployment']['kubernetes'] = True
    
    # Apps
    console.print("\n[bold cyan]Applications[/bold cyan]")
    
    while True:
        app_name = Prompt.ask("App name (or 'done' to finish)")
        if app_name.lower() == 'done':
            break
        
        app = {
            'name': app_name,
            'models': []
        }
        
        # Models for this app
        while True:
            model_name = Prompt.ask(f"Model name for {app_name} (or 'done' to finish)")
            if model_name.lower() == 'done':
                break
            
            model = {
                'name': model_name,
                'fields': []
            }
            
            # Basic fields
            model['fields'].extend([
                {'name': 'created_at', 'type': 'DateTimeField', 'auto_now_add': True},
                {'name': 'updated_at', 'type': 'DateTimeField', 'auto_now': True}
            ])
            
            # Custom fields
            while True:
                field_name = Prompt.ask(f"Field name for {model_name} (or 'done' to finish)")
                if field_name.lower() == 'done':
                    break
                
                field_type = Prompt.ask(
                    "Field type",
                    choices=['CharField', 'TextField', 'IntegerField', 'BooleanField', 'DateTimeField', 'ForeignKey'],
                    default='CharField'
                )
                
                field = {'name': field_name, 'type': field_type}
                
                if field_type == 'CharField':
                    field['max_length'] = int(Prompt.ask("Max length", default="200"))
                elif field_type == 'ForeignKey':
                    field['to'] = Prompt.ask("Related model")
                
                model['fields'].append(field)
            
            app['models'].append(model)
        
        schema['apps'].append(app)
    
    return schema


def _check_python_version(ctx) -> Dict[str, Any]:
    """Check Python version."""
    import sys
    version = sys.version_info
    
    if version >= (3, 9):
        return {'status': 'ok', 'message': f'Python {version.major}.{version.minor}.{version.micro}'}
    else:
        return {'status': 'error', 'message': f'Python {version.major}.{version.minor} is too old. Requires 3.9+'}


def _check_dependencies(ctx) -> Dict[str, Any]:
    """Check required dependencies."""
    required_packages = ['django', 'jinja2', 'pyyaml', 'click', 'rich']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        return {'status': 'error', 'message': f'Missing packages: {", ".join(missing)}'}
    else:
        return {'status': 'ok', 'message': 'All dependencies installed'}


def _check_templates(ctx) -> Dict[str, Any]:
    """Check template files."""
    template_dir = Path(__file__).parent / 'templates'
    
    if not template_dir.exists():
        return {'status': 'error', 'message': 'Template directory not found'}
    
    template_count = len(list(template_dir.rglob('*.j2')))
    
    if template_count > 0:
        return {'status': 'ok', 'message': f'{template_count} templates found'}
    else:
        return {'status': 'warning', 'message': 'No templates found'}


def _check_plugins(ctx) -> Dict[str, Any]:
    """Check plugin system."""
    try:
        plugin_count = len(ctx.obj.plugin_manager.get_discovered_plugins())
        return {'status': 'ok', 'message': f'{plugin_count} plugins discovered'}
    except Exception as e:
        return {'status': 'error', 'message': f'Plugin system error: {e}'}


def _check_configuration(ctx) -> Dict[str, Any]:
    """Check configuration."""
    try:
        settings_dict = ctx.obj.settings.to_dict()
        return {'status': 'ok', 'message': f'{len(settings_dict)} settings loaded'}
    except Exception as e:
        return {'status': 'error', 'message': f'Configuration error: {e}'}


def _show_health_check_results(results: List[tuple]) -> None:
    """Show health check results."""
    table = Table(title="Health Check Results", show_header=True, header_style="bold blue")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Message", style="white")
    
    for check_name, result in results:
        status = result['status']
        if status == 'ok':
            status_display = "[green]✓ OK[/green]"
        elif status == 'warning':
            status_display = "[yellow]⚠ Warning[/yellow]"
        else:
            status_display = "[red]✗ Error[/red]"
        
        table.add_row(check_name, status_display, result['message'])
    
    console.print(table)


def _get_minimal_example() -> Dict[str, Any]:
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


def _get_standard_example() -> Dict[str, Any]:
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
            }
        ]
    }


def _get_full_example() -> Dict[str, Any]:
    """Get full example schema."""
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
                    'backend': 'redis'
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
                        ]
                    }
                ]
            }
        ]
    }


if __name__ == '__main__':
    cli()