from django.urls import path
from . import api_productos

urlpatterns = [
    # Lista de productos, con filtro opcional ?q=
    path(
        "productos/",
        api_productos.listar_productos,
        name="listar_productos",
    ),

    # Detalle de un producto
    path(
        "productos/<int:producto_id>/",
        api_productos.detalle_producto,
        name="detalle_producto",
    ),

    # Stock de un producto
    path(
        "productos/<int:producto_id>/stock/",
        api_productos.ver_stock,
        name="ver_stock_producto",
    ),
]
