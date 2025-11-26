from django.urls import path
from . import api_ventas, api_reportes, api_productos

urlpatterns = [
    # --- VENTAS ---
    path("ventas/crear/", api_ventas.crear_venta, name="api_crear_venta"),

    # --- REPORTES ---
    path(
        "reportes/ventas-resumen/",
        api_reportes.ventas_resumen,
        name="api_reportes_ventas_resumen",
    ),
    path(
        "reportes/ventas-por-dia/",
        api_reportes.ventas_por_dia,
        name="api_reportes_ventas_por_dia",
    ),
    path(
        "reportes/productos-mas-vendidos/",
        api_reportes.productos_mas_vendidos,
        name="api_reportes_productos_mas_vendidos",
    ),

    # --- PRODUCTOS  ---
    path(
        "productos/",
        api_productos.lista_productos,
        name="api_productos_lista",
    ),
    path(
        "productos/<int:producto_id>/",
        api_productos.detalle_producto,
        name="api_productos_detalle",
    ),
    path(
        "productos/<int:producto_id>/stock/",
        api_productos.stock_producto,
        name="api_productos_stock",
    ),
]

