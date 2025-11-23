from django.contrib import admin
from .models import Venta, DetalleVenta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'cliente', 'tipo_pago', 'es_credito', 'total')
    list_filter = ('tipo_pago', 'es_credito', 'fecha')
    search_fields = ('id', 'cliente__nombre')
    inlines = [DetalleVentaInline]


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'producto', 'cantidad', 'precio_unitario', 'subtotal')
    list_filter = ('producto',)
