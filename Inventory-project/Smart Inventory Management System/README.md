# Smart Inventory Management System

Enterprise-grade microservices inventory platform built with **FastAPI** + **React**.

---

## Phase 1 Services

| Service | Port | Description |
|---|---|---|
| API Gateway | 8000 | Central entry point, JWT validation, request routing |
| Auth Service | 8001 | Register, Login, JWT, Refresh Tokens, Roles |
| Inventory Service | 8002 | Product CRUD, stock management, low-stock detection |
| AI Service | 8003 | Insights, demand prediction, reorder suggestions, NL query |
| React Frontend | 5173 | Modern Vite + Tailwind UI |

---

## Tech Stack

### Backend
- **FastAPI** + **Uvicorn** — each service is an independent app
- **SQLAlchemy ORM** + **Alembic** migrations
- **MySQL** database
- **JWT** authentication with refresh tokens
- **bcrypt** password hashing
- **httpx** for inter-service communication

### AI
- **Scikit-learn** — demand prediction model
- **Pandas** + **NumPy** — data processing
- Rule-based NL query parser (Phase 1)

### Frontend
- **React 18** + **Vite**
- **Tailwind CSS v3**
- **React Router DOM v6**
- **Axios** + **TanStack React Query**
- **React Hook Form**
- **Chart.js** + **react-chartjs-2**

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MySQL 8.0+

### 1. Install dependencies and configure environment files

From the project root, create a virtual environment and install the Python dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r auth-service\requirements.txt -r inventory-service\requirements.txt -r ai-service\requirements.txt -r api-gateway\requirements.txt
```

Create local environment files from the templates:

```powershell
Copy-Item auth-service\.env.example auth-service\.env
Copy-Item inventory-service\.env.example inventory-service\.env
Copy-Item ai-service\.env.example ai-service\.env
Copy-Item api-gateway\.env.example api-gateway\.env
```

Set each database password and replace the JWT placeholder with the same randomly generated secret in Auth, Inventory, AI, and Gateway settings. Set local bootstrap passwords before the first Auth Service startup. The Auth Service uses these variables to create missing local bootstrap users:

- `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`
- `BOOTSTRAP_MANAGER_EMAIL` and `BOOTSTRAP_MANAGER_PASSWORD`

Set both variables for an account together. Passwords are hashed with the normal Auth Service password hasher. Startup creates an account only if its email is not already present; it never resets an existing account's password or role. Keep `.env` files private and out of source control. Install frontend dependencies once with `Set-Location .\frontend; npm install`.

Create the two MySQL databases before running migrations:

```sql
CREATE DATABASE smart_inventory_auth;
CREATE DATABASE smart_inventory_products;
```

### 2. Start the services on Windows

Run each block in a separate PowerShell terminal from the project root. The commands use the project's `.venv` and load service settings from that service's `.env`.

**Auth Service** (runs migrations before startup):

```powershell
Set-Location .\auth-service
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Inventory Service** (runs migrations before startup):

```powershell
Set-Location .\inventory-service
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

**AI Service:**

```powershell
Set-Location .\ai-service
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

**API Gateway:**

```powershell
Set-Location .\api-gateway
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**

```powershell
Set-Location .\frontend
npm install
npm run dev
```

The Auth Service provisions missing Admin and Manager accounts at startup when their bootstrap email/password environment variables are configured. Public registration creates Employee accounts; additional roles are assigned by an administrator in the app.

---

## Architecture

```
React Frontend (5173)
        ↓
API Gateway (8000)  ← JWT validation + routing
        ↓
 ┌──────┼──────┐
Auth  Inventory  AI
(8001) (8002)  (8003)
        ↓
     MySQL DB
```

---

## Folder Structure

```
smart-inventory/
├── api-gateway/
├── auth-service/
├── inventory-service/
├── ai-service/
├── frontend/
├── shared/
├── docker/
├── docs/
└── README.md
```

---

## API Documentation

Each service exposes Swagger UI:
- Gateway: http://localhost:8000/docs
- Auth: http://localhost:8001/docs
- Inventory: http://localhost:8002/docs
- AI: http://localhost:8003/docs

---

## Roles & Permissions

| Role | Account provisioning | Products | User management | AI |
|---|---|---|---|---|
| Admin | Local bootstrap or admin-created | Full CRUD | Full | ✓ |
| Manager | Admin-created | Read and update | ✗ | ✓ |
| Employee | Public registration | Read only | ✗ | ✓ |

---

## Future Phases (Planned)

- Phase 2: Supplier Service, Purchase Order Service
- Phase 3: Sales Service (real demand data)
- Phase 4: Notification Service (RabbitMQ/Kafka)
- Phase 5: Reports & Analytics Service
- Phase 6: Docker Compose + Kubernetes deployment
+