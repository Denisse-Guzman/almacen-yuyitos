from django.urls import path
from . import api_productos

urlpatterns = [
    # Productos (lista + crear)
    # GET  /api/productos/      -> lista productos
    # POST /api/productos/      -> crea producto
    path(
        "productos/",
        api_productos.productos_collection,
        name="api_productos_collection",
    ),

    # Alias opcional por si el frontend aún llama a /productos/crear/
    # (GET no hace nada aquí, pero POST creará igual el producto)
    path(
        "productos/crear/",
        api_productos.productos_collection,
        name="api_productos_crear",
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

    # Listar categorías
    path(
        "categorias/",
        api_productos.listar_categorias,
        name="api_categorias_lista",
    ),
]
