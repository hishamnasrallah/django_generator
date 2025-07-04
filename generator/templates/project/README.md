# {{ project_title }}

{{ project.description | default('A Django application built with Django Enhanced Generator', true) }}

## Features

{% if features.api %}
- **API**: {% if features.api.rest_framework %}REST API with Django REST Framework{% endif %}{% if features.api.graphql %}, GraphQL support{% endif %}{% if features.api.websockets %}, WebSocket support{% endif %}
  {% endif %}
  {% if features.authentication %}
- **Authentication**: {% if features.authentication.jwt %}JWT tokens{% endif %}{% if features.authentication.oauth2 %}, OAuth2 ({{ features.authentication.oauth2.providers | join(', ') }}){% endif %}{% if features.authentication.two_factor %}, Two-factor authentication{% endif %}
  {% endif %}
  {% if features.database %}
- **Database**: {{ features.database.engine | default('PostgreSQL') }}{% if features.database.read_replica %} with read replicas{% endif %}
  {% endif %}
  {% if features.performance %}
- **Performance**: {% if features.performance.caching %}{{ features.performance.caching.backend | default('Redis') }} caching{% endif %}{% if features.performance.celery %}, Celery task queue{% endif %}{% if features.performance.elasticsearch %}, Elasticsearch{% endif %}
  {% endif %}
  {% if features.deployment %}
- **Deployment**: {% if features.deployment.docker %}Docker{% endif %}{% if features.deployment.kubernetes %}, Kubernetes{% endif %}{% if features.deployment.ci_cd %}, CI/CD with {{ features.deployment.ci_cd }}{% endif %}
  {% endif %}

## Quick Start

### Prerequisites

- Python {{ python_version }}+
- {% if features.database.engine == 'postgresql' %}PostgreSQL{% elif features.database.engine == 'mysql' %}MySQL{% else %}SQLite{% endif %}
  {% if features.performance.caching %}- Redis{% endif %}
  {% if features.deployment.docker %}- Docker and Docker Compose{% endif %}

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd {{ project_name }}
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/development.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

{% if features.deployment.docker %}
5. **Start services with Docker**
   ```bash
   docker-compose up -d
   ```
{% else %}
5. **Set up the database**
   ```bash
   # Create database
   createdb {{ project_name }}
   ```
{% endif %}

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

Visit http://localhost:8000 to see the application.

## Project Structure

```
{{ project_name }}/
├── {{ project_name }}/          # Django project directory
│   ├── settings/                # Settings module
│   │   ├── base.py             # Base settings
│   │   ├── development.py      # Development settings
│   │   ├── staging.py          # Staging settings
│   │   ├── production.py       # Production settings
│   │   └── testing.py          # Test settings
│   ├── urls.py                 # URL configuration
│   ├── wsgi.py                 # WSGI configuration
{% if features.api.websockets %}│   ├── asgi.py                 # ASGI configuration
{% endif %}{% if features.performance.celery %}│   └── celery.py               # Celery configuration
{% endif %}├── apps/                        # Django applications
{% for app in apps %}│   ├── {{ app.name }}/
{% endfor %}├── static/                      # Static files
├── media/                       # Media files
├── templates/                   # HTML templates
├── requirements/                # Requirements files
├── docs/                        # Documentation
{% if features.deployment.docker %}├── docker/                      # Docker configuration
├── docker-compose.yml           # Docker Compose configuration
{% endif %}{% if features.deployment.ci_cd %}├── .github/workflows/           # CI/CD workflows
{% endif %}└── manage.py                    # Django management script
```

## Available Commands

### Management Commands

```bash
# Run tests
python manage.py test

# Create new app
python manage.py startapp <app_name>

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic
```

{% if features.deployment.docker %}
### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Run commands in container
docker-compose exec web python manage.py <command>

# Stop all services
docker-compose down
```
{% endif %}

{% if features.performance.celery %}
### Celery Commands

```bash
# Start Celery worker
celery -A {{ project_name }} worker -l info

# Start Celery beat
celery -A {{ project_name }} beat -l info

# Start Flower (Celery monitoring)
celery -A {{ project_name }} flower
```
{% endif %}

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov={{ project_name }} --cov-report=html

# Run specific test
pytest apps/<app_name>/tests/test_<module>.py
```

## API Documentation

{% if features.api.rest_framework %}
### REST API

API documentation is available at:
- Swagger UI: http://localhost:8000/api/swagger/
- ReDoc: http://localhost:8000/api/redoc/
  {% endif %}

{% if features.api.graphql %}
### GraphQL

GraphQL playground is available at:
- http://localhost:8000/graphql/
  {% endif %}

## Deployment

### Production Deployment

1. **Set environment variables**
   ```bash
   export DJANGO_SETTINGS_MODULE={{ project_name }}.settings.production
   export SECRET_KEY=<your-secret-key>
   export DATABASE_URL=<your-database-url>
   ```

2. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Run migrations**
   ```bash
   python manage.py migrate
   ```

4. **Start application**
   ```bash
   gunicorn {{ project_name }}.wsgi:application
   ```

{% if features.deployment.kubernetes %}
### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods
```
{% endif %}

## Contributing

Please read [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, email support@example.com or create an issue in the repository.

---

Generated with [Django Enhanced Generator](https://github.com/django-enhanced-generator/)