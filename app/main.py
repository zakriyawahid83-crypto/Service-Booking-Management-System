from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

from app.routers import (
    auth,
    providers,
    services,
    categories,
    bookings,
    availability,
    payments,
    reviews,
    notifications,
    complaints,
    search,
    admin,
    customers,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Service Booking & Management Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(services.router)
app.include_router(categories.router)
app.include_router(bookings.router)
app.include_router(availability.router)
app.include_router(payments.router)
app.include_router(reviews.router)
app.include_router(notifications.router)
app.include_router(complaints.router)
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(customers.router)


@app.get("/")
def root():
    return {
        "message": "Service Booking API is running"
    }
