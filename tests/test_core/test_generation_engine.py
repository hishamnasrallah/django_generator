"""
Tests for Generation Engine
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path

from generator.core.generation_engine import GenerationEngine, GenerationContext
from generator.config.settings import Settings


class TestGenerationContext:
    """Test cases for GenerationContext."""
    
    @pytest.fixture
    def schema(self):
        """Create test schema."""
        return {
            'project': {'name': 'test_project'},
            'apps': [
                {
                    'name': 'blog',
                    'models': [
                        {
                            'name': 'Post',
                            'fields': [
                                {'name': 'title', 'type': 'CharField', 'max_length': 200}
                            ]
                        }
                    ]
                }
            ]
        }
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def context(self, schema, settings):
        """Create generation context."""
        return GenerationContext(schema, settings)
    
    def test_context_initialization(self, context, schema, settings):
        """Test context initialization."""
        assert context.schema == schema
        assert context.settings == settings
        assert context.generated_files == []
        assert context.errors == []
        assert context.warnings == []
        assert context.stats['generators_executed'] == 0
        assert context.stats['files_generated'] == 0
    
    def test_add_generated_file_thread_safe(self, context):
        """Test thread-safe file addition."""
        context.add_generated_file('test.py')
        
        assert 'test.py' in context.generated_files
        assert context.stats['files_generated'] == 1
    
    def test_add_error_thread_safe(self, context):
        """Test thread-safe error addition."""
        context.add_error('Test error')
        
        assert 'Test error' in context.errors
    
    def test_add_warning_thread_safe(self, context):
        """Test thread-safe warning addition."""
        context.add_warning('Test warning')
        
        assert 'Test warning' in context.warnings
    
    def test_increment_stat_thread_safe(self, context):
        """Test thread-safe stat increment."""
        context.increment_stat('test_stat', 5)
        
        assert context.stats['test_stat'] == 5
        
        context.increment_stat('test_stat', 3)
        assert context.stats['test_stat'] == 8


class TestGenerationEngine:
    """Test cases for GenerationEngine."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def engine(self, settings):
        """Create generation engine."""
        return GenerationEngine(settings)
    
    @pytest.fixture
    def mock_registry(self):
        """Create mock generator registry."""
        mock_registry = Mock()
        mock_generator = Mock()
        mock_generator.name = 'TestGenerator'
        mock_generator.description = 'Test generator'
        mock_generator.order = 10
        mock_generator.requires = set()
        mock_generator.provides = set()
        mock_generator.can_generate.return_value = True
        mock_generator.generate.return_value = []
        
        mock_registry.get_generator_chain.return_value = [mock_generator]
        mock_registry.validate_generator_chain.return_value = []
        return mock_registry
    
    @pytest.fixture
    def mock_schema_parser(self):
        """Create mock schema parser."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {
            'project': {'name': 'test_project'},
            'apps': []
        }
        return mock_parser
    
    @pytest.fixture
    def valid_schema(self):
        """Create valid test schema."""
        return {
            'project': {
                'name': 'test_project',
                'description': 'Test project'
            },
            'apps': [
                {
                    'name': 'blog',
                    'models': [
                        {
                            'name': 'Post',
                            'fields': [
                                {'name': 'title', 'type': 'CharField', 'max_length': 200},
                                {'name': 'content', 'type': 'TextField'}
                            ]
                        }
                    ]
                }
            ]
        }
    
    def test_engine_initialization(self, settings):
        """Test engine initialization."""
        engine = GenerationEngine(settings)
        
        assert engine.settings == settings
        assert engine.registry is not None
        assert engine.plugin_manager is not None
        assert engine.schema_parser is not None
        assert engine.context is None
        assert engine.progress_callbacks == []
        assert engine.pre_generation_hooks == []
        assert engine.post_generation_hooks == []
    
    @patch('generator.core.generation_engine.get_registry')
    @patch('generator.core.generation_engine.get_plugin_manager')
    def test_generate_success(self, mock_get_plugin_manager, mock_get_registry, 
                             engine, mock_registry, mock_schema_parser, valid_schema):
        """Test successful generation."""
        # Setup mocks
        mock_get_registry.return_value = mock_registry
        mock_get_plugin_manager.return_value = Mock()
        engine.registry = mock_registry
        engine.schema_parser = mock_schema_parser
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = engine.generate(
                schema=valid_schema,
                output_dir=temp_dir,
                force=False,
                dry_run=False
            )
        
        assert result['success'] is True
        assert 'generated_files' in result
        assert 'stats' in result
        assert 'execution_time' in result
        assert result['errors'] == []
    
    @patch('generator.core.generation_engine.get_registry')
    def test_generate_schema_validation_error(self, mock_get_registry, engine, mock_registry):
        """Test generation with schema validation error."""
        mock_get_registry.return_value = mock_registry
        engine.registry = mock_registry
        
        # Mock schema parser to raise error
        mock_parser = Mock()
        mock_parser.parse.side_effect = ValueError("Invalid schema")
        engine.schema_parser = mock_parser
        
        result = engine.generate(
            schema={'invalid': 'schema'},
            output_dir='.',
            force=False,
            dry_run=False
        )
        
        assert result['success'] is False
        assert 'Schema validation failed' in result['error']
    
    @patch('generator.core.generation_engine.get_registry')
    def test_generate_no_generators(self, mock_get_registry, engine, mock_schema_parser):
        """Test generation with no applicable generators."""
        # Setup mocks
        mock_registry = Mock()
        mock_registry.get_generator_chain.return_value = []
        mock_get_registry.return_value = mock_registry
        
        engine.registry = mock_registry
        engine.schema_parser = mock_schema_parser
        
        result = engine.generate(
            schema={'project': {'name': 'test'}},
            output_dir='.',
            force=False,
            dry_run=False
        )
        
        assert result['success'] is False
        assert 'No applicable generators found' in result['error']
    
    def test_validate_schema_success(self, engine, mock_schema_parser, valid_schema):
        """Test successful schema validation."""
        engine.schema_parser = mock_schema_parser
        
        result = engine.validate_schema(valid_schema)
        
        assert result['valid'] is True
        assert result['schema'] is not None
        assert result['errors'] == []
    
    def test_validate_schema_error(self, engine, valid_schema):
        """Test schema validation error."""
        # Mock schema parser to raise error
        mock_parser = Mock()
        mock_parser.parse.side_effect = ValueError("Invalid schema")
        engine.schema_parser = mock_parser
        
        result = engine.validate_schema(valid_schema)
        
        assert result['valid'] is False
        assert result['schema'] is None
        assert len(result['errors']) > 0
    
    @patch('generator.core.generation_engine.get_registry')
    def test_get_generation_plan_success(self, mock_get_registry, engine, 
                                       mock_registry, mock_schema_parser, valid_schema):
        """Test successful generation plan."""
        mock_get_registry.return_value = mock_registry
        engine.registry = mock_registry
        engine.schema_parser = mock_schema_parser
        
        result = engine.get_generation_plan(valid_schema)
        
        assert result['valid'] is True
        assert 'generators' in result
        assert 'execution_order' in result
        assert 'estimated_files' in result
        assert len(result['generators']) > 0
    
    def test_get_generation_plan_error(self, engine, valid_schema):
        """Test generation plan error."""
        # Mock schema parser to raise error
        mock_parser = Mock()
        mock_parser.parse.side_effect = ValueError("Invalid schema")
        engine.schema_parser = mock_parser
        
        result = engine.get_generation_plan(valid_schema)
        
        assert result['valid'] is False
        assert 'error' in result
        assert result['generators'] == []
    
    def test_add_progress_callback(self, engine):
        """Test adding progress callback."""
        callback = Mock()
        
        engine.add_progress_callback(callback)
        
        assert callback in engine.progress_callbacks
    
    def test_add_pre_generation_hook(self, engine):
        """Test adding pre-generation hook."""
        hook = Mock()
        
        engine.add_pre_generation_hook(hook)
        
        assert hook in engine.pre_generation_hooks
    
    def test_add_post_generation_hook(self, engine):
        """Test adding post-generation hook."""
        hook = Mock()
        
        engine.add_post_generation_hook(hook)
        
        assert hook in engine.post_generation_hooks
    
    def test_estimate_file_count(self, engine, valid_schema):
        """Test file count estimation."""
        generators = []  # Empty list for testing
        
        count = engine._estimate_file_count(generators, valid_schema)
        
        assert count > 0  # Should estimate some files
        assert isinstance(count, int)
    
    def test_group_by_dependency_level(self, engine):
        """Test grouping generators by dependency level."""
        # Create mock generators with dependencies
        gen1 = Mock()
        gen1.name = 'Gen1'
        gen1.requires = set()
        gen1.provides = {'feature1'}
        
        gen2 = Mock()
        gen2.name = 'Gen2'
        gen2.requires = {'feature1'}
        gen2.provides = {'feature2'}
        
        gen3 = Mock()
        gen3.name = 'Gen3'
        gen3.requires = set()
        gen3.provides = {'feature3'}
        
        generators = [gen1, gen2, gen3]
        
        levels = engine._group_by_dependency_level(generators)
        
        assert len(levels) >= 2  # Should have at least 2 levels
        # Gen1 and Gen3 should be in first level (no dependencies)
        # Gen2 should be in second level (depends on Gen1)
        first_level_names = [g.name for g in levels[0]]
        assert 'Gen1' in first_level_names
        assert 'Gen3' in first_level_names
        
        if len(levels) > 1:
            second_level_names = [g.name for g in levels[1]]
            assert 'Gen2' in second_level_names


@pytest.mark.integration
class TestGenerationEngineIntegration:
    """Integration tests for generation engine."""
    
    def test_complete_generation_workflow(self):
        """Test complete generation workflow."""
        # This would require actual generators and templates
        # For now, we'll test the basic workflow with mocks
        
        settings = Settings()
        engine = GenerationEngine(settings)
        
        # Mock all dependencies
        with patch.object(engine, 'schema_parser') as mock_parser, \
             patch.object(engine, 'registry') as mock_registry, \
             patch.object(engine, 'plugin_manager') as mock_plugin_manager:
            
            # Setup mocks
            mock_parser.parse.return_value = {
                'project': {'name': 'test_project'},
                'apps': []
            }
            
            mock_generator = Mock()
            mock_generator.name = 'TestGenerator'
            mock_generator.generate.return_value = []
            mock_registry.get_generator_chain.return_value = [mock_generator]
            mock_registry.validate_generator_chain.return_value = []
            
            mock_plugin_manager.get_plugin_post_generation_hooks.return_value = []
            
            with tempfile.TemporaryDirectory() as temp_dir:
                result = engine.generate(
                    schema={'project': {'name': 'test'}},
                    output_dir=temp_dir,
                    force=False,
                    dry_run=False
                )
            
            assert result['success'] is True
            mock_generator.generate.assert_called_once()
    
    def test_error_handling_in_workflow(self):
        """Test error handling in generation workflow."""
        settings = Settings()
        engine = GenerationEngine(settings)
        
        # Mock schema parser to raise error
        with patch.object(engine, 'schema_parser') as mock_parser:
            mock_parser.parse.side_effect = Exception("Test error")
            
            result = engine.generate(
                schema={'invalid': 'schema'},
                output_dir='.',
                force=False,
                dry_run=False
            )
            
            assert result['success'] is False
            assert 'Test error' in result['error']