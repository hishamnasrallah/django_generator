
# {{ project_title }} Documentation

Welcome to the documentation for {{ project_title }}.

## Overview

{{ project.description | default('This project was generated using Django Enhanced Generator.', true) }}

## Getting Started

Please refer to the main [README.md](../README.md) for quick start instructions.

## Documentation Structure

- [Architecture](ARCHITECTURE.md) - System architecture and design decisions
- [API Documentation](API.md) - API endpoints and usage
- [Deployment Guide](DEPLOYMENT.md) - Deployment instructions
- [Contributing Guide](CONTRIBUTING.md) - How to contribute to the project

## Quick Links

- **Admin Panel**: [http://localhost:8000/admin/](http://localhost:8000/admin/)
  {% if features.api.rest_framework %}
- **API Documentation**: [http://localhost:8000/api/swagger/](http://localhost:8000/api/swagger/)
  {% endif %}
  {% if features.api.graphql %}
- **GraphQL Playground**: [http://localhost:8000/graphql/](http://localhost:8000/graphql/)
  {% endif %}

## Project Structure
{{ project_name }}/
├── apps/               # Django applications
{% for app in apps %}
│   ├── {{ app.name }}/
{% endfor %}
├── {{ project_name }}/         # Project configuration
├── docs/               # Documentation
├── static/             # Static files
├── media/              # User-uploaded files
├── templates/          # HTML templates
└── requirements/       # Dependencies

## Key Features

{% if features.api.rest_framework %}
- ✅ REST API with Django REST Framework
  {% endif %}
  {% if features.api.graphql %}
- ✅ GraphQL API support
  {% endif %}
  {% if features.api.websockets %}
- ✅ WebSocket support for real-time features
  {% endif %}
  {% if features.authentication.jwt %}
- ✅ JWT authentication
  {% endif %}
  {% if features.authentication.oauth2 %}
- ✅ OAuth2 authentication ({{ features.authentication.oauth2.providers | join(', ') }})
  {% endif %}
  {% if features.performance.caching %}
- ✅ Caching with {{ features.performance.caching.backend }}
  {% endif %}
  {% if features.performance.celery %}
- ✅ Asynchronous task processing with Celery
  {% endif %}
  {% if features.deployment.docker %}
- ✅ Docker support
  {% endif %}
  {% if features.deployment.kubernetes %}
- ✅ Kubernetes deployment ready
  {% endif %}