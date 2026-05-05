from fastapi import APIRouter
from .customer_routes import router as customer_router
from .campaigns import router as sales_campaigns_router
from .customers import router as sales_customers_router
from .deliveries import router as sales_deliveries_router
from .orders import router as sales_orders_router
from .sales_routes import router as sales_router
from .smart_orders import router as smart_orders_router
from .stock import router as stock_router
from .admin_routes import router as admin_router
from .route_map import router as route_map_router

router = APIRouter(prefix="/seftali", tags=["Seftali"])
router.include_router(customer_router)
router.include_router(sales_campaigns_router)
router.include_router(sales_customers_router)
router.include_router(sales_deliveries_router)
router.include_router(sales_orders_router)
router.include_router(smart_orders_router)
router.include_router(stock_router)
router.include_router(sales_router)
router.include_router(admin_router)
router.include_router(route_map_router)
