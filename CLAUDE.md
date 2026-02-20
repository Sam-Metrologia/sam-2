# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SAM Metrologia is a Django-based metrology management system for ISO/IEC 17020:2012 compliance. It handles equipment tracking, calibration scheduling, maintenance management, intermediate verifications (comprobaciones), and company management for metrology businesses. The system supports multi-tenant companies with equipment limits and subscription plans.

**Norm:** ISO/IEC 17020:2012 (Inspection Bodies)
**Language:** Spanish (Colombia)
**Version:** 2.0.0

## Current Status (Feb 19, 2026)

- **Tests:** 1,023 passing, 0 failing, 1 skipped
- **Coverage:** 57.91% (Goal: 70%)
- **Score:** 7.6/10 (audited)
- **Last Audit:** `auditorias/AUDITORIA_INTEGRAL_CERO_CONFIANZA_2026-02-19.md`
- **Dashboard Cache:** Habilitado (5 min, invalidado por signals)
- **Dependencies:** Actualizadas 2026-02-19 (32 CVEs corregidos)
- **Next:** Trial autoservicio + Onboarding + Pagos (`docs/PLAN_TRIAL_ONBOARDING_PAGOS.md`)

## Project Structure

```
sam-2/
  manage.py                  # Django management
  pyproject.toml             # pytest + coverage config
  requirements.txt           # Production dependencies
  requirements_test.txt      # Test dependencies
  Dockerfile / Procfile       # Deploy config
  render.yaml                # Render.com deploy
  start.sh / build.sh        # Deploy scripts
  run_tests.sh / .bat        # Test runners
  terminos_condiciones_v1.0.html  # Legal terms (loaded by management command)

  core/                      # Main Django app (all business logic)
    models.py                # All models (4,148 lines - needs refactoring)
    constants.py             # Centralized constants (327 lines)
    forms.py                 # All forms (1,742 lines)
    signals.py               # Cache invalidation signals
    urls.py                  # URL routing
    views/                   # Views organized by domain
      dashboard.py           # Main dashboard (optimized, cached)
      equipment.py           # Equipment CRUD
      reports.py             # PDF/Excel generation (3,699 lines)
      confirmacion.py        # Metrological confirmation
      comprobacion.py        # Intermediate verifications
      prestamos.py           # Equipment loans
      panel_decisiones.py    # Decision panel / analytics
      calendario.py          # Activity calendar
      aprobaciones.py        # Document approvals
      companies.py           # Company management
      activities.py          # Activity views
      maintenance.py         # Maintenance views
      admin.py               # Admin views
      scheduled_tasks_api.py # API for scheduled tasks
      terminos.py            # Terms & conditions
    services.py              # Business logic services
    services_new.py          # Optimized services (cache, file upload)
    monitoring.py            # System health monitoring
    notifications.py         # Notification system
    file_validators.py       # File upload validation
    storage_validators.py    # Storage limit validation
    zip_functions.py         # ZIP generation for equipment docs
    middleware.py            # Company middleware, security
    optimizations.py         # Query optimizations
    security.py              # Security utilities
    admin_services.py        # Admin business logic
    admin_views.py           # Admin extra views
    utils/                   # Utility modules
      analisis_financiero.py # Financial analysis
      decision_intelligence.py # Decision intelligence
      impersonation.py       # User impersonation
    static/                  # CSS, JS, images
    templates/               # App-specific templates
    templatetags/            # Custom template filters
    management/commands/     # Django management commands
    migrations/              # Database migrations

  proyecto_c/                # Django project settings
    settings.py              # Environment-based settings
    urls.py                  # Root URL config
    wsgi.py                  # WSGI entry point

  templates/                 # Global templates (base.html, etc.)

  tests/                     # All tests (pytest)
    conftest.py              # Shared fixtures
    factories.py             # Factory Boy factories
    test_critical/           # Critical flow tests
    test_integration/        # Integration tests
    test_models/             # Model tests
    test_monitoring/         # Monitoring tests
    test_notifications/      # Notification tests
    test_performance/        # Performance benchmarks
    test_security/           # Security tests
    test_services/           # Service layer tests
    test_views/              # View/endpoint tests
    test_zip/                # ZIP generation tests

  scripts/                   # Utility/diagnostic scripts (not auto-run)
  auditorias/                # Audit reports and plans
  docs/                      # Technical documentation
    PLAN_TRIAL_ONBOARDING_PAGOS.md  # Plan: trial + onboarding + pagos
    DEPENDENCY_MANAGEMENT.md         # Procedimiento actualizacion dependencias
    AUTO_UPDATE_DOCS.md              # Sistema auto-actualizacion docs
    BACKUP_RECOVERY.md               # Procedimiento backup/recovery
  backups/                   # Local backup files
  logs/                      # Application logs
  media/                     # Dev file uploads
  staticfiles/               # Collected static files
  htmlcov/                   # Coverage HTML report
```

## Development Commands

### Essential Commands
```bash
# Start development server
python manage.py runserver

# Apply database migrations
python manage.py migrate

# Create migrations after model changes
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Install dependencies
pip install -r requirements.txt

# Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### Testing
```bash
# Run all tests (recommended)
python -m pytest

# Run with coverage
python -m pytest --cov=core --cov-report=html --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_views/test_dashboard.py -v

# Run by marker
python -m pytest -m integration

# Check for issues
python manage.py check
```

### Test Organization

Tests are in `tests/` (configured in pyproject.toml `testpaths`). Structure:

| Directory | Purpose | Key modules covered |
|-----------|---------|-------------------|
| test_critical/ | Critical business flows | Multi-tenant, core workflows |
| test_integration/ | End-to-end workflows | Auth, equipment, company flows |
| test_models/ | Model unit tests | Empresa, Equipo, Usuario |
| test_monitoring/ | System health | monitoring.py (81.58%) |
| test_notifications/ | Notifications | notifications.py (56.72%) |
| test_performance/ | Benchmarks, cache | Dashboard perf, cache invalidation |
| test_security/ | File security | file_validators.py |
| test_services/ | Service layer | services_new.py (72.73%) |
| test_views/ | Views & endpoints | All view modules |
| test_zip/ | ZIP generation | zip_functions.py (49.22%) |

**Testing best practices:**
1. Use mocks only for external I/O (storage, email, cache)
2. Test error handling and edge cases
3. Run full suite before commits: `python -m pytest`
4. Keep coverage above 57%

### Deployment
```bash
# Production (from start.sh)
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn proyecto_c.wsgi:application

# ZIP processor
./start_zip_processor.sh
./stop_zip_processor.sh
./monitor_zip_system.sh
```

## Architecture

### Settings
Environment-based with automatic switching:
- **Dev**: SQLite, local storage, debug logging
- **Prod**: PostgreSQL (DATABASE_URL), AWS S3, JSON logging
- **Detection**: `RENDER_EXTERNAL_HOSTNAME` env var

### Multi-tenancy
All data is filtered by `empresa` (company). Key patterns:
- QuerySets: `Equipo.objects.filter(empresa=request.user.empresa)`
- Cache keys: `f"dashboard_{user.id}_{empresa_id}"`
- Middleware validates empresa on each request

### Caching
- **Dev**: Local memory cache
- **Prod + Redis**: Redis with connection pooling
- **Prod fallback**: Database cache (`sam_cache_table`)
- Dashboard cached for 5 min, auto-invalidated via signals

### Key Constants
All in `core/constants.py` - equipment states, loan states, service types, limits, messages, etc.

## Environment Variables

### Required (Production)
```
SECRET_KEY, DATABASE_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME, RENDER_EXTERNAL_HOSTNAME
```

### Optional
```
DEBUG_VALUE, REDIS_URL, EMAIL_HOST, EMAIL_HOST_USER,
EMAIL_HOST_PASSWORD, ADMIN_EMAIL
```

## Known Technical Debt

- `core/models.py`: 4,148 lines (should be split into modules)
- `core/views/reports.py`: 3,699 lines (has helpers but still large)
- `core/forms.py`: 1,742 lines (should split by domain)
- Coverage gaps: comprobacion.py (32%), maintenance.py (32%), confirmacion.py (38%)
- ISO 17020 modules missing: complaints, non-conformities, impartiality
- `core/views_optimized.py`, `core/zip_optimizer.py`, `core/async_zip_improved.py`: Evaluate if still needed

## Backups

### PostgreSQL to Cloudflare R2
- Daily at 3:00 AM (Colombia) via GitHub Actions
- Script: `scripts/backup_to_s3.py`
- Retention: 180 days

### Soft Delete
- Companies: 180-day retention before permanent deletion
- Command: `python manage.py cleanup_deleted_companies`

## Security
- HTTPS + HSTS in production
- CSP headers, XSS protection
- Session: 8 hours, CSRF: 8 hours
- Custom user model: `core.CustomUser`
- File validation on all uploads
- Rate limiting configured
