from django.urls import path
from . import api_ventas, api_reportes, api_productos

urlpatterns = [
# Ventas
    path("ventas/crear/", api_ventas.crear_venta, name="api_crear_venta"),

    # Productos
    path("productos/", api_productos.lista_productos, name="api_lista_productos"),
    path("productos/<int:producto_id>/", api_productos.detalle_producto, name="api_detalle_producto"),
    path("productos/<int:producto_id>/stock/", api_productos.stock_producto, name="api_stock_producto"),

    # Reportes
    path("reportes/ventas/", api_reportes.reporte_ventas, name="api_reporte_ventas"),
    path("reportes/productos-mas-vendidos/", api_reportes.productos_mas_vendidos, name="api_productos_mas_vendidos"),
]

