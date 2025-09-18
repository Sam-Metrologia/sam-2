# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SAM Metrología is a Django-based metrology management system that handles equipment tracking, maintenance scheduling, and company management for metrology businesses. The system supports multi-tenant companies with equipment limits and subscription plans.

## Development Commands

### Essential Commands
```bash
# Start development server
python manage.py runserver

# Apply database migrations
python manage.py migrate

# Create database migrations after model changes
python manage.py makemigrations

# Create superuser for admin access
python manage.py createsuperuser

# Collect static files (required for production)
python manage.py collectstatic

# Install dependencies
pip install -r requirements.txt

# Start with virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Testing and Quality
```bash
# Run tests
python manage.py test

# Check for issues
python manage.py check

# Create cache table (if using database cache)
python manage.py createcachetable sam_cache_table
```

### Deployment Commands
```bash
# Production deployment (from start.sh)
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn proyecto_c.wsgi:application
```

## Architecture Overview

### Project Structure
- **core/**: Main business logic app containing models, views, and business logic
- **proyecto_c/**: Django project settings and main configuration
- **templates/**: Global templates directory
- **media/**: Local file uploads (development only)
- **logs/**: Application logs with rotation

### Key Models and Domain
- **Empresa**: Company/client management with logo, contact info, and equipment limits
- **CustomUser**: Extended user model with company associations and role management
- **Equipment Management**: Equipment tracking, maintenance scheduling, and documentation
- **Subscription System**: Company-based equipment limits and plan management

### Settings Architecture
Environment-based configuration with automatic switching:
- **Development**: SQLite database, local file storage, debug logging
- **Production**: PostgreSQL database, AWS S3 storage, structured JSON logging
- **Environment Detection**: Uses `RENDER_EXTERNAL_HOSTNAME` to detect production

### Database Configuration
- **Development**: SQLite (`db.sqlite3`)
- **Production**: PostgreSQL via `DATABASE_URL` environment variable
- **Migrations**: Located in `core/migrations/`

### File Storage Strategy
- **Development**: Local filesystem storage in `media/` directory
- **Production**: AWS S3 with server-side encryption and optimized settings
- **Static Files**: WhiteNoise for development, S3 for production

### Caching System
Three-tier caching based on environment:
- **Development**: Local memory cache
- **Production with Redis**: Redis cache with connection pooling
- **Production fallback**: Database cache with table `sam_cache_table`

### Logging Configuration
Structured logging with multiple handlers:
- **Development**: Console output with verbose formatting
- **Production**: JSON-formatted logs with file rotation
- **Log Files**:
  - `logs/sam_info.log`: General application logs
  - `logs/sam_errors.log`: Error logs with extended retention
  - `logs/sam_security.log`: Security-related events

## Environment Variables

### Required for Production
```bash
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://...
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=us-east-2
RENDER_EXTERNAL_HOSTNAME=your-domain.com
```

### Optional Configuration
```bash
DEBUG_VALUE=False
REDIS_URL=redis://...
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_password
ADMIN_EMAIL=admin@yourcompany.com
```

## Security Configuration

### Production Security Features
- HTTPS enforcement with HSTS
- Content Security Policy (CSP) headers
- XSS and content type protection
- Secure cookie settings
- AWS S3 server-side encryption
- Rate limiting configuration in `RATE_LIMIT_CONFIG`

### Authentication System
- Custom user model (`AUTH_USER_MODEL = 'core.CustomUser'`)
- Company-based user associations
- Login redirects to dashboard (`core:dashboard`)
- Session-based authentication with security cookies

## Application-Specific Configuration

### SAM Configuration (`SAM_CONFIG`)
- `DEFAULT_EQUIPMENT_LIMIT`: 5 equipments per company default
- `MAX_EQUIPMENT_LIMIT`: 1000 equipments maximum
- `MAX_FILE_SIZE_MB`: 10MB file upload limit
- `ALLOWED_IMAGE_FORMATS`: jpg, jpeg, png
- `ALLOWED_DOCUMENT_FORMATS`: pdf, xlsx, docx
- `PAGINATION_SIZE`: 25 items per page

### Localization
- **Language**: Spanish Colombia (`es-co`)
- **Timezone**: America/Bogota
- **Date Format**: dd/mm/yyyy
- **Time Format**: 24-hour format

## Development Guidelines

### Model Changes
1. Make model changes in `core/models.py`
2. Run `python manage.py makemigrations`
3. Apply with `python manage.py migrate`
4. Update admin registration in `core/admin.py` if needed

### File Uploads
- Use configured storage backends (auto-switches based on environment)
- Files are validated for type and size in `core/forms.py`
- Images and documents handled separately with different validation rules

### Performance Considerations
- Database connection pooling enabled in production (`CONN_MAX_AGE = 600`)
- Cache configuration with timeout settings
- AWS S3 optimized with connection pooling and retry logic
- Static file compression with WhiteNoise

### Error Handling
- Structured logging captures errors with context
- Email notifications for critical errors in production
- Security events logged separately for monitoring

## Common Development Tasks

### Adding New Equipment Types
1. Update models in `core/models.py`
2. Create and apply migrations
3. Update forms in `core/forms.py`
4. Add validation logic in `core/services.py`

### Template Development
- Global templates in `templates/`
- App-specific templates in `core/templates/`
- Bootstrap 5 with Crispy Forms integration
- Base template inheritance pattern

### PDF Generation
- Uses WeasyPrint for PDF generation
- Templates in `core/templates/` with PDF-specific styling
- Configured for handling Spanish characters and formatting

### AWS S3 Troubleshooting
- Check environment variables are set correctly
- Verify AWS credentials have S3 permissions
- Monitor logs for S3-related errors in `logs/sam_errors.log`
- Test with local storage first by clearing AWS environment variables