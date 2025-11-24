import os
from litestar import Litestar
from litestar.di import Provide
from litestar.openapi import OpenAPIConfig

from app.controllers.user_controller import UserController
from app.controllers.product_controller import ProductController
from app.controllers.order_controller import OrderController
from app.dependencies import (
    provide_db_session,
    provide_user_repository,
    provide_user_service,
    provide_product_repository,
    provide_product_service,
    provide_order_repository,
    provide_order_service,
)


app = Litestar(
    route_handlers=[
        UserController,
        ProductController,
        OrderController,
    ],
    dependencies={
        "db_session": Provide(provide_db_session),
        "user_repository": Provide(provide_user_repository),
        "user_service": Provide(provide_user_service),
        "product_repository": Provide(provide_product_repository),
        "product_service": Provide(provide_product_service),
        "order_repository": Provide(provide_order_repository),
        "order_service": Provide(provide_order_service),
    },
    openapi_config=OpenAPIConfig(
        title="E-Commerce API",
        version="1.0.0",
        description="API для управления пользователями, продуктами и заказами с использованием Dependency Injection и SQLAlchemy",
    ),
)


if __name__ == "__main__":
    import uvicorn
    import logging
    
    # Логгирование для отладки
    logging.basicConfig(level=logging.DEBUG)
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="debug"
    )
