from django.contrib import admin
from .models import Proveedor, OrdenCompra, DetalleOrdenCompra


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "telefono", "email", "es_activo")
    search_fields = ("nombre", "rut")


class DetalleOrdenCompraInline(admin.TabularInline):
    model = DetalleOrdenCompra
    extra = 0


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "proveedor", "nombre_proveedor_libre", "total")
    search_fields = ("id", "proveedor__nombre", "nombre_proveedor_libre")
    date_hierarchy = "fecha"
    inlines = [DetalleOrdenCompraInline]
