"""
Pytest configuration and fixtures for Django Enhanced Generator tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from generator.config.settings import Settings


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings()


@pytest.fixture
def sample_schema():
    """Create a sample schema for testing."""
    return {
        'project': {
            'name': 'test_project',
            'description': 'A test Django project',
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
                'name': 'blog',
                'description': 'Blog application',
                'models': [
                    {
                        'name': 'Post',
                        'description': 'Blog post model',
                        'fields': [
                            {
                                'name': 'title',
                                'type': 'CharField',
                                'max_length': 200,
                                'help_text': 'Post title'
                            },
                            {
                                'name': 'content',
                                'type': 'TextField',
                                'help_text': 'Post content'
                            },
                            {
                                'name': 'published',
                                'type': 'BooleanField',
                                'default': False,
                                'help_text': 'Is post published'
                            },
                            {
                                'name': 'created_at',
                                'type': 'DateTimeField',
                                'auto_now_add': True
                            },
                            {
                                'name': 'updated_at',
                                'type': 'DateTimeField',
                                'auto_now': True
                            }
                        ],
                        'meta': {
                            'ordering': ['-created_at'],
                            'verbose_name': 'Blog Post',
                            'verbose_name_plural': 'Blog Posts'
                        }
                    },
                    {
                        'name': 'Category',
                        'description': 'Blog category model',
                        'fields': [
                            {
                                'name': 'name',
                                'type': 'CharField',
                                'max_length': 100,
                                'unique': True
                            },
                            {
                                'name': 'slug',
                                'type': 'SlugField',
                                'unique': True
                            },
                            {
                                'name': 'description',
                                'type': 'TextField',
                                'blank': True
                            }
                        ]
                    }
                ]
            },
            {
                'name': 'accounts',
                'description': 'User accounts application',
                'models': [
                    {
                        'name': 'Profile',
                        'description': 'User profile model',
                        'fields': [
                            {
                                'name': 'user',
                                'type': 'OneToOneField',
                                'to': 'auth.User',
                                'on_delete': 'CASCADE'
                            },
                            {
                                'name': 'bio',
                                'type': 'TextField',
                                'blank': True,
                                'help_text': 'User biography'
                            },
                            {
                                'name': 'avatar',
                                'type': 'ImageField',
                                'upload_to': 'avatars/',
                                'blank': True,
                                'null': True
                            },
                            {
                                'name': 'birth_date',
                                'type': 'DateField',
                                'blank': True,
                                'null': True
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def minimal_schema():
    """Create a minimal schema for testing."""
    return {
        'project': {
            'name': 'minimal_project'
        },
        'apps': [
            {
                'name': 'core',
                'models': [
                    {
                        'name': 'Item',
                        'fields': [
                            {
                                'name': 'name',
                                'type': 'CharField',
                                'max_length': 100
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_generator():
    """Create a mock generator for testing."""
    generator = Mock()
    generator.name = 'MockGenerator'
    generator.description = 'Mock generator for testing'
    generator.version = '1.0.0'
    generator.order = 10
    generator.requires = set()
    generator.provides = {'mock_feature'}
    generator.can_generate.return_value = True
    generator.generate.return_value = []
    return generator


@pytest.fixture
def mock_file_generator():
    """Create a mock file generator for testing."""
    file_gen = Mock()
    file_gen.generate_file_from_template.return_value = Mock()
    file_gen.generate_file_from_string.return_value = Mock()
    file_gen.copy_file.return_value = Mock()
    file_gen.create_directory.return_value = Mock()
    file_gen.get_stats.return_value = {
        'files_generated': 0,
        'files_skipped': 0,
        'templates_rendered': 0
    }
    return file_gen


@pytest.fixture
def mock_template_engine():
    """Create a mock template engine for testing."""
    engine = Mock()
    engine.render_template.return_value = "Rendered template content"
    engine.render_string.return_value = "Rendered string content"
    return engine


@pytest.fixture
def test_template_content():
    """Sample template content for testing."""
    return """
{% for model in models %}
class {{ model.name }}(models.Model):
    """{{ model.description }}"""
    {% for field in model.fields %}
    {{ field.name }} = {{ field|django_field }}
    {% endfor %}
    
    class Meta:
        verbose_name = "{{ model.name|verbose_name }}"
        verbose_name_plural = "{{ model.name|plural|verbose_name }}"
        {% if model.meta %}
        {% for key, value in model.meta.items() %}
        {{ key }} = {{ value|repr }}
        {% endfor %}
        {% endif %}
    
    def __str__(self):
        {% for field in model.fields %}
        {% if field.name in ['name', 'title'] %}
        return str(self.{{ field.name }})
        {% endif %}
        {% else %}
        return f"{{ model.name }} #{self.pk}"
        {% endfor %}
{% endfor %}
    """.strip()


@pytest.fixture
def expected_model_output():
    """Expected output for model generation."""
    return """
class Post(models.Model):
    \"\"\"Blog post model\"\"\"
    title = models.CharField(max_length=200)
    content = models.TextField()
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ['-created_at']
    
    def __str__(self):
        return str(self.title)
    """.strip()


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any global state that might interfere with tests
    yield
    # Cleanup after test
    pass


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add markers based on test location
    for item in items:
        # Mark integration tests
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Mark slow tests
        if "test_slow" in item.nodeid or "test_performance" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # Mark unit tests (default)
        if not any(marker.name in ['integration', 'slow'] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Test utilities
class TestUtils:
    """Utility functions for tests."""
    
    @staticmethod
    def create_test_file(path: Path, content: str) -> Path:
        """Create a test file with content."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path
    
    @staticmethod
    def assert_file_exists(path: Path, content_contains: str = None):
        """Assert that a file exists and optionally contains specific content."""
        assert path.exists(), f"File {path} does not exist"
        
        if content_contains:
            content = path.read_text()
            assert content_contains in content, f"File {path} does not contain '{content_contains}'"
    
    @staticmethod
    def assert_directory_structure(base_path: Path, expected_structure: dict):
        """Assert that a directory has the expected structure."""
        for name, content in expected_structure.items():
            path = base_path / name
            
            if isinstance(content, dict):
                # It's a directory
                assert path.is_dir(), f"Expected directory {path} does not exist"
                TestUtils.assert_directory_structure(path, content)
            else:
                # It's a file
                assert path.is_file(), f"Expected file {path} does not exist"
                if content:  # If content is specified, check it
                    file_content = path.read_text()
                    assert content in file_content, f"File {path} does not contain expected content"


@pytest.fixture
def test_utils():
    """Provide test utilities."""
    return TestUtils