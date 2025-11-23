from django.contrib import admin

from .models import Venta, DetalleVenta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    inlines = [DetalleVentaInline]

    # Cómo se ve la lista de ventas
    list_display = ("id", "fecha", "cliente_mostrado", "total", "es_credito")
    list_filter = ("es_credito", "fecha")
    search_fields = ("id", "cliente__nombre", "nombre_cliente_libre")

    # Campos que se muestran en el formulario
    fieldsets = (
        ("Datos del cliente", {
            "fields": ("cliente", "nombre_cliente_libre"),
            "description": (
                "Puedes seleccionar un cliente registrado "
                "O escribir el nombre manualmente."
            ),
        }),
        ("Información de la venta", {
            "fields": ("fecha", "es_credito", "total", "observaciones"),
        }),
    )

    # total no se pueda editar a mano
    readonly_fields = ("total",)

    def cliente_mostrado(self, obj):
        """Qué mostrar en la columna 'Cliente' de la lista."""
        if obj.cliente:
            return obj.cliente.nombre
        return obj.nombre_cliente_libre or "-"
    cliente_mostrado.short_description = "Cliente"


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ("venta", "producto", "cantidad", "precio_unitario", "subtotal")
    list_select_related = ("venta", "producto")
