
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

# Load environment variables before importing application services.
load_dotenv()

from app.api.products import router as products_router
from app.api.chat import router as chat_router
from app.api.tickets import router as tickets_router
from app.api import knowledge

from app.db.database import Base, engine
from app.models.product import ProductDB
from app.models.ticket import SupportTicketDB
from app.api.auth import router as auth_router
from app.models.conversation import ConversationDB
from app.models.staff import StaffUserDB
from app.api import guest
from app.api.dashboard import router as dashboard_router
from app.models.order import OrderDB
from app.api.orders import router as orders_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="SupportIQ AI",
    description="AI-powered customer support for department stores",
    version="1.0.0",
    lifespan=lifespan,
)


# Allow Angular frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Welcome to SupportIQ AI!",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SupportIQ AI",
    }


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