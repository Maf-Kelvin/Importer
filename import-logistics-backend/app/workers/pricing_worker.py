# app/workers/pricing_worker.py
from celery import current_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.pricing_service import PricingService
from app.services.scraper_service import ScraperService


@celery_app.task(bind=True)
def fetch_market_prices(self, item_id: int, user_id: int):
    """Fetch market prices for an item from various sources."""
    db = SessionLocal()
    try:
        pricing_service = PricingService(db)
        scraper_service = ScraperService()
        
        # Update task state
        current_task.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 5, 'status': 'Starting market price fetch...'}
        )
        
        # Fetch from different sources
        sources = ['jiji', 'ebay', 'mobile_de', 'autoscout24', 'bazos_cz']
        results = []
        
        for i, source in enumerate(sources):
            current_task.update_state(
                state='PROGRESS',
                meta={'current': i+1, 'total': 5, 'status': f'Fetching from {source}...'}
            )
            
            try:
                prices = scraper_service.scrape_prices(item_id, source)
                if prices:
                    # Save price records
                    for price_data in prices:
                        pricing_service.create_market_price_record(
                            item_id, source, price_data, user_id
                        )
                    results.extend(prices)
            except Exception as e:
                print(f"Error fetching from {source}: {e}")
        
        return {
            'status': 'SUCCESS',
            'results_count': len(results),
            'sources_checked': len(sources)
        }
        
    except Exception as exc:
        return {
            'status': 'FAILURE',
            'error': str(exc)
        }
    finally:
        db.close()


@celery_app.task
def update_item_pricing(item_id: int):
    """Update pricing recommendations for an item."""
    db = SessionLocal()
    try:
        pricing_service = PricingService(db)
        return pricing_service.calculate_recommended_price(item_id)
    except Exception as exc:
        return {'status': 'FAILURE', 'error': str(exc)}
    finally:
        db.close()