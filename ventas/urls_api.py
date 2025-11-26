from django.urls import path
from . import api_ventas

urlpatterns = [
    path("ventas/crear/", api_ventas.crear_venta, name="api_crear_venta"),
]
