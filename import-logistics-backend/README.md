# Import Profit & Logistics Intelligence System - Backend API

A comprehensive enterprise-grade backend system for managing import containers, tracking shipments, calculating costs, and optimizing pricing strategies.

## 🚀 Features

### Core Functionality
- **Container Management**: Handle 20ft and 40ft containers with complete expense tracking
- **Item Management**: Track mixed goods with purchase details, weight, and conditions
- **Cost Allocation**: Automatic cost distribution using weight-based or value-based methods
- **Multi-Currency Support**: Handle USD, EUR, CZK, and NGN with real-time FX rates

### Pricing Intelligence
- **Cost-Based Pricing**: Calculate recommended prices with configurable margins
- **Market Price Scraping**: Fetch prices from Jiji, eBay, Mobile.de, AutoScout24, Bazos.cz
- **Historical Pricing**: Track last sold prices and price history

### Tracking & Notifications
- **MSC Container Tracking**: Real-time shipment status updates
- **Automated Notifications**: Email alerts for status changes
- **Periodic Updates**: Configurable tracking intervals (3, 5, or 7 days)

### Enterprise Features
- **Role-Based Access Control**: Admin, Manager, Clerk, Viewer roles
- **Multi-User Support**: Team collaboration with permission management
- **Comprehensive Reporting**: Profit analysis, FX impact, sales history
- **Offline-Friendly**: Mobile sync capabilities
- **Background Processing**: Async tasks for pricing and tracking

## 🏗️ Architecture

```
FastAPI + PostgreSQL + Redis + Celery
├── API Layer (FastAPI)
├── Business Logic (Services)
├── Data Layer (SQLAlchemy + PostgreSQL)
├── Background Tasks (Celery + Redis)
├── External APIs (MSC, FX, Scraping)
└── Authentication (JWT + RBAC)
```

## 📁 Project Structure

```
import-logistics-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Configuration and settings
│   │   ├── database.py                  # Database connection setup
│   │   ├── security.py                  # JWT and password handling
│   │   ├── celery_app.py               # Celery configuration
│   │   └── dependencies.py             # FastAPI dependencies
│   ├── models/                          # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── user.py                     # User model with roles
│   │   ├── container.py                # Container model
│   │   ├── item.py                     # Item model
│   │   ├── expense.py                  # Container expense model
│   │   ├── pricing.py                  # Price records model
│   │   ├── tracking.py                 # Tracking records model
│   │   └── base.py                     # Base model with timestamps
│   ├── schemas/                         # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── user.py                     # User schemas
│   │   ├── container.py                # Container schemas
│   │   ├── item.py                     # Item schemas
│   │   ├── expense.py                  # Expense schemas
│   │   ├── pricing.py                  # Pricing schemas
│   │   ├── tracking.py                 # Tracking schemas
│   │   └── common.py                   # Common schemas (pagination, etc.)
│   ├── routers/                        # API route handlers
│   │   ├── __init__.py                 # Main API router
│   │   ├── deps.py                     # API dependencies & auth
│   │   ├── auth.py                     # Authentication endpoints
│   │   ├── users.py                    # User management endpoints
│   │   ├── containers.py               # Container CRUD endpoints
│   │   ├── items.py                    # Item management endpoints
│   │   ├── expenses.py                 # Expense management endpoints
│   │   ├── pricing.py                  # Pricing engine endpoints
│   │   ├── tracking.py                 # Tracking endpoints
│   │   └── reports.py                  # Reporting endpoints
│   ├── services/                       # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py             # Authentication business logic
│   │   ├── container_service.py        # Container operations
│   │   ├── pricing_service.py          # Pricing calculations
│   │   ├── tracking_service.py         # MSC API integration
│   │   ├── cost_allocation_service.py  # Cost allocation algorithms
│   │   ├── fx_service.py               # Foreign exchange handling
│   │   ├── notification_service.py     # Email notifications
│   │   └── scraper_service.py          # Web scraping for prices
│   ├── workers/                        # Celery background workers
│   │   ├── __init__.py
│   │   ├── pricing_worker.py           # Price scraping tasks
│   │   ├── tracking_worker.py          # Container tracking tasks
│   │   ├── fx_worker.py                # FX rate update tasks
│   │   └── notification_worker.py      # Email notification tasks
│   ├── utils/                          # Utility functions
│   │   ├── __init__.py
│   │   ├── helpers.py                  # General helper functions
│   │   ├── exceptions.py               # Custom exceptions
│   │   ├── validators.py               # Data validators
│   │   └── constants.py                # Application constants
│   └── tests/                          # Test suite
│       ├── __init__.py
│       ├── conftest.py                 # Test configuration
│       ├── test_auth.py                # Authentication tests
│       ├── test_containers.py          # Container tests
│       ├── test_items.py               # Item tests
│       ├── test_pricing.py             # Pricing tests
│       └── test_tracking.py            # Tracking tests
├── alembic/                            # Database migrations
│   ├── versions/                       # Migration files
│   ├── env.py                         # Alembic environment
│   ├── script.py.mako                 # Migration template
│   └── alembic.ini                    # Alembic configuration
├── docker/                            # Docker configuration
│   ├── Dockerfile                     # Application container
│   ├── docker-compose.yml            # Development environment
│   ├── docker-compose.prod.yml       # Production environment
│   └── redis.conf                     # Redis configuration
├── scripts/                           # Utility scripts
│   ├── init_db.py                     # Database initialization
│   ├── create_admin.py                # Create admin users
│   └── seed_data.py                   # Sample data seeding
├── .env.example                       # Environment variables template
├── .env                              # Environment variables (local)
├── .gitignore                        # Git ignore rules
├── requirements.txt                  # Python dependencies
├── requirements-dev.txt              # Development dependencies
├── pyproject.toml                    # Project configuration
└── README.md                         # This file
```

### 📂 Key Directory Explanations

**`app/core/`** - Core application configuration
- Database connections, security, Celery setup, and global dependencies

**`app/models/`** - Database layer
- SQLAlchemy ORM models defining database structure and relationships

**`app/schemas/`** - API validation layer  
- Pydantic models for request/response validation and serialization

**`app/routers/`** - API routing layer
- FastAPI routers organized by feature with proper authentication and permissions

**`app/services/`** - Business logic layer
- Core business operations, external API integrations, and complex calculations

**`app/workers/`** - Background processing
- Celery tasks for async operations like price scraping and tracking updates

**`alembic/`** - Database migrations
- Version-controlled database schema changes and data migrations

**`docker/`** - Containerization
- Docker setup for development and production deployment

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache & Queue**: Redis
- **Background Tasks**: Celery
- **Authentication**: JWT with Role-Based Access Control
- **Migration**: Alembic
- **Containerization**: Docker & Docker Compose
- **API Documentation**: OpenAPI/Swagger

## 📦 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL (if running locally)
- Redis (if running locally)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd import-logistics-backend

# Copy environment file
cp .env.example .env

# Edit .env file with your configuration
nano .env
```

### 2. Docker Setup (Recommended)
```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Initialize database
docker-compose -f docker/docker-compose.yml exec web python scripts/init_db.py

# Check logs
docker-compose -f docker/docker-compose.yml logs -f web
```

### 3. Local Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup database
python scripts/init_db.py

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000

# In separate terminals:
celery -A app.core.celery_app worker --loglevel=info
celery -A app.core.celery_app beat --loglevel=info
```

### 4. Access the Application
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Celery Monitoring**: http://localhost:5555 (Flower)

### 5. Default Login
```
Email: admin@example.com
Username: admin
Password: changethis
```

## 🔧 Configuration

### Environment Variables
Key configuration options in `.env`:

```bash
# API Configuration
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=10080
PROJECT_NAME=Import Profit & Logistics Intelligence System

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/import_logistics

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# External APIs
MSC_API_KEY=your_msc_api_key_here
EXCHANGERATE_API_KEY=your_exchange_rate_api_key_here

# Email Configuration
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_password

# Pricing
DEFAULT_PROFIT_MARGIN=0.20
SCRAPING_ENABLED=true
```

### Database Migration
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## 📚 API Usage

### Authentication
```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=changethis"

# Use token in subsequent requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/containers/"
```

### Key Endpoints

#### Containers
- `POST /api/v1/containers/` - Create container
- `GET /api/v1/containers/` - List containers
- `GET /api/v1/containers/{id}` - Get container details
- `POST /api/v1/containers/{id}/seal` - Seal container
- `POST /api/v1/containers/{id}/allocate-costs` - Allocate costs

#### Items
- `POST /api/v1/items/` - Add item to container
- `GET /api/v1/items/` - List items
- `PUT /api/v1/items/{id}` - Update item
- `POST /api/v1/items/{id}/mark-sold` - Mark as sold

#### Pricing
- `POST /api/v1/pricing/generate/{item_id}` - Generate pricing
- `POST /api/v1/pricing/refresh-market/{item_id}` - Refresh market prices
- `GET /api/v1/pricing/item/{item_id}` - Get price history

#### Tracking
- `POST /api/v1/tracking/{container_id}/update` - Update tracking
- `GET /api/v1/tracking/{container_id}/history` - Get tracking history
- `GET /api/v1/tracking/{container_id}/status` - Current status

#### Reports
- `GET /api/v1/reports/profit/items` - Item profit report
- `GET /api/v1/reports/profit/containers` - Container profit report
- `GET /api/v1/reports/profit/categories` - Category profit report

## 🔐 User Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access, user management |
| **Manager** | All containers, reports, user oversight |
| **Clerk** | Own containers only, basic operations |
| **Viewer** | Read-only access to assigned data |

## 🔄 Background Tasks

### Automated Processes
- **FX Rate Updates**: Every hour
- **Container Tracking**: Every hour  
- **Price Scraping**: On-demand and scheduled
- **Email Notifications**: Real-time triggers

### Manual Triggers
```bash
# Trigger specific tasks
celery -A app.core.celery_app call app.workers.fx_worker.update_fx_rates
celery -A app.core.celery_app call app.workers.tracking_worker.update_all_tracking
```

## 📊 Database Schema

### Core Tables
- **users** - User accounts and roles
- **containers** - Container information
- **items** - Items within containers
- **container_expenses** - Container-level costs
- **price_records** - Pricing history
- **tracking_records** - Shipment tracking data

### Relationships
```
users (1:N) containers (1:N) items (1:N) price_records
containers (1:N) container_expenses
containers (1:N) tracking_records
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/tests/test_containers.py

# Run with verbose output
pytest -v
```

## 🚀 Production Deployment

### Docker Production Setup
```bash
# Use production compose file
docker-compose -f docker/docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker/docker-compose.prod.yml up -d --scale celery_worker=4
```

### Performance Optimizations
- Enable PostgreSQL connection pooling
- Configure Redis persistence
- Set up proper logging
- Configure Nginx reverse proxy
- Enable HTTPS/SSL
- Set up monitoring (Prometheus/Grafana)

### Security Checklist
- [ ] Change default SECRET_KEY
- [ ] Update default admin credentials
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable PostgreSQL SSL
- [ ] Configure Redis AUTH
- [ ] Set up backup strategies
- [ ] Enable audit logging

## 📝 API Examples

### Create Container Flow
```python
# 1. Create container
container_data = {
    "name": "CONT-2024-001",
    "container_type": "40ft",
    "msc_container_number": "MSCU123456789",
    "allocation_method": "weight_based"
}

# 2. Add expenses
expenses = [
    {"expense_type": "loading_fee", "amount": 500, "currency": "USD"},
    {"expense_type": "shipping_fee", "amount": 2000, "currency": "USD"},
    {"expense_type": "clearing_fee", "amount": 800, "currency": "USD"}
]

# 3. Add items
items = [
    {
        "name": "Samsung 55\" TV",
        "category": "electronics",
        "condition": "new",
        "purchase_price": 800,
        "purchase_currency": "USD",
        "weight": 25.5
    }
]

# 4. Allocate costs
# POST /api/v1/containers/{id}/allocate-costs

# 5. Generate pricing
# POST /api/v1/pricing/generate/{item_id}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests and linting
6. Submit a pull request

### Code Style
```bash
# Format code
black app/
isort app/

# Check linting
flake8 app/
```

## 📞 Support

- **Documentation**: See `/docs` endpoint when running
- **Issues**: Create GitHub issues for bugs
- **Features**: Submit feature requests via GitHub
- **Email**: support@yourcompany.com

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🔧 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check PostgreSQL status
docker-compose -f docker/docker-compose.yml ps db

# View database logs
docker-compose -f docker/docker-compose.yml logs db
```

**Celery Worker Issues**
```bash
# Check Redis connection
redis-cli -u redis://localhost:6379 ping

# Monitor Celery tasks
celery -A app.core.celery_app inspect active
```

**Migration Problems**
```bash
# Reset migrations (CAUTION: Data loss)
alembic downgrade base
alembic upgrade head

# Or stamp current version
alembic stamp head
```

**Permission Errors**
```bash
# Check user roles
python scripts/create_admin.py user@example.com admin password First Last
```

### Performance Tuning

**Database Optimization**
```sql
-- Add indexes for common queries
CREATE INDEX idx_items_category ON items(category);
CREATE INDEX idx_containers_owner ON containers(owner_id);
CREATE INDEX idx_tracking_container ON tracking_records(container_id);
```

**Redis Configuration**
```bash
# Monitor Redis memory
redis-cli info memory

# Check slow queries
redis-cli slowlog get 10
```

This comprehensive backend system provides a solid foundation for your Import Profit & Logistics Intelligence System. All components are production-ready with proper error handling, security measures, and scalability considerations.