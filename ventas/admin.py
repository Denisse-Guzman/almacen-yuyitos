from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError

from .models import Venta, DetalleVenta


# 1) Formset que obliga a tener al menos un detalle
class DetalleVentaInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        tiene_detalles_validos = False

        for form in self.forms:
            # Formularios vacíos no tienen cleaned_data útil
            if not hasattr(form, "cleaned_data"):
                continue

            # Si está marcado para borrar, lo ignoramos
            if form.cleaned_data.get("DELETE"):
                continue

            producto = form.cleaned_data.get("producto")
            cantidad = form.cleaned_data.get("cantidad")

            if producto and cantidad and cantidad > 0 and not form.errors:
                tiene_detalles_validos = True
                break

        if not tiene_detalles_validos:
            raise ValidationError("La venta debe tener al menos un producto.")


# 2) Inline que usa ese formset
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    formset = DetalleVentaInlineFormSet


# 3) Admin de Venta
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

        from clientes.models import MovimientoCredito

        venta = form.instance
        venta.actualizar_total()

        if venta.es_credito and venta.cliente:
            mov_existente = MovimientoCredito.objects.filter(
                venta=venta,
                tipo="COMPRA",
            ).order_by("id").first()

            if mov_existente is None:
                venta.cliente.registrar_movimiento_credito(
                    tipo="COMPRA",
                    monto=venta.total,
                    venta=venta,
                    observaciones=f"Compra a crédito (Venta #{venta.id})",
                )
            else:
                saldo_antes = mov_existente.saldo_despues - mov_existente.monto
                mov_existente.monto = venta.total
                nuevo_saldo = saldo_antes + venta.total
                mov_existente.saldo_despues = nuevo_saldo
                mov_existente.save()

                cliente = venta.cliente
                cliente.saldo_actual = nuevo_saldo
                cliente.save(update_fields=["saldo_actual"])


# 4) Admin de DetalleVenta “normal”
@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ("venta", "producto", "cantidad", "precio_unitario", "subtotal")
    list_filter = ("producto",)
