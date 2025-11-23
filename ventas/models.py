from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from inventario.models import Producto
from clientes.models import Cliente


class Venta(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas",
    )
    
    nombre_cliente_libre = models.CharField(
        "Nombre cliente (libre)",
        max_length=150,
        blank=True,
        help_text="Usar si el cliente no está registrado",
    )

    fecha = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    es_credito = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)

    def actualizar_total(self):
        """Recalcula el total a partir de los detalles."""
        total = sum(
            (detalle.subtotal or Decimal("0.00"))
            for detalle in self.detalles.all()
        )
        self.total = total
        self.save(update_fields=["total"])

    def __str__(self):
        if self.cliente:
            return f"Venta #{self.id} - {self.cliente.nombre} - ${self.total}"
        if self.nombre_cliente_libre:
            return f"Venta #{self.id} - {self.nombre_cliente_libre} - ${self.total}"
        return f"Venta #{self.id} - ${self.total}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_venta",
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        """
        - Pone precio_unitario = precio_venta del producto si viene vacío
        - Ajusta stock del producto (nuevo, o cambio de cantidad)
        - Recalcula subtotal
        - Actualiza total de la venta
        """
        if self.pk:
            anterior = DetalleVenta.objects.get(pk=self.pk)
            diferencia = self.cantidad - anterior.cantidad
        else:
            anterior = None
            diferencia = self.cantidad

        if self.precio_unitario is None:
            self.precio_unitario = self.producto.precio_venta

        if diferencia > 0:
            if not self.producto.hay_stock(diferencia):
                raise ValidationError(
                    f"No hay stock suficiente de '{self.producto.nombre}' "
                    f"para vender {self.cantidad} unidades."
                )
            self.producto.descontar_stock(diferencia)
        elif diferencia < 0:
            self.producto.aumentar_stock(-diferencia)

        self.subtotal = (self.precio_unitario or Decimal("0.00")) * self.cantidad

        super().save(*args, **kwargs)

        self.venta.actualizar_total()

    def delete(self, *args, **kwargs):
        venta = self.venta
        self.producto.aumentar_stock(self.cantidad)
        super().delete(*args, **kwargs)
        venta.actualizar_total()

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"
