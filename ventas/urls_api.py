from django.urls import path
from . import api_ventas, api_reportes

urlpatterns = [
    # Crear venta

    path(
        "ventas/crear/",
        api_ventas.crear_venta,
        name="api_crear_venta",
    ),

    # Reporte resumen de ventas
  
    path(
        "reportes/ventas-resumen/",
        api_reportes.ventas_resumen,
        name="api_reportes_ventas_resumen",
    ),

    # Reporte ventas por día
  
    path(
        "reportes/ventas-por-dia/",
        api_reportes.ventas_por_dia,
        name="api_reportes_ventas_por_dia",
    ),

    # Top productos más vendidos
   
    path(
        "reportes/productos-mas-vendidos/",
        api_reportes.productos_mas_vendidos,
        name="api_reportes_productos_mas_vendidos",
    ),
]
