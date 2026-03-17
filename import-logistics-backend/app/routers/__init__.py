# app/routers/__init__.py
from fastapi import APIRouter

from app.routers import (
    auth,
    users,
    containers,
    items,
    expenses,
    pricing,
    tracking,
    reports,
    health,
    files,
)

api_router = APIRouter()

api_router.include_router(auth.router,       prefix="/auth",       tags=["Authentication"])
api_router.include_router(users.router,      prefix="/users",      tags=["Users"])
api_router.include_router(containers.router, prefix="/containers", tags=["Containers"])
api_router.include_router(items.router,      prefix="/items",      tags=["Items"])
api_router.include_router(expenses.router,   prefix="/expenses",   tags=["Expenses"])
api_router.include_router(pricing.router,    prefix="/pricing",    tags=["Pricing"])
api_router.include_router(tracking.router,   prefix="/tracking",   tags=["Tracking"])
api_router.include_router(reports.router,    prefix="/reports",    tags=["Reports"])
api_router.include_router(files.router,      prefix="/files",      tags=["Files"])
# /health and /ready are mounted directly on app in main.py (outside rate limiter)