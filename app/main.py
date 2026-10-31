from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.products import router as products_router
from app.db.database import Base, engine
from app.models.product import ProductDB
from app.api.chat import router as chat_router
from app.models.ticket import SupportTicketDB
from app.api.tickets import router as tickets_router
from app.models.conversation import ConversationDB
from app.api import chat, products, tickets, knowledge

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