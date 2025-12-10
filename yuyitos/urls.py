"""
URL configuration for yuyitos project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from cuentas import views as cuentas_views


def raiz_a_login(request):
    # Redirige a la vista de login
    return redirect("login")


urlpatterns = [
    path("admin/", admin.site.urls),

    # Raíz del sitio -> login
    path("", raiz_a_login, name="raiz"),

    # API
    path("api/", include("clientes.urls_api")),
    path("api/", include("ventas.urls_api")),
    path("api/", include("inventario.urls_api")),
    path("api/", include("proveedores.urls_api")),

    # Auth
    path("login/", cuentas_views.login_view, name="login"),
    path("logout/", cuentas_views.logout_view, name="logout"),
    path("dashboard/caja/", cuentas_views.dashboard_caja, name="dashboard_caja"),
    path("dashboard/bodega/", cuentas_views.dashboard_bodega, name="dashboard_bodega"),
    path("dashboard/admin/", cuentas_views.dashboard_admin, name="dashboard_admin"),
]
