"""
Tests for File Generator
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from generator.core.file_generator import FileGenerator, ConflictResolver
from generator.core.base_generator import GeneratedFile
from generator.config.settings import Settings


class TestFileGenerator:
    """Test cases for FileGenerator."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def file_generator(self, settings, temp_dir):
        """Create file generator instance."""
        return FileGenerator(settings, output_dir=temp_dir)
    
    @pytest.fixture
    def mock_template_engine(self):
        """Create mock template engine."""
        mock_engine = Mock()
        mock_engine.render_template.return_value = "Generated content"
        mock_engine.render_string.return_value = "Generated content"
        return mock_engine
    
    def test_file_generator_initialization(self, settings, temp_dir):
        """Test file generator initialization."""
        generator = FileGenerator(settings, output_dir=temp_dir)
        
        assert generator.settings == settings
        assert generator.template_engine is not None
        assert generator.code_formatter is not None
        assert generator.fs_manager is not None
        assert generator.generated_files == []
        assert generator.stats['files_generated'] == 0
    
    def test_generate_file_from_template(self, file_generator, mock_template_engine):
        """Test generating file from template."""
        file_generator.template_engine = mock_template_engine
        
        result = file_generator.generate_file_from_template(
            template_name='test.j2',
            output_path='test.py',
            context={'name': 'test'}
        )
        
        assert result is not None
        assert result.path == 'test.py'
        assert result.content == "Generated content"
        assert result.file_type == 'python'
        assert len(file_generator.generated_files) == 1
        assert file_generator.stats['files_generated'] == 1
        
        mock_template_engine.render_template.assert_called_once_with('test.j2', {'name': 'test'})
    
    def test_generate_file_from_string(self, file_generator, mock_template_engine):
        """Test generating file from template string."""
        file_generator.template_engine = mock_template_engine
        
        result = file_generator.generate_file_from_string(
            template_string='Hello {{ name }}!',
            output_path='test.txt',
            context={'name': 'World'}
        )
        
        assert result is not None
        assert result.path == 'test.txt'
        assert result.content == "Generated content"
        assert result.file_type == 'text'
        
        mock_template_engine.render_string.assert_called_once_with('Hello {{ name }}!', {'name': 'World'})
    
    def test_copy_file(self, file_generator, temp_dir):
        """Test copying file."""
        # Create source file
        source_path = Path(temp_dir) / 'source.txt'
        source_path.write_text('Source content')
        
        result = file_generator.copy_file(
            source_path=str(source_path),
            dest_path='dest.txt'
        )
        
        assert result is not None
        assert result.path == 'dest.txt'
        assert result.content == 'Source content'
        assert result.metadata['operation'] == 'copy'
    
    def test_copy_nonexistent_file(self, file_generator):
        """Test copying nonexistent file."""
        with pytest.raises(RuntimeError):
            file_generator.copy_file(
                source_path='nonexistent.txt',
                dest_path='dest.txt'
            )
    
    def test_create_directory(self, file_generator):
        """Test creating directory."""
        result = file_generator.create_directory('test_dir')
        
        assert result is not None
        assert result.exists()
        assert result.is_dir()
    
    def test_batch_generate(self, file_generator, mock_template_engine):
        """Test batch file generation."""
        file_generator.template_engine = mock_template_engine
        
        file_specs = [
            {
                'template': 'test1.j2',
                'output_path': 'test1.py',
                'context': {'name': 'test1'}
            },
            {
                'template_string': 'Hello {{ name }}!',
                'output_path': 'test2.txt',
                'context': {'name': 'test2'}
            }
        ]
        
        results = file_generator.batch_generate(file_specs)
        
        assert len(results) == 2
        assert results[0].path == 'test1.py'
        assert results[1].path == 'test2.txt'
        assert file_generator.stats['files_generated'] == 2
    
    def test_file_type_detection(self, file_generator):
        """Test file type detection."""
        assert file_generator._get_file_type('test.py') == 'python'
        assert file_generator._get_file_type('test.js') == 'javascript'
        assert file_generator._get_file_type('test.html') == 'html'
        assert file_generator._get_file_type('test.css') == 'css'
        assert file_generator._get_file_type('test.yml') == 'yaml'
        assert file_generator._get_file_type('test.json') == 'json'
        assert file_generator._get_file_type('Dockerfile') == 'dockerfile'
        assert file_generator._get_file_type('test.unknown') == 'text'
    
    def test_get_stats(self, file_generator):
        """Test getting generation statistics."""
        stats = file_generator.get_stats()
        
        assert 'files_generated' in stats
        assert 'files_skipped' in stats
        assert 'templates_rendered' in stats
        assert 'total_files' in stats
        assert 'fs_stats' in stats
    
    def test_get_generated_files(self, file_generator, mock_template_engine):
        """Test getting generated files list."""
        file_generator.template_engine = mock_template_engine
        
        file_generator.generate_file_from_template(
            template_name='test.j2',
            output_path='test.py',
            context={}
        )
        
        files = file_generator.get_generated_files()
        
        assert len(files) == 1
        assert files[0].path == 'test.py'
        assert isinstance(files, list)  # Should be a copy
    
    def test_dry_run_mode(self, settings, temp_dir):
        """Test dry run mode."""
        generator = FileGenerator(settings, output_dir=temp_dir, dry_run=True)
        mock_engine = Mock()
        mock_engine.render_template.return_value = "Generated content"
        generator.template_engine = mock_engine
        
        result = generator.generate_file_from_template(
            template_name='test.j2',
            output_path='test.py',
            context={}
        )
        
        assert result is not None
        assert result.path == 'test.py'
        # File should not actually be written in dry run mode
        assert not (Path(temp_dir) / 'test.py').exists()
    
    def test_force_mode(self, file_generator, mock_template_engine):
        """Test force overwrite mode."""
        file_generator.template_engine = mock_template_engine
        
        # Create existing file
        existing_path = Path(file_generator.fs_manager.output_dir) / 'test.py'
        existing_path.write_text('Existing content')
        
        # Generate with force mode
        file_generator.fs_manager.force = True
        
        result = file_generator.generate_file_from_template(
            template_name='test.j2',
            output_path='test.py',
            context={}
        )
        
        assert result is not None
        # File should be overwritten
        assert existing_path.read_text() == "Generated content"


class TestConflictResolver:
    """Test cases for ConflictResolver."""
    
    @pytest.fixture
    def resolver(self):
        """Create conflict resolver instance."""
        return ConflictResolver()
    
    def test_overwrite_strategy(self, resolver):
        """Test overwrite strategy."""
        existing = "Old content"
        new = "New content"
        
        result_content, should_write = resolver.resolve_conflict(existing, new, 'overwrite')
        
        assert result_content == new
        assert should_write is True
    
    def test_skip_strategy(self, resolver):
        """Test skip strategy."""
        existing = "Old content"
        new = "New content"
        
        result_content, should_write = resolver.resolve_conflict(existing, new, 'skip')
        
        assert result_content == existing
        assert should_write is False
    
    def test_backup_strategy(self, resolver):
        """Test backup strategy."""
        existing = "Old content"
        new = "New content"
        
        result_content, should_write = resolver.resolve_conflict(existing, new, 'backup')
        
        assert result_content == new
        assert should_write is True
    
    def test_merge_strategy_identical(self, resolver):
        """Test merge strategy with identical content."""
        existing = "Same content"
        new = "Same content"
        
        result_content, should_write = resolver.resolve_conflict(existing, new, 'merge')
        
        assert result_content == existing
        assert should_write is False
    
    def test_merge_strategy_different(self, resolver):
        """Test merge strategy with different content."""
        existing = "Old content"
        new = "New content"
        
        result_content, should_write = resolver.resolve_conflict(existing, new, 'merge')
        
        assert "Old content" in result_content
        assert "New content" in result_content
        assert should_write is True
    
    def test_unknown_strategy(self, resolver):
        """Test unknown strategy falls back to backup."""
        existing = "Old content"
        new = "New content"
        
        result_content, should_write = resolver.resolve_conflict(existing, new, 'unknown')
        
        assert result_content == new
        assert should_write is True


@pytest.mark.integration
class TestFileGeneratorIntegration:
    """Integration tests for file generator."""
    
    def test_complete_file_generation_workflow(self):
        """Test complete file generation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings()
            generator = FileGenerator(settings, output_dir=temp_dir)
            
            # Mock template engine
            mock_engine = Mock()
            mock_engine.render_template.return_value = '''
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
            '''.strip()
            generator.template_engine = mock_engine
            
            # Generate file
            result = generator.generate_file_from_template(
                template_name='models.py.j2',
                output_path='app/models.py',
                context={'model_name': 'TestModel'}
            )
            
            # Verify file was created
            output_path = Path(temp_dir) / 'app' / 'models.py'
            assert output_path.exists()
            
            # Verify content
            content = output_path.read_text()
            assert 'class TestModel(models.Model):' in content
            assert 'name = models.CharField(max_length=100)' in content
            
            # Verify metadata
            assert result.path == 'app/models.py'
            assert result.file_type == 'python'
            assert result.metadata['template'] == 'models.py.j2'
            assert result.metadata['generator'] == 'FileGenerator'
    
    def test_error_handling_in_generation(self):
        """Test error handling during generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings()
            generator = FileGenerator(settings, output_dir=temp_dir)
            
            # Mock template engine to raise error
            mock_engine = Mock()
            mock_engine.render_template.side_effect = Exception("Template error")
            generator.template_engine = mock_engine
            
            # Should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                generator.generate_file_from_template(
                    template_name='test.j2',
                    output_path='test.py',
                    context={}
                )
            
            assert "Template error" in str(exc_info.value)
    
    def test_file_formatting_integration(self):
        """Test file formatting integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings()
            generator = FileGenerator(settings, output_dir=temp_dir)
            
            # Mock template engine with unformatted Python code
            mock_engine = Mock()
            mock_engine.render_template.return_value = 'def test():pass'
            generator.template_engine = mock_engine
            
            # Generate file
            result = generator.generate_file_from_template(
                template_name='test.py.j2',
                output_path='test.py',
                context={}
            )
            
            # Content should be formatted (though exact formatting depends on formatter)
            assert result.content != 'def test():pass'  # Should be different after formatting