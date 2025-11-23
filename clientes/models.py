from django.db import models
from decimal import Decimal
from django.db import models
from django.utils import timezone

class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    rut = models.CharField(
        max_length=12,
        unique=True,
        help_text="RUT con guion, ej: 12.345.678-9"
    )
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)

    # Crédito
    tiene_credito = models.BooleanField(default=False)
    cupo_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Cupo máximo de crédito del cliente"
    )
    saldo_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Deuda actual del cliente (monto pendiente)"
    )

    # Estado y auditoría
    es_activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

class MovimientoCredito(models.Model):
    TIPO_CHOICES = [
        ("COMPRA", "Compra a crédito"),
        ("ABONO", "Abono"),
        ("AJUSTE", "Ajuste"),
    ]

    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="movimientos_credito",
    )

    # Venta asociada (opcional, normalmente solo para COMPRA)
    venta = models.ForeignKey(
        "ventas.Venta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_credito",
    )

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_despues = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    fecha = models.DateTimeField(default=timezone.now)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Movimiento de crédito"
        verbose_name_plural = "Movimientos de crédito"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.tipo} - {self.cliente.nombre} - ${self.monto}"

    def save(self, *args, **kwargs):
        """
        Al crear un movimiento nuevo, actualiza el saldo_actual del cliente
        y guarda en saldo_despues cómo quedó.
        Si solo se edita un movimiento ya existente, no toca el saldo.
        """
        es_nuevo = self.pk is None

        if es_nuevo:
            cliente = self.cliente


            if self.tipo == "COMPRA":
                if not cliente.puede_comprar_a_credito(self.monto):
                    raise ValueError("El monto supera el cupo de crédito del cliente.")
                nuevo_saldo = cliente.saldo_actual + self.monto

            elif self.tipo in ("ABONO", "AJUSTE"):
                nuevo_saldo = cliente.saldo_actual - self.monto

            else:
                nuevo_saldo = cliente.saldo_actual

            self.saldo_despues = nuevo_saldo

            cliente.saldo_actual = nuevo_saldo
            cliente.save(update_fields=["saldo_actual"])

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

    def puede_comprar_a_credito(self, monto: Decimal) -> bool:
        """Revisa si con este monto no se pasa del cupo."""
        if not self.tiene_credito or not self.es_activo:
            return False
        return (self.saldo_actual + monto) <= self.cupo_maximo