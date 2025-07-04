"""
Django Enhanced Code Generator Setup
"""
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='django-enhanced-generator',
    version='1.0.0',
    description='Advanced Django code generator for production-ready applications',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/django-enhanced-generator',
    author='Your Name',
    author_email='your.email@example.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Code Generators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
    ],
    keywords='django, code-generator, scaffolding, boilerplate, productivity',
    packages=find_packages(exclude=['tests*']),
    python_requires='>=3.9',
    install_requires=[
        'Django>=4.2',
        'click>=8.0',
        'jinja2>=3.0',
        'pyyaml>=6.0',
        'inflection>=0.5',
        'black>=23.0',
        'isort>=5.0',
        'pylint>=2.0',
        'colorama>=0.4',
        'rich>=13.0',
        'pydantic>=2.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0',
            'pytest-django>=4.0',
            'pytest-cov>=4.0',
            'pytest-mock>=3.0',
            'factory-boy>=3.0',
            'faker>=18.0',
        ],
        'docs': [
            'sphinx>=6.0',
            'sphinx-rtd-theme>=1.0',
            'sphinx-click>=4.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'django-gen=django_enhanced_generator.cli:cli',
        ],
    },
    include_package_data=True,
    package_data={
        'django_enhanced_generator': [
            'templates/**/*.j2',
            'config/*.yaml',
        ],
    },
)