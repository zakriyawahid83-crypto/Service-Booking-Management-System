# Service-Booking-Management-System
FastAPI-based backend for a Service Booking Management System with PostgreSQL, authentication, service management, provider availability, bookings, and REST APIs.

## ✨ Features

### 🔐 Authentication & Authorization

* User registration and login
* JWT-based authentication
* Secure password authentication
* Role-based access control
* Customer and Provider accounts
* Protected API endpoints
* Session/token authentication

### 👤 Customer Features

* Customer profile
* Browse service providers
* Browse service categories
* View available services
* View service details
* Check available booking slots
* Book services
* View bookings
* Manage booking status
* Submit reviews and ratings
* Notifications

### 🏢 Provider Features

* Provider registration
* Provider profile management
* Business information management
* Create services
* Update services
* Delete services
* Service pricing
* Service duration
* Service images
* Category management
* Provider availability
* Working hours
* Break times
* Blocked dates
* Blocked times
* View customer bookings
* Manage bookings
* Earnings information
* Reviews and ratings

### 📅 Booking & Availability

* Date-based availability
* Dynamic time slots
* Service duration-based slots
* Provider working hours
* Break time handling
* Existing booking conflict prevention
* Blocked date handling
* Blocked time handling
* Past date protection
* Same-day past-slot protection

### ⭐ Reviews

* Customer reviews
* Provider ratings
* Service feedback

### 🔔 Notifications

* Booking-related notifications
* Provider/customer notifications
* Notification management

### 💳 Payments

* Payment-related API structure
* Booking payment information
* Payment records

---

# 🛠️ Tech Stack

| Technology | Purpose                      |
| ---------- | ---------------------------- |
| Python     | Backend programming language |
| FastAPI    | REST API framework           |
| PostgreSQL | Relational database          |
| SQLAlchemy | ORM                          |
| Pydantic   | Data validation              |
| JWT        | Authentication               |
| Uvicorn    | ASGI server                  |
| React.js   | Frontend                     |
| Railway    | Backend deployment           |

---

# 📁 Project Structure

```text
backend/
│
├── app/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── database/
│   ├── dependencies/
│   └── main.py
│
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

> The exact structure may vary depending on the current backend implementation.

---

# ⚙️ Local Installation

## 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/service-booking-backend.git
```

Move into the project:

```bash
cd service-booking-backend
```

---

## 2. Create Virtual Environment

Windows:

```bash
python -m venv venv
```

Activate:

```bash
venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🗄️ PostgreSQL Database

The application uses **PostgreSQL** as its database.

Create a PostgreSQL database and configure the connection using an environment variable.

Example:

```env
DATABASE_URL=postgresql://username:password@host:5432/database_name
```

---

# 🔐 Environment Variables

Create a `.env` file in the backend root directory.

Example:

```env
DATABASE_URL=your_database_url
SECRET_KEY=your_secret_key
```

Depending on the application configuration, additional environment variables may be required.

### ⚠️ Security

Never upload `.env` to GitHub.

Add this to `.gitignore`:

```gitignore
.env
.env.*
!.env.example
__pycache__/
*.pyc
venv/
.venv/
```

---

# ▶️ Run Backend Locally

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

If your `main.py` is located somewhere else, use the corresponding module path.

The API will normally be available at:

```text
http://127.0.0.1:8000
```

---

# 📚 API Documentation

FastAPI automatically provides interactive API documentation.

### Swagger UI

```text
http://127.0.0.1:8000/docs
```

### ReDoc

```text
http://127.0.0.1:8000/redoc
```

Swagger can be used to test authentication, providers, services, bookings, availability, and other API endpoints.

---

# 🔗 Main API Modules

The backend provides APIs for:

```text
/auth
/provider
/customer
/services
/categories
/availability
/bookings
/reviews
/notifications
/payments
```

The exact endpoints are available through the Swagger documentation.

---

# 🚂 Railway Deployment

The backend is designed to be deployed on **Railway**.

## 1. Push Backend to GitHub

Initialize Git:

```bash
git init
```

Add files:

```bash
git add .
```

Commit:

```bash
git commit -m "Initial backend"
```

Connect GitHub repository:

```bash
git remote add origin https://github.com/YOUR_USERNAME/service-booking-backend.git
```

Push:

```bash
git branch -M main
git push -u origin main
```

---

## 2. Create Railway Project

1. Open Railway
2. Create a new project
3. Select **Deploy from GitHub Repo**
4. Select this backend repository
5. Railway will start building the application

---

## 3. Configure Environment Variables

Add the required variables in Railway:

```env
DATABASE_URL=your_production_postgresql_url
SECRET_KEY=your_production_secret_key
```

Do **not** upload your local `.env` file.

---

## 4. PostgreSQL on Railway

A PostgreSQL database can be added to the Railway project.

After creating the database, use the PostgreSQL connection URL provided by Railway as:

```env
DATABASE_URL=...
```

The backend uses this URL to connect to the production database.

---

## 5. Start Command

For FastAPI/Uvicorn deployment, the production server should use:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If your FastAPI application is located in another module, update:

```text
app.main:app
```

accordingly.

---

# 🌐 Frontend Integration

The frontend of this project is built with **React.js**.

After deploying the backend, Railway provides a public backend URL such as:

```text
https://your-backend.up.railway.app
```

The React frontend should use this URL instead of the local development URL:

```text
http://127.0.0.1:8000
```

Example:

```javascript
const API_URL = "https://your-backend.up.railway.app";
```

---

# 🔒 CORS

The backend must allow requests from the deployed React frontend.

Example:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

During local development, the frontend URL can also be added.

---

# 🔄 Application Flow

```text
Customer
   │
   ▼
React Frontend
   │
   ▼
FastAPI REST API
   │
   ├── Authentication
   ├── Services
   ├── Categories
   ├── Availability
   ├── Bookings
   ├── Reviews
   ├── Notifications
   └── Payments
   │
   ▼
PostgreSQL
```

Provider flow:

```text
Provider
   │
   ▼
Provider Dashboard
   │
   ├── Profile
   ├── Categories
   ├── Services
   ├── Availability
   ├── Bookings
   ├── Reviews
   └── Earnings
   │
   ▼
FastAPI Backend
   │
   ▼
PostgreSQL
```

---

# 🧪 Testing

API endpoints can be tested using:

* FastAPI Swagger UI
* Postman
* React frontend

Swagger:

```text
/docs
```

---

# 🚀 Production Deployment

Production architecture:

```text
                    ┌──────────────────┐
                    │   React Frontend │
                    │      Vercel      │
                    └────────┬─────────┘
                             │
                             │ REST API
                             ▼
                    ┌──────────────────┐
                    │ FastAPI Backend  │
                    │     Railway      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   PostgreSQL     │
                    │     Database     │
                    └──────────────────┘
```

---

# 🔑 Important Security Notes

* Never commit `.env`
* Never expose database passwords
* Never expose JWT secret keys
* Use HTTPS in production
* Use a strong production `SECRET_KEY`
* Configure CORS for the production frontend
* Keep development and production database credentials separate

---

# 👨‍💻 Author

**Zakirya Wahid**

Software Engineering Intern — CodeCelix, Rawalpindi

### Technologies

* React.js
* FastAPI
* Python
* PostgreSQL
* REST APIs
* SQLAlchemy
* Git & GitHub

---

# 📌 Project Status

🚧 **Active Development**

The project is being developed as a full-stack Service Booking Management System with a React.js frontend, FastAPI backend, and PostgreSQL database.

---

## 📄 License

This project is developed for educational and portfolio purposes.
