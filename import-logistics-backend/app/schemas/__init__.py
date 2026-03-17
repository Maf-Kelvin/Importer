# app/schemas/__init__.py
# Import order: pricing before item to prevent circular imports.
# item.py uses TYPE_CHECKING for PriceRecordInDB — model_rebuild() resolves it.

from app.schemas.common import (       # noqa: F401
    PaginationParams,
    CursorPaginationParams,
    PagedResponse,
    CursorPagedResponse,
    ResponseMessage,
    ErrorDetail,
    ErrorResponse,
)

from app.schemas.user import (         # noqa: F401
    UserBase, UserCreate, UserAdminCreate,
    UserUpdate, UserAdminUpdate,
    UserInDB, UserPublic,
    Token, TokenRefresh, LogoutRequest, TokenPayload,
)

from app.schemas.pricing import (      # noqa: F401
    PriceRecordBase, PriceRecordCreate, PriceRecordInDB,
    PricingRequest, PricingResponse,
    MarketPrice,
)

from app.schemas.item import (         # noqa: F401
    ItemBase, ItemCreate, ItemUpdate,
    MarkSoldRequest, ItemInDB, ItemWithPricing,
)

from app.schemas.expense import (      # noqa: F401
    ExpenseBase, ExpenseCreate, ExpenseUpdate, ExpenseInDB,
)

from app.schemas.container import (    # noqa: F401
    ContainerBase, ContainerCreate, ContainerUpdate,
    ContainerInDB, ContainerWithItems,
)

from app.schemas.tracking import (     # noqa: F401
    TrackingRecordBase, TrackingRecordInDB,
    NotificationSettingsUpdate, TrackingStatusResponse,
)

from app.schemas.reports import (      # noqa: F401
    ReportFilters, ProfitReportItem,
    ContainerReport, CategoryReport,
    FXImpactReport, DashboardSummary, DemandSnapshot,
)