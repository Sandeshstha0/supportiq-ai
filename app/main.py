
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables before importing application services.
load_dotenv()

# Application routers
from app.api.products import router as products_router
from app.api.chat import router as chat_router
from app.api.tickets import router as tickets_router
from app.api import knowledge
from app.api.auth import router as auth_router
from app.api import guest
from app.api.dashboard import router as dashboard_router
from app.api.orders import router as orders_router
from app.api.customers import router as customers_router
from app.api.conversations import router as conversations_router

# Database and models
from app.db.database import Base, engine
from app.models.product import ProductDB
from app.models.ticket import SupportTicketDB
from app.models.conversation import ConversationDB
from app.models.staff import StaffUserDB
from app.models.order import OrderDB


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="SupportIQ AI",
    description="AI-powered customer support for department stores",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS configuration
# Supports local development and deployed frontend domains.
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "FRONTEND_URLS",
        "http://localhost:4200,http://127.0.0.1:4200",
         "https://supportiq-ai-ten.vercel.app",
        "https://supportiq-du9ldifwt-sandeshstha0s-projects.vercel.app",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to SupportIQ AI!",
        "status": "running",
    }


# Health check endpoint for Render
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SupportIQ AI",
    }


# Register API routers
app.include_router(products_router)
app.include_router(chat_router)
app.include_router(tickets_router)

app.include_router(
    knowledge.router,
    prefix="/api/v1",
)

app.include_router(guest.router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(orders_router)
app.include_router(customers_router)
app.include_router(conversations_router)
