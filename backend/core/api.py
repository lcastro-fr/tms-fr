from __future__ import annotations

from ninja import NinjaAPI

from catalog.api import ubicaciones_router, zonas_router
from core.api_errors import register_exception_handlers
from logistica.api import ordenes_servicio_router
from tracking.api import ordenes_router
from tracking.api import router as tracking_router
from transportista.api import tarifarios_router
from users.api import auth_router

api = NinjaAPI(
    title="TMS FR API",
    version="1.0.0",
    description="API interna del TMS",
    urls_namespace="api_v1",
    docs_url="/docs",
)

register_exception_handlers(api)

api.add_router("/auth/", auth_router)
api.add_router("/tickets/", tracking_router)
api.add_router("/ordenes-servicio/", ordenes_router)
api.add_router("/ordenes-servicio/", ordenes_servicio_router)
api.add_router("/zonas/", zonas_router)
api.add_router("/ubicaciones/", ubicaciones_router)
api.add_router("/tarifarios/", tarifarios_router)
