from fastapi import APIRouter

from .outbox_events.router import router as outbox_router

main_router = APIRouter(prefix="/api")

list_routers = (
    outbox_router,
)

for router in list_routers:
    main_router.include_router(router)

