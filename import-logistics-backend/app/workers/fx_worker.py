# app/workers/fx_worker.py
from app.core.celery_app import celery_app
from app.services.fx_service import FXService
from app.core.config import SUPPORTED_CURRENCIES


@celery_app.task
def update_fx_rates():
    """Update FX rates for all supported currencies."""
    fx_service = FXService()
    
    results = {}
    for currency in SUPPORTED_CURRENCIES:
        if currency != "USD":  # Skip USD as it's the base
            try:
                rate = fx_service.get_fx_rate(currency, "USD")
                results[f"{currency}_USD"] = rate
            except Exception as e:
                results[f"{currency}_USD"] = f"Error: {str(e)}"
    
    return {
        'status': 'SUCCESS',
        'rates_updated': len([r for r in results.values() if isinstance(r, float)]),
        'rates': results
    }
