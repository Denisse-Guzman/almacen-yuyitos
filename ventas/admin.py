from django.contrib import admin
from .models import Venta, DetalleVenta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "cliente", "total", "es_credito")
    list_filter = ("es_credito", "fecha", "cliente")
    search_fields = ("id", "cliente__nombre", "cliente__rut")
    inlines = [DetalleVentaInline]

    def save_related(self, request, form, formsets, change):
        """
        Se ejecuta DESPUÉS de guardar la Venta y los DetalleVenta.
        Aquí ya tenemos el total correcto.
        """
        super().save_related(request, form, formsets, change)

        from clientes.models import MovimientoCredito  # por si acaso, aunque usamos el método del cliente

        venta = form.instance

        # nos aseguramos que el total esté bien recalculado
        venta.actualizar_total()

        if venta.es_credito and venta.cliente:
            # Para evitar duplicar movimientos si se edita la venta,
            # primero revisamos si ya hay uno tipo COMPRA para esta venta.
            mov_existente = MovimientoCredito.objects.filter(
                venta=venta,
                tipo="COMPRA",
            ).order_by("id").first()

            if mov_existente is None:
                # Creamos el movimiento usando el método del cliente
                venta.cliente.registrar_movimiento_credito(
                    tipo="COMPRA",
                    monto=venta.total,
                    venta=venta,
                    observaciones=f"Compra a crédito (Venta #{venta.id})",
                )
            else:
                # Si ya existe, actualizamos el monto y el saldo
                saldo_antes = mov_existente.saldo_despues - mov_existente.monto
                mov_existente.monto = venta.total
                nuevo_saldo = saldo_antes + venta.total
                mov_existente.saldo_despues = nuevo_saldo
                mov_existente.save()

                # Y actualizamos también el saldo_actual del cliente
                cliente = venta.cliente
                cliente.saldo_actual = nuevo_saldo
                cliente.save(update_fields=["saldo_actual"])


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ("venta", "producto", "cantidad", "precio_unitario", "subtotal")
    list_filter = ("producto",)
