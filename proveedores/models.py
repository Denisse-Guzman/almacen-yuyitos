from decimal import Decimal

from django.db import models
from django.utils import timezone

from inventario.models import Producto


class Proveedor(models.Model):
    nombre = models.CharField(max_length=255)
    rut = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)

    es_activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class OrdenCompra(models.Model):
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="ordenes_compra",
        null=True,
        blank=True,
    )
    # registrar compras sin proveedor
    nombre_proveedor_libre = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nombre del proveedor si no está registrado en el sistema.",
    )

    fecha = models.DateTimeField(default=timezone.now)
    observaciones = models.TextField(blank=True)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        base = f"OC #{self.id or 'nuevo'}"
        if self.proveedor:
            return f"{base} - {self.proveedor.nombre}"
        if self.nombre_proveedor_libre:
            return f"{base} - {self.nombre_proveedor_libre}"
        return base

    def recalcular_total(self):
        total = self.detalles.aggregate(
            total=models.Sum(models.F("cantidad") * models.F("costo_unitario"))
        )["total"] or Decimal("0.00")
        self.total = total
        self.save(update_fields=["total"])
        return self.total


class DetalleOrdenCompra(models.Model):
    orden = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_orden_compra",
    )
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"

    def save(self, *args, **kwargs):
        # Calcula subtotal simple: cantidad * costo_unitario
        self.subtotal = (self.cantidad or 0) * (self.costo_unitario or 0)
        super().save(*args, **kwargs)

