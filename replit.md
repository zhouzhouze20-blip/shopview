# 百货柜位管理系统 (Department Store Counter Management System)

## Overview

This is a comprehensive full-stack web application for department store counter management across multiple locations. The system provides complete lifecycle management for retail counters, from tenant prospecting to contract management and financial operations.

**Target Locations:**
1. 常州购物中心 (Changzhou Shopping Center) - Store Code: CZ001
2. 常州新世纪 (Changzhou New Century) - Store Code: CZ002
3. Additional stores as needed

**Current Implementation:** The system has been fully migrated from Node.js to **Python/FastAPI** with complete Docker deployment configuration. 

### Core Modules:
1. **可视化驾驶舱 (Dashboard)** - KPI monitoring and management overview
2. **铺位资源管理 (Space Asset Management)** - Physical space digitization and management
3. **品牌/商户管理 (Tenant & Brand Management)** - Business partner information management
4. **合同管理 (Contract Management)** - Complete contract lifecycle from LOI to renewal
5. **财务管理 (Financial Management)** - Billing and revenue management
6. **系统管理 (System Administration)** - User, role and permission management

The current floor plan visualization is one component of the larger Space Asset Management module.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Python Backend Architecture (Primary Implementation)
- **Framework**: FastAPI with Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **API Design**: RESTful API with automatic OpenAPI documentation
- **Authentication**: JWT tokens with Python-JOSE
- **Data Validation**: Pydantic models with automatic validation
- **Migration**: Alembic for database schema management
- **Development**: Uvicorn ASGI server with hot reload
- **Deployment**: Docker containerization with nginx reverse proxy

### Legacy Node.js Architecture (Available)
- **Framework**: Express.js with TypeScript
- **UI Library**: Shadcn/ui components built on Radix UI primitives
- **Styling**: Tailwind CSS with CSS variables for theming
- **State Management**: TanStack Query (React Query) for server state management
- **Routing**: Wouter for client-side routing
- **Build Tool**: Vite with React plugin
- **Data Layer**: Drizzle ORM for database interactions

### Database Design
- **ORM**: Drizzle ORM with PostgreSQL dialect
- **Schema**: 
  - **Rooms**: Store room details, position, dimensions, tenant info, and financial data
  - **Floor Plans**: Manage multiple floor plan versions with active status
  - **Activities**: Track system activities and changes
  - **Users**: User management (basic structure in place)
- **Migrations**: Automated migration system with Drizzle Kit
- **Validation**: Zod schemas for type-safe data validation

### Key Features
- **Interactive Floor Plan**: SVG-based room visualization with zoom controls and color-coded status indicators
- **Multi-view Modes**: Revenue view, occupancy view, and lease expiry view
- **Real-time Search**: Filter rooms by number, name, or tenant
- **Analytics Dashboard**: Statistics tracking for occupancy rates and revenue metrics
- **Activity Logging**: Track system changes and user interactions
- **Responsive Design**: Mobile-optimized interface with touch-friendly controls

### Data Flow
1. Frontend components use TanStack Query for API calls
2. Express routes handle HTTP requests and validate input with Zod schemas
3. Storage layer abstracts data operations
4. Real-time updates through query invalidation
5. Error boundaries provide graceful error handling

## External Dependencies

### Core Framework Dependencies
- **@neondatabase/serverless**: Neon PostgreSQL database driver for serverless environments
- **drizzle-orm**: Type-safe ORM for database operations
- **express**: Web application framework for the backend API
- **react**: Frontend UI library
- **@tanstack/react-query**: Server state management and caching

### UI and Styling
- **@radix-ui/***: Comprehensive set of accessible UI primitives (dialog, dropdown, toast, etc.)
- **tailwindcss**: Utility-first CSS framework
- **class-variance-authority**: Utility for creating variant-based component APIs
- **lucide-react**: Icon library with React components

### Development and Build Tools
- **vite**: Fast build tool and development server
- **typescript**: Type checking and enhanced development experience
- **drizzle-kit**: Database migrations and schema management
- **esbuild**: Fast JavaScript bundler for production builds

### Validation and Forms
- **zod**: Runtime type validation and schema definition
- **react-hook-form**: Performant form library with minimal re-renders
- **@hookform/resolvers**: Zod integration for form validation

### Utilities
- **date-fns**: Date manipulation and formatting
- **clsx**: Utility for constructing className strings conditionally
- **wouter**: Lightweight router for React applications
- **nanoid**: URL-safe unique string ID generator

The application is configured to use Neon Database (PostgreSQL) in production but includes flexible storage interfaces that can accommodate different database providers.

## Python System Features

### Core API Modules
1. **门店管理 (Store Management)**
   - Store information and configuration
   - Manager contact details
   - Store-specific settings

2. **柜位管理 (Counter Management)**
   - Physical space digitization
   - Counter status tracking (occupied/vacant)
   - Rental rates and area calculations

3. **租户管理 (Tenant Management)**
   - Company and contact information
   - Business category classification
   - Tenant status and history

4. **仪表板 (Dashboard)**
   - Real-time KPI monitoring
   - Occupancy rate statistics
   - Revenue and billing summaries

### Test Data Configuration
- **Store 1**: 常州购物中心 (CZ001) - Central Business District location
- **Store 2**: 常州新世纪 (CZ002) - New Century Commercial Plaza
- **Sample Tenants**: Technology and Fashion retailers
- **Sample Counters**: Various sizes and rental rates

## Docker Deployment Configuration

The system includes complete Python/FastAPI Docker deployment configuration:

### Python Docker Files
- **Dockerfile.python**: Python 3.11-slim base with FastAPI
- **docker-compose.python.yml**: Complete orchestration with PostgreSQL and Nginx
- **nginx-python.conf**: Reverse proxy configuration for Python backend
- **build-python.sh**: Automated build and deployment script
- **python_requirements.txt**: Python dependencies

### Services Architecture
1. **PostgreSQL Database** (postgres:15-alpine)
   - Port 15433 (custom to avoid conflicts)
   - Counter management schema initialization
   - Health checks and persistent storage

2. **Python FastAPI Application** (Custom build)
   - Port 18001 for direct API access
   - Automatic OpenAPI documentation at `/docs`
   - Health check endpoint at `/api/health`
   - JWT authentication ready

3. **Nginx Reverse Proxy** (nginx:alpine)
   - Port 18081 for HTTP, 18444 for HTTPS
   - Proxy to Python backend
   - Security headers and compression

### Deployment Features
- **Custom Ports**: Configured to avoid server conflicts (18001, 15433, 18081, 18444)
- **Documentation**: Auto-generated API docs via FastAPI
- **Testing**: Built-in test application for development
- **Security**: JWT authentication, non-root containers
- **Monitoring**: Health checks and logging

### Quick Deployment
```bash
# Python version deployment
./build-python.sh

# Manual deployment
docker-compose -f docker-compose.python.yml up -d

# Test the API
curl http://localhost:18001/api/health
```

### API Access Points
- **API Documentation**: http://localhost:18001/docs
- **Main API**: http://localhost:18001
- **Nginx Proxy**: http://localhost:18081
- **Database**: localhost:15433