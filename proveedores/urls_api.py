from django.urls import path
from . import api_proveedores

urlpatterns = [
    path(
        "ingreso-mercaderia/",
        api_proveedores.ingreso_mercaderia,
        name="api_ingreso_mercaderia",
    ),
]
