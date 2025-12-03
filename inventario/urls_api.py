from django.urls import path
from . import api_productos


urlpatterns = [
    # Listar productos
    path(
        "productos/",
        api_productos.listar_productos,
        name="api_productos_lista",
    ),
    # Detalle de producto
    path(
        "productos/<int:producto_id>/",
        api_productos.detalle_producto,
        name="api_productos_detalle",
    ),
    # Stock de producto
    path(
        "productos/<int:producto_id>/stock/",
        api_productos.stock_producto,
        name="api_productos_stock",
    ),
    # Crear producto
    path(
        "productos/crear/",
        api_productos.crear_producto,
        name="api_productos_crear",
    ),
    # Actualizar producto
    path(
        "productos/<int:producto_id>/actualizar/",
        api_productos.actualizar_producto,
        name="api_productos_actualizar",
    ),
    # Eliminar producto
    path(
        "productos/<int:producto_id>/eliminar/",
        api_productos.eliminar_producto,
        name="api_productos_eliminar",
    ),

    # Listar categorías
    path(
        "categorias/",
        api_productos.listar_categorias,
        name="api_categorias_lista",
    ),
]