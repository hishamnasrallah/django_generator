"""
Tests for Template Engine
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import os

from generator.core.template_engine import TemplateEngine
from generator.config.settings import Settings


class TestTemplateEngine:
    """Test cases for TemplateEngine."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def template_engine(self, settings):
        """Create template engine instance."""
        return TemplateEngine(settings)
    
    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir) / 'templates'
            template_dir.mkdir()
            
            # Create test template
            test_template = template_dir / 'test.j2'
            test_template.write_text('Hello {{ name }}!')
            
            yield str(template_dir)
    
    def test_template_engine_initialization(self, settings):
        """Test template engine initialization."""
        engine = TemplateEngine(settings)
        
        assert engine.settings == settings
        assert engine.naming is not None
        assert engine.django_helper is not None
        assert engine.env is not None
    
    def test_render_template_basic(self, template_engine, temp_template_dir):
        """Test basic template rendering."""
        # Add temp directory to template dirs
        template_engine.template_dirs.append(temp_template_dir)
        template_engine.env.loader.searchpath.append(temp_template_dir)
        
        result = template_engine.render_template('test.j2', {'name': 'World'})
        assert result == 'Hello World!'
    
    def test_render_string(self, template_engine):
        """Test string template rendering."""
        template_string = 'Hello {{ name }}!'
        context = {'name': 'World'}
        
        result = template_engine.render_string(template_string, context)
        assert result == 'Hello World!'
    
    def test_naming_filters(self, template_engine):
        """Test naming convention filters."""
        template_string = '{{ "user_profile"|pascal_case }}'
        result = template_engine.render_string(template_string, {})
        assert result == 'UserProfile'
        
        template_string = '{{ "UserProfile"|snake_case }}'
        result = template_engine.render_string(template_string, {})
        assert result == 'user_profile'
    
    def test_django_filters(self, template_engine):
        """Test Django-specific filters."""
        template_string = '{{ "user"|model_name }}'
        result = template_engine.render_string(template_string, {})
        assert result == 'User'
        
        template_string = '{{ "FirstName"|field_name }}'
        result = template_engine.render_string(template_string, {})
        assert result == 'first_name'
    
    def test_type_conversion_filters(self, template_engine):
        """Test type conversion filters."""
        template_string = '{{ "CharField"|python_type }}'
        result = template_engine.render_string(template_string, {})
        assert result == 'str'
        
        template_string = '{{ "IntegerField"|graphql_type }}'
        result = template_engine.render_string(template_string, {})
        assert result == 'Int'
    
    def test_field_definition_filter(self, template_engine):
        """Test Django field definition filter."""
        field = {
            'type': 'CharField',
            'max_length': 100,
            'null': True,
            'blank': True
        }
        
        template_string = '{{ field|field_definition }}'
        result = template_engine.render_string(template_string, {'field': field})
        assert 'models.CharField(' in result
        assert 'max_length=100' in result
        assert 'null=True' in result
        assert 'blank=True' in result
    
    def test_indent_filter(self, template_engine):
        """Test indent filter."""
        template_string = '{{ "line1\nline2"|indent(4) }}'
        result = template_engine.render_string(template_string, {})
        assert result == 'line1\n    line2'
    
    def test_comment_filter(self, template_engine):
        """Test comment filter."""
        template_string = '{{ "This is a comment"|comment("python") }}'
        result = template_engine.render_string(template_string, {})
        assert result == '# This is a comment'
    
    def test_docstring_filter(self, template_engine):
        """Test docstring filter."""
        template_string = '{{ "This is a docstring"|docstring }}'
        result = template_engine.render_string(template_string, {})
        assert result == '"""This is a docstring"""'
    
    def test_group_by_filter(self, template_engine):
        """Test group_by filter."""
        items = [
            {'category': 'A', 'name': 'item1'},
            {'category': 'B', 'name': 'item2'},
            {'category': 'A', 'name': 'item3'},
        ]
        
        template_string = '{% set grouped = items|group_by("category") %}{{ grouped.A|length }}'
        result = template_engine.render_string(template_string, {'items': items})
        assert result == '2'
    
    def test_context_processors(self, template_engine):
        """Test context processors."""
        def test_processor(context):
            return {'processed': True}
        
        template_engine.add_context_processor(test_processor)
        
        template_string = '{{ processed }}'
        result = template_engine.render_string(template_string, {})
        assert result == 'True'
    
    def test_custom_functions(self, template_engine):
        """Test custom template functions."""
        template_string = '{{ range(3)|list|length }}'
        result = template_engine.render_string(template_string, {})
        assert result == '3'
    
    def test_error_handling(self, template_engine):
        """Test error handling."""
        with pytest.raises(Exception):
            template_engine.render_template('nonexistent.j2', {})
    
    def test_template_caching(self, template_engine, temp_template_dir):
        """Test template caching."""
        # Add temp directory to template dirs
        template_engine.template_dirs.append(temp_template_dir)
        template_engine.env.loader.searchpath.append(temp_template_dir)
        
        # First render
        result1 = template_engine.render_template('test.j2', {'name': 'World'})
        
        # Second render (should use cache)
        result2 = template_engine.render_template('test.j2', {'name': 'World'})
        
        assert result1 == result2
        assert 'test.j2' in template_engine._template_cache


class TestTemplateFilters:
    """Test template filters in isolation."""
    
    @pytest.fixture
    def template_engine(self):
        """Create template engine instance."""
        return TemplateEngine()
    
    def test_python_type_conversion(self, template_engine):
        """Test Python type conversion."""
        assert template_engine._get_python_type('CharField') == 'str'
        assert template_engine._get_python_type('IntegerField') == 'int'
        assert template_engine._get_python_type('BooleanField') == 'bool'
        assert template_engine._get_python_type('ForeignKey') == 'Optional[int]'
    
    def test_graphql_type_conversion(self, template_engine):
        """Test GraphQL type conversion."""
        assert template_engine._get_graphql_type('CharField') == 'String'
        assert template_engine._get_graphql_type('IntegerField') == 'Int'
        assert template_engine._get_graphql_type('BooleanField') == 'Boolean'
        assert template_engine._get_graphql_type('ForeignKey') == 'ID'
    
    def test_typescript_type_conversion(self, template_engine):
        """Test TypeScript type conversion."""
        assert template_engine._get_typescript_type('CharField') == 'string'
        assert template_engine._get_typescript_type('IntegerField') == 'number'
        assert template_engine._get_typescript_type('BooleanField') == 'boolean'
        assert template_engine._get_typescript_type('ForeignKey') == 'number | null'
    
    def test_field_choices_formatting(self, template_engine):
        """Test field choices formatting."""
        choices = {'active': 'Active', 'inactive': 'Inactive'}
        result = template_engine._get_field_choices(choices)
        assert "('active', 'Active')" in result
        assert "('inactive', 'Inactive')" in result
    
    def test_api_endpoint_generation(self, template_engine):
        """Test API endpoint generation."""
        assert template_engine._get_api_endpoint('User', 'list') == '/api/v1/users/'
        assert template_engine._get_api_endpoint('User', 'detail') == '/api/v1/users/{id}/'
    
    def test_url_pattern_generation(self, template_engine):
        """Test URL pattern generation."""
        assert template_engine._get_url_pattern('User', 'list') == 'users/'
        assert template_engine._get_url_pattern('User', 'detail') == 'users/<int:pk>/'
        assert template_engine._get_url_pattern('User', 'create') == 'users/create/'


class TestTemplateHelpers:
    """Test template helper functions."""
    
    @pytest.fixture
    def template_engine(self):
        """Create template engine instance."""
        return TemplateEngine()
    
    def test_related_name_generation(self, template_engine):
        """Test related name generation."""
        result = template_engine._get_related_name('User', 'Post', 'author')
        assert 'posts' in result.lower()
    
    def test_model_permissions_generation(self, template_engine):
        """Test model permissions generation."""
        permissions = template_engine._get_model_permissions('User')
        assert len(permissions) == 4
        assert any('add_user' in perm for perm in permissions)
        assert any('change_user' in perm for perm in permissions)
        assert any('delete_user' in perm for perm in permissions)
        assert any('view_user' in perm for perm in permissions)
    
    def test_import_statement_generation(self, template_engine):
        """Test import statement generation."""
        result = template_engine._get_import_statement('django.db', 'models')
        assert result == 'from django.db import models'
        
        result = template_engine._get_import_statement('django.db', ['models', 'transaction'])
        assert result == 'from django.db import models, transaction'


@pytest.mark.integration
class TestTemplateEngineIntegration:
    """Integration tests for template engine."""
    
    def test_complete_model_template(self):
        """Test rendering a complete model template."""
        engine = TemplateEngine()
        
        context = {
            'app_name': 'blog',
            'models': [
                {
                    'name': 'Post',
                    'description': 'Blog post model',
                    'fields': [
                        {'name': 'title', 'type': 'CharField', 'max_length': 200},
                        {'name': 'content', 'type': 'TextField'},
                        {'name': 'published', 'type': 'BooleanField', 'default': False},
                        {'name': 'created_at', 'type': 'DateTimeField', 'auto_now_add': True},
                    ],
                    'meta': {
                        'ordering': ['-created_at'],
                        'verbose_name': 'Blog Post',
                        'verbose_name_plural': 'Blog Posts',
                    }
                }
            ],
            'imports': {
                'django': ['from django.db import models'],
            }
        }
        
        template_string = '''
{% for model in models %}
class {{ model.name }}(models.Model):
    """{{ model.description }}"""
    {% for field in model.fields %}
    {{ field.name }} = {{ field|field_definition }}
    {% endfor %}
    
    class Meta:
        {% for key, value in model.meta.items() %}
        {{ key }} = {{ value|repr }}
        {% endfor %}
{% endfor %}
        '''.strip()
        
        result = engine.render_string(template_string, context)
        
        assert 'class Post(models.Model):' in result
        assert 'title = models.CharField(max_length=200)' in result
        assert 'content = models.TextField()' in result
        assert 'published = models.BooleanField(default=False)' in result
        assert 'created_at = models.DateTimeField(auto_now_add=True)' in result
        assert 'class Meta:' in result