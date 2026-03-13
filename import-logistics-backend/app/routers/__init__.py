# app/routers/__init__.py
from fastapi import APIRouter
from app.routers import auth, users, containers, items, expenses, pricing, tracking, reports

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(containers.router, prefix="/containers", tags=["containers"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"])
api_router.include_router(tracking.router, prefix="/tracking", tags=["tracking"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

