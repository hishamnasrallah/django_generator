"""
Generator modules for Django Enhanced Generator.
This file imports and registers all available generators.
"""

# Import all generators to make them discoverable
from generator.generators.api.serializer_generator import SerializerGenerator
from generator.generators.api.view_generator import ViewGenerator
from generator.generators.app.model_generator import ModelGenerator
from generator.generators.project.structure_generator import ProjectStructureGenerator

# Add more imports as needed based on what's actually implemented

# Export all generators
__all__ = [
    'SerializerGenerator',
    'ViewGenerator',
    'ModelGenerator',
    'ProjectStructureGenerator',
]