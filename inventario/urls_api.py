from django.urls import path
from . import api_productos

urlpatterns = [
    # GET /api/productos/
    # GET /api/productos/?q=arroz
    path(
        "productos/",
        api_productos.listar_productos,
        name="api_productos_lista",
    ),

    # GET /api/productos/<id>/
    path(
        "productos/<int:producto_id>/",
        api_productos.detalle_producto,
        name="api_productos_detalle",
    ),

    # GET /api/productos/<id>/stock/
    path(
        "productos/<int:producto_id>/stock/",
        api_productos.stock_producto,
        name="api_productos_stock",
    ),
]
