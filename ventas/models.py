from django.db import models

class Venta(models.Model):
    TIPO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('DEBITO', 'Débito'),
        ('CREDITO', 'Crédito'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('OTRO', 'Otro'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
  
    cliente = models.ForeignKey(
        'clientes.Cliente',       
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Cliente asociado (opcional)",
    )
    tipo_pago = models.CharField(
        max_length=20,
        choices=TIPO_PAGO_CHOICES,
        default='EFECTIVO',
    )
    es_credito = models.BooleanField(
        default=False,
        help_text="Marcar si esta venta es a crédito",
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total final de la venta",
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Notas internas de la venta (opcional)",
    )

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']

    def __str__(self):
        if self.cliente:
            return f"Venta #{self.id} - {self.cliente} - ${self.total}"
        return f"Venta #{self.id} - ${self.total}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles'
    )

    producto = models.ForeignKey(
        'inventario.Producto',
        on_delete=models.PROTECT,
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,   
    )

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"

    def save(self, *args, **kwargs):
        # Calcular subtotal automáticamente
        self.subtotal = (self.precio_unitario or 0) * self.cantidad
        super().save(*args, **kwargs)

