from __future__ import annotations

from ninja import NinjaAPI

from catalog.api import zonas_router
from core.api_errors import register_exception_handlers
from tracking.api import ordenes_router
from tracking.api import router as tracking_router

# csrf=False es correcto mientras la única auth sea por header. Pasar a True al
# agregar auth por sesión para la SPA.
api = NinjaAPI(
    title="TMS FR API",
    version="1.0.0",
    description="API interna del TMS",
    urls_namespace="api_v1",
    docs_url="/docs",
)

register_exception_handlers(api)

api.add_router("/tickets/", tracking_router)
api.add_router("/ordenes-servicio/", ordenes_router)
api.add_router("/zonas/", zonas_router)
