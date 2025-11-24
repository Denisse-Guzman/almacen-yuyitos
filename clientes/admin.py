from django.contrib import admin
from .models import Cliente, MovimientoCredito


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "tiene_credito", "cupo_maximo", "saldo_actual", "es_activo")
    search_fields = ("nombre", "rut")
    list_filter = ("tiene_credito", "es_activo")


@admin.register(MovimientoCredito)
class MovimientoCreditoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "cliente", "tipo", "monto", "saldo_despues", "venta")
    list_filter = ("tipo", "cliente")
    search_fields = ("cliente__nombre", "cliente__rut", "observaciones")

    readonly_fields = ("saldo_despues", "fecha")

    def has_change_permission(self, request, obj=None):
        """
        Para que los movimientos NO se editen después de creados
        (así no se descuadra el saldo). Solo se pueden crear o borrar.
        """
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)
