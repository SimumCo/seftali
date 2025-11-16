# Production & Distribution Network Management System

## Overview

This is a Turkish-language production and distribution network management system built for enterprise use. The application manages the complete lifecycle of manufacturing operations, inventory tracking, and logistics coordination across multiple facilities and warehouses. It provides role-based access control with different user types (operator, manager, admin) and comprehensive tracking of production orders, shipments, and inventory levels.

The system is designed to handle complex workflows including production planning, warehouse management, distribution logistics, and real-time inventory monitoring with alerts for low-stock situations.

## User Preferences

Preferred communication style: Simple, everyday language.

## Application Status

**Current State:** Production-ready with full authentication, 4-module functionality, and e2e tested.

**Login Credentials:**
- Username: `admin`
- Password: `admin123`
- Role: Admin (full access to all modules)

**Session Management:**
- 7-day session expiration
- HTTP-only cookies for security
- Session persistence via PostgreSQL store

**Recent Changes (November 16, 2025):**
- Added relational data loading to backend (production orders, shipments, inventory now include product/facility/warehouse details)
- Fixed ProtectedRoute navigation using useEffect to prevent render-time navigation warnings
- Added credentials: "include" to all authentication requests
- Validated full application flow with e2e tests covering login, dashboard, production, distribution, inventory, and logout
- All tests passing successfully

## System Architecture

### Frontend Architecture

**Technology Stack:**
- React with TypeScript for type safety
- Vite as build tool and development server
- Wouter for client-side routing (lightweight alternative to React Router)
- TanStack Query (React Query) for server state management and caching

**UI Framework:**
- shadcn/ui component library (Radix UI primitives)
- Tailwind CSS for styling with custom design tokens
- IBM Carbon Design System principles adapted for data-heavy enterprise applications
- IBM Plex Sans and IBM Plex Mono fonts for typography
- Dark mode support with theme toggle

**Design Decisions:**
- Component-based architecture with reusable UI primitives
- Custom design system extending shadcn/ui with Carbon Design System principles
- Optimized for dense information displays (tables, dashboards, forms)
- Responsive grid layouts with mobile-first approach
- Path aliases (@/, @shared/, @assets/) for clean imports

### Backend Architecture

**Server Framework:**
- Express.js with TypeScript
- Session-based authentication using express-session
- RESTful API architecture with /api/* endpoints

**Authentication & Authorization:**
- bcryptjs for password hashing
- Session cookies (HTTP-only, secure in production)
- Role-based access control (operator, manager, admin roles)
- 7-day session expiration

**API Structure:**
- `/api/auth/*` - Authentication endpoints (login, register, me)
- `/api/production/orders` - Production order management
- `/api/shipments` - Distribution and logistics
- `/api/inventory` - Warehouse inventory tracking
- `/api/dashboard/stats` - Aggregated metrics and KPIs
- `/api/facilities`, `/api/products`, `/api/warehouses` - Master data endpoints

**Data Layer:**
- Storage abstraction pattern (IStorage interface) for database operations
- Centralized database queries through storage module
- Type-safe database access with Drizzle ORM

### Database Architecture

**ORM & Tooling:**
- Drizzle ORM for type-safe database queries
- PostgreSQL as primary database (via Neon serverless)
- WebSocket connections for serverless PostgreSQL
- Schema-first approach with shared TypeScript types

**Schema Design:**
- `users` - User accounts with role-based permissions
- `facilities` - Production facilities (factories, warehouses, distribution centers)
- `products` - Product catalog with SKU and pricing
- `production_orders` - Manufacturing orders with status tracking
- `warehouses` - Storage locations with capacity limits
- `inventory` - Stock levels per product/warehouse with min/max thresholds
- `shipments` - Distribution logistics with delivery tracking

**Key Features:**
- Enum types for status tracking (order_status, shipment_status, priority)
- Auto-incrementing identity columns for primary keys
- Timestamp tracking (createdAt, updatedAt fields)
- Foreign key relationships for data integrity
- Decimal precision for monetary values

**Data Validation:**
- Zod schemas generated from Drizzle schemas (drizzle-zod)
- Client and server-side validation using same schemas
- Type safety across full stack with shared schema definitions

### Development & Build

**Development Environment:**
- Hot module replacement (HMR) with Vite
- Middleware mode for Vite integration with Express
- Replit-specific plugins for error overlay and dev tools
- TypeScript strict mode enabled

**Build Process:**
- Client build: Vite bundles React app to dist/public
- Server build: esbuild bundles Express server to dist/
- Separate build outputs for frontend and backend
- ESM module format throughout

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string (required)
- `SESSION_SECRET` - Session encryption key
- `NODE_ENV` - Environment flag (development/production)

## External Dependencies

### Database
- **Neon PostgreSQL** - Serverless PostgreSQL database with WebSocket support
- Connection pooling via @neondatabase/serverless

### Authentication
- **bcryptjs** - Password hashing (10 rounds)
- **express-session** - Server-side session management
- **connect-pg-simple** - PostgreSQL session store

### UI Components
- **Radix UI** - Comprehensive set of accessible UI primitives (20+ components)
- **shadcn/ui** - Pre-built component patterns on top of Radix
- **Lucide React** - Icon library
- **class-variance-authority** - Variant-based component styling
- **tailwind-merge** & **clsx** - Conditional class name utilities

### Forms & Validation
- **react-hook-form** - Form state management
- **@hookform/resolvers** - Validation resolver integration
- **zod** - Schema validation library

### State Management
- **@tanstack/react-query** - Server state caching and synchronization
- Infinite stale time for cached data
- Optimistic updates disabled by default

### Fonts
- **IBM Plex Sans** - Primary UI font (via Google Fonts CDN)
- **IBM Plex Mono** - Monospace font for numeric data display

### Development Tools
- **Replit plugins** - Runtime error modal, cartographer, dev banner
- **TypeScript** - Type checking and code intelligence
- **Drizzle Kit** - Database migration tooling