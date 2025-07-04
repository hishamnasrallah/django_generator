"""
Enhanced Project Structure Generator
Creates comprehensive Django project structure with all modern components
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import secrets
import os

from .base_generator import BaseGenerator, GeneratedFile


class EnhancedProjectGenerator(BaseGenerator):
    """
    Enhanced project structure generator that creates a complete
    production-ready Django project with all modern components.
    
    Features:
    - Multi-environment settings
    - Docker configuration
    - CI/CD pipelines
    - Monitoring setup
    - Security configurations
    - Performance optimizations
    """
    
    name = "EnhancedProjectGenerator"
    description = "Creates comprehensive Django project structure"
    version = "1.0.0"
    order = 5
    
    def can_generate(self, schema: Dict[str, Any]) -> bool:
        """Always generate project structure."""
        return 'project' in schema
    
    def generate(self, schema: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[GeneratedFile]:
        """Generate enhanced project structure."""
        self.generated_files = []
        
        project = schema['project']
        features = schema.get('features', {})
        
        # Build comprehensive context
        ctx = {
            'project': project,
            'project_name': project['name'],
            'project_title': self.naming.to_title_case(project['name']),
            'features': features,
            'apps': schema.get('apps', []),
            'python_version': project.get('python_version', '3.11'),
            'django_version': project.get('django_version', '4.2'),
            'secret_key': self._generate_secret_key(),
            'database_url': self._generate_database_url(features.get('database', {})),
            'redis_url': self._generate_redis_url(features.get('performance', {})),
        }
        
        # Generate all project components
        self._generate_root_structure(ctx)
        self._generate_settings_structure(ctx)
        self._generate_requirements_structure(ctx)
        self._generate_docker_structure(ctx)
        self._generate_scripts_structure(ctx)
        self._generate_docs_structure(ctx)
        
        # Optional components based on features
        if features.get('deployment', {}).get('ci_cd'):
            self._generate_ci_cd_structure(ctx)
        
        if features.get('deployment', {}).get('kubernetes'):
            self._generate_kubernetes_structure(ctx)
        
        if features.get('performance', {}).get('monitoring'):
            self._generate_monitoring_structure(ctx)
        
        return self.generated_files
    
    def _generate_root_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate root project files."""
        # README.md
        self.create_file_from_template(
            'project/root/README.md.j2',
            'README.md',
            ctx
        )
        
        # .gitignore
        self.create_file_from_template(
            'project/root/gitignore.j2',
            '.gitignore',
            ctx
        )
        
        # .env.example
        self.create_file_from_template(
            'project/root/env.example.j2',
            '.env.example',
            ctx
        )
        
        # manage.py
        self.create_file_from_template(
            'project/root/manage.py.j2',
            'manage.py',
            ctx,
            executable=True
        )
        
        # Makefile
        self.create_file_from_template(
            'project/root/Makefile.j2',
            'Makefile',
            ctx
        )
        
        # pyproject.toml
        self.create_file_from_template(
            'project/root/pyproject.toml.j2',
            'pyproject.toml',
            ctx
        )
        
        # setup.cfg
        self.create_file_from_template(
            'project/root/setup.cfg.j2',
            'setup.cfg',
            ctx
        )
        
        # .pre-commit-config.yaml
        self.create_file_from_template(
            'project/root/pre-commit-config.yaml.j2',
            '.pre-commit-config.yaml',
            ctx
        )
    
    def _generate_settings_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate Django settings structure."""
        project_name = ctx['project_name']
        
        # Create project directory
        self.create_file(f'{project_name}/__init__.py', '')
        
        # Main URLs
        self.create_file_from_template(
            'project/django/urls.py.j2',
            f'{project_name}/urls.py',
            ctx
        )
        
        # WSGI
        self.create_file_from_template(
            'project/django/wsgi.py.j2',
            f'{project_name}/wsgi.py',
            ctx
        )
        
        # ASGI (if WebSockets enabled)
        if ctx['features'].get('api', {}).get('websockets'):
            self.create_file_from_template(
                'project/django/asgi.py.j2',
                f'{project_name}/asgi.py',
                ctx
            )
        
        # Celery (if enabled)
        if ctx['features'].get('performance', {}).get('celery'):
            self.create_file_from_template(
                'project/django/celery.py.j2',
                f'{project_name}/celery.py',
                ctx
            )
        
        # Settings package
        settings_dir = f'{project_name}/settings'
        
        self.create_file_from_template(
            'project/settings/__init__.py.j2',
            f'{settings_dir}/__init__.py',
            ctx
        )
        
        self.create_file_from_template(
            'project/settings/base.py.j2',
            f'{settings_dir}/base.py',
            ctx
        )
        
        self.create_file_from_template(
            'project/settings/development.py.j2',
            f'{settings_dir}/development.py',
            ctx
        )
        
        self.create_file_from_template(
            'project/settings/staging.py.j2',
            f'{settings_dir}/staging.py',
            ctx
        )
        
        self.create_file_from_template(
            'project/settings/production.py.j2',
            f'{settings_dir}/production.py',
            ctx
        )
        
        self.create_file_from_template(
            'project/settings/testing.py.j2',
            f'{settings_dir}/testing.py',
            ctx
        )
        
        self.create_file_from_template(
            'project/settings/logging.py.j2',
            f'{settings_dir}/logging.py',
            ctx
        )
    
    def _generate_requirements_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate requirements files."""
        requirements_files = [
            ('base.txt', 'project/requirements/base.txt.j2'),
            ('development.txt', 'project/requirements/development.txt.j2'),
            ('production.txt', 'project/requirements/production.txt.j2'),
            ('testing.txt', 'project/requirements/testing.txt.j2'),
        ]
        
        for filename, template in requirements_files:
            self.create_file_from_template(
                template,
                f'requirements/{filename}',
                ctx
            )
    
    def _generate_docker_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate Docker configuration."""
        if not ctx['features'].get('deployment', {}).get('docker'):
            return
        
        # Dockerfile
        self.create_file_from_template(
            'project/docker/Dockerfile.j2',
            'Dockerfile',
            ctx
        )
        
        # docker-compose.yml
        self.create_file_from_template(
            'project/docker/docker-compose.yml.j2',
            'docker-compose.yml',
            ctx
        )
        
        # docker-compose.prod.yml
        self.create_file_from_template(
            'project/docker/docker-compose.prod.yml.j2',
            'docker-compose.prod.yml',
            ctx
        )
        
        # .dockerignore
        self.create_file_from_template(
            'project/docker/.dockerignore.j2',
            '.dockerignore',
            ctx
        )
        
        # Docker scripts
        docker_scripts = [
            ('docker/scripts/entrypoint.sh', 'project/docker/scripts/entrypoint.sh.j2'),
            ('docker/scripts/wait-for-it.sh', 'project/docker/scripts/wait-for-it.sh.j2'),
            ('docker/scripts/health-check.sh', 'project/docker/scripts/health-check.sh.j2'),
        ]
        
        for output_path, template_path in docker_scripts:
            self.create_file_from_template(
                template_path,
                output_path,
                ctx,
                executable=True
            )
    
    def _generate_scripts_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate utility scripts."""
        scripts = [
            ('scripts/setup_dev.sh', 'project/scripts/setup_dev.sh.j2'),
            ('scripts/run_tests.sh', 'project/scripts/run_tests.sh.j2'),
            ('scripts/deploy.sh', 'project/scripts/deploy.sh.j2'),
            ('scripts/backup_db.sh', 'project/scripts/backup_db.sh.j2'),
            ('scripts/restore_db.sh', 'project/scripts/restore_db.sh.j2'),
        ]
        
        for output_path, template_path in scripts:
            self.create_file_from_template(
                template_path,
                output_path,
                ctx,
                executable=True
            )
    
    def _generate_docs_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate documentation structure."""
        docs_files = [
            ('docs/README.md', 'project/docs/README.md.j2'),
            ('docs/ARCHITECTURE.md', 'project/docs/ARCHITECTURE.md.j2'),
            ('docs/API.md', 'project/docs/API.md.j2'),
            ('docs/DEPLOYMENT.md', 'project/docs/DEPLOYMENT.md.j2'),
            ('docs/CONTRIBUTING.md', 'project/docs/CONTRIBUTING.md.j2'),
            ('docs/SECURITY.md', 'project/docs/SECURITY.md.j2'),
            ('docs/CHANGELOG.md', 'project/docs/CHANGELOG.md.j2'),
        ]
        
        for output_path, template_path in docs_files:
            self.create_file_from_template(
                template_path,
                output_path,
                ctx
            )
        
        # API documentation
        if ctx['features'].get('api', {}).get('rest_framework'):
            self.create_file_from_template(
                'project/docs/api/swagger.yml.j2',
                'docs/api/swagger.yml',
                ctx
            )
    
    def _generate_ci_cd_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate CI/CD configuration."""
        ci_cd_type = ctx['features'].get('deployment', {}).get('ci_cd', 'github_actions')
        
        if ci_cd_type == 'github_actions':
            workflows = [
                ('ci.yml', 'project/ci_cd/github/ci.yml.j2'),
                ('deploy.yml', 'project/ci_cd/github/deploy.yml.j2'),
                ('security.yml', 'project/ci_cd/github/security.yml.j2'),
                ('performance.yml', 'project/ci_cd/github/performance.yml.j2'),
            ]
            
            for filename, template_path in workflows:
                self.create_file_from_template(
                    template_path,
                    f'.github/workflows/{filename}',
                    ctx
                )
            
            # Dependabot
            self.create_file_from_template(
                'project/ci_cd/github/dependabot.yml.j2',
                '.github/dependabot.yml',
                ctx
            )
            
            # Issue templates
            self.create_file_from_template(
                'project/ci_cd/github/bug_report.md.j2',
                '.github/ISSUE_TEMPLATE/bug_report.md',
                ctx
            )
            
            self.create_file_from_template(
                'project/ci_cd/github/feature_request.md.j2',
                '.github/ISSUE_TEMPLATE/feature_request.md',
                ctx
            )
        
        elif ci_cd_type == 'gitlab':
            self.create_file_from_template(
                'project/ci_cd/gitlab-ci.yml.j2',
                '.gitlab-ci.yml',
                ctx
            )
        
        elif ci_cd_type == 'jenkins':
            self.create_file_from_template(
                'project/ci_cd/Jenkinsfile.j2',
                'Jenkinsfile',
                ctx
            )
    
    def _generate_kubernetes_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate Kubernetes manifests."""
        k8s_files = [
            ('k8s/namespace.yaml', 'project/kubernetes/namespace.yaml.j2'),
            ('k8s/configmap.yaml', 'project/kubernetes/configmap.yaml.j2'),
            ('k8s/secrets.yaml', 'project/kubernetes/secrets.yaml.j2'),
            ('k8s/deployment.yaml', 'project/kubernetes/deployment.yaml.j2'),
            ('k8s/service.yaml', 'project/kubernetes/service.yaml.j2'),
            ('k8s/ingress.yaml', 'project/kubernetes/ingress.yaml.j2'),
            ('k8s/hpa.yaml', 'project/kubernetes/hpa.yaml.j2'),
            ('k8s/pdb.yaml', 'project/kubernetes/pdb.yaml.j2'),
        ]
        
        for output_path, template_path in k8s_files:
            self.create_file_from_template(
                template_path,
                output_path,
                ctx
            )
        
        # Database manifests if using PostgreSQL
        if ctx['features'].get('database', {}).get('engine') == 'postgresql':
            db_files = [
                ('k8s/postgres-deployment.yaml', 'project/kubernetes/postgres-deployment.yaml.j2'),
                ('k8s/postgres-service.yaml', 'project/kubernetes/postgres-service.yaml.j2'),
                ('k8s/postgres-pvc.yaml', 'project/kubernetes/postgres-pvc.yaml.j2'),
            ]
            
            for output_path, template_path in db_files:
                self.create_file_from_template(
                    template_path,
                    output_path,
                    ctx
                )
        
        # Redis manifests if caching enabled
        if ctx['features'].get('performance', {}).get('caching'):
            redis_files = [
                ('k8s/redis-deployment.yaml', 'project/kubernetes/redis-deployment.yaml.j2'),
                ('k8s/redis-service.yaml', 'project/kubernetes/redis-service.yaml.j2'),
            ]
            
            for output_path, template_path in redis_files:
                self.create_file_from_template(
                    template_path,
                    output_path,
                    ctx
                )
    
    def _generate_monitoring_structure(self, ctx: Dict[str, Any]) -> None:
        """Generate monitoring configuration."""
        monitoring_files = [
            ('monitoring/prometheus.yml', 'project/monitoring/prometheus.yml.j2'),
            ('monitoring/grafana-dashboard.json', 'project/monitoring/grafana-dashboard.json.j2'),
            ('monitoring/alerts.yml', 'project/monitoring/alerts.yml.j2'),
        ]
        
        for output_path, template_path in monitoring_files:
            self.create_file_from_template(
                template_path,
                output_path,
                ctx
            )
    
    def _generate_secret_key(self) -> str:
        """Generate a secure Django secret key."""
        return secrets.token_urlsafe(50)
    
    def _generate_database_url(self, database_config: Dict[str, Any]) -> str:
        """Generate database URL based on configuration."""
        engine = database_config.get('engine', 'postgresql')
        
        if engine == 'postgresql':
            return 'postgresql://user:password@localhost:5432/dbname'
        elif engine == 'mysql':
            return 'mysql://user:password@localhost:3306/dbname'
        else:
            return 'sqlite:///db.sqlite3'
    
    def _generate_redis_url(self, performance_config: Dict[str, Any]) -> str:
        """Generate Redis URL if caching is enabled."""
        if performance_config.get('caching', {}).get('backend') == 'redis':
            return 'redis://localhost:6379/0'
        return ''