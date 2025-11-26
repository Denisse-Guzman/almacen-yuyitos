from django.urls import path
from .api_credito import abonar_credito
from . import api_credito,api_clientes, api_consultas

urlpatterns = [
    # Abonos
    path(
        "creditos/abonar/",
        api_credito.abonar_credito,
        name="abonar_credito",
    ),

    # Consultar saldo
    path(
        "creditos/saldo/",
        api_credito.ver_saldo,
        name="ver_saldo_credito",
    ),

    # Listar movimientos
    path(
        "creditos/movimientos/",
        api_credito.listar_movimientos,
        name="listar_movimientos_credito",
    ),
    # Clientes con deuda
    path("creditos/deudas/", api_credito.clientes_con_deuda, name="clientes_con_deuda"),
        # Clientes
    path(
        "clientes/",
        api_clientes.lista_clientes,
        name="lista_clientes",
    ),
    path(
        "clientes/<int:cliente_id>/",
        api_clientes.detalle_cliente,
        name="detalle_cliente",
    ),
    path(
        "clientes/crear/",
        api_clientes.crear_cliente,
        name="crear_cliente",
    ),
]

