# app/services/container_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from app.models.container import Container, AllocationMethod, ContainerType
from app.models.item import Item
from app.models.expense import ContainerExpense
from app.models.user import User, UserRole
from app.schemas.container import ContainerCreate, ContainerUpdate
from app.schemas.item import ItemCreate, ItemUpdate
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.services.fx_service import FXService
from app.services.cost_allocation_service import CostAllocationService
from datetime import datetime


class ContainerService:
    def __init__(self, db: Session):
        self.db = db
        self.fx_service = FXService()
        self.cost_allocation_service = CostAllocationService(db)
    
    def create_container(self, container_data: ContainerCreate, owner_id: int) -> Container:
        """Create a new container."""
        container = Container(
            name=container_data.name,
            container_type=container_data.container_type,
            msc_container_number=container_data.msc_container_number,
            allocation_method=container_data.allocation_method,
            notes=container_data.notes,
            owner_id=owner_id
        )
        
        self.db.add(container)
        self.db.commit()
        self.db.refresh(container)
        return container
    
    def get_containers(self, skip: int = 0, limit: int = 50, **filters) -> Dict[str, Any]:
        """Get containers with filtering and pagination."""
        query = self.db.query(Container)
        
        # Apply filters
        if filters.get('owner_id'):
            query = query.filter(Container.owner_id == filters['owner_id'])
        
        if filters.get('container_type'):
            query = query.filter(Container.container_type == filters['container_type'])
        
        if filters.get('is_shipped') is not None:
            query = query.filter(Container.is_shipped == filters['is_shipped'])
        
        # Role-based filtering
        current_user = filters.get('current_user')
        if current_user and current_user.role == UserRole.CLERK:
            query = query.filter(Container.owner_id == current_user.id)
        
        total = query.count()
        containers = query.options(joinedload(Container.owner)).offset(skip).limit(limit).all()
        
        return {
            'items': containers,
            'total': total,
            'page': (skip // limit) + 1,
            'per_page': limit,
            'pages': (total + limit - 1) // limit
        }
    
    def get_container_by_id(self, container_id: int, current_user: User) -> Optional[Container]:
        """Get container by ID with permission check."""
        query = self.db.query(Container).options(
            joinedload(Container.items),
            joinedload(Container.expenses)
        ).filter(Container.id == container_id)
        
        # Role-based access control
        if current_user.role == UserRole.CLERK:
            query = query.filter(Container.owner_id == current_user.id)
        
        return query.first()
    
    def update_container(self, container_id: int, container_update: ContainerUpdate, current_user: User) -> Optional[Container]:
        """Update container."""
        container = self.get_container_by_id(container_id, current_user)
        if not container:
            return None
        
        # Check if user can edit this container
        if current_user.role == UserRole.CLERK and container.owner_id != current_user.id:
            return None
        
        update_data = container_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(container, field, value)
        
        self.db.commit()
        self.db.refresh(container)
        return container
    
    def seal_container(self, container_id: int, current_user: User) -> Optional[Container]:
        """Seal container (prevent adding more items)."""
        container = self.get_container_by_id(container_id, current_user)
        if not container:
            return None
        
        container.is_sealed = True
        self.db.commit()
        self.db.refresh(container)
        return container
    
    def allocate_costs(self, container_id: int, allocation_method: Optional[str], current_user: User) -> Optional[Dict]:
        """Allocate container costs to items."""
        container = self.get_container_by_id(container_id, current_user)
        if not container:
            return None
        
        return self.cost_allocation_service.allocate_container_costs(container_id, allocation_method)
    
    # Item methods
    def create_item(self, item_data: ItemCreate, current_user: User) -> Optional[Item]:
        """Create item in container."""
        container = self.get_container_by_id(item_data.container_id, current_user)
        if not container or container.is_sealed:
            return None
        
        # Convert purchase price to USD
        fx_rate = self.fx_service.get_fx_rate(item_data.purchase_currency, "USD")
        purchase_price_usd = item_data.purchase_price * fx_rate
        
        item = Item(
            container_id=item_data.container_id,
            name=item_data.name,
            description=item_data.description,
            category=item_data.category,
            condition=item_data.condition,
            purchase_price=item_data.purchase_price,
            purchase_currency=item_data.purchase_currency,
            purchase_date=item_data.purchase_date,
            fx_rate_to_usd=fx_rate,
            purchase_price_usd=purchase_price_usd,
            weight=item_data.weight,
            volume=item_data.volume
        )
        
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
    
    def create_expense(self, expense_data: ExpenseCreate, current_user: User) -> Optional[ContainerExpense]:
        """Create container expense."""
        container = self.get_container_by_id(expense_data.container_id, current_user)
        if not container:
            return None
        
        # Convert amount to USD
        fx_rate = self.fx_service.get_fx_rate(expense_data.currency, "USD")
        amount_usd = expense_data.amount * fx_rate
        
        expense = ContainerExpense(
            container_id=expense_data.container_id,
            expense_type=expense_data.expense_type,
            amount=expense_data.amount,
            currency=expense_data.currency,
            description=expense_data.description,
            fx_rate_to_usd=fx_rate,
            amount_usd=amount_usd
        )
        
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense