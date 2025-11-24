# clientes/models.py
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    rut = models.CharField(
        max_length=12,
        unique=True,
        help_text="RUT con guion, ej: 12.345.678-9",
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
        help_text="Cupo máximo de crédito del cliente",
    )
    saldo_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Deuda actual del cliente (monto pendiente)",
    )

    # Estado y auditoría
    es_activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

    # --- Reglas de negocio de crédito ---

    def puede_comprar_a_credito(self, monto: Decimal) -> bool:
        """
        True si el cliente puede tomar una nueva compra a crédito
        por 'monto' sin pasarse del cupo.
        """
        if not self.tiene_credito or not self.es_activo:
            return False
        return (self.saldo_actual + monto) <= self.cupo_maximo

    def registrar_movimiento_credito(
        self,
        tipo: str,
        monto: Decimal,
        venta=None,
        observaciones: str = "",
    ):
        """
        Crea un MovimientoCredito usando este cliente como dueño.
        Se usa desde Venta.save() para crear la COMPRA, y también
        lo puedes llamar cuando registres abonos manuales en una vista.
        """
        from .models import MovimientoCredito  # evita import circular

        monto = Decimal(monto)

        # Validaciones de negocio reutilizables
        if tipo == "COMPRA":
            if not self.puede_comprar_a_credito(monto):
                raise ValidationError(
                    "El monto de la compra supera el cupo disponible del cliente."
                )
            nuevo_saldo = self.saldo_actual + monto

        elif tipo == "ABONO":
            if monto <= 0:
                raise ValidationError("El abono debe ser mayor que 0.")
            if monto > self.saldo_actual:
                raise ValidationError(
                    "El abono no puede ser mayor que la deuda actual del cliente."
                )
            nuevo_saldo = self.saldo_actual - monto

        elif tipo == "AJUSTE":
            nuevo_saldo = self.saldo_actual - monto

        else:
            raise ValidationError(f"Tipo de movimiento no soportado: {tipo}")

        # Crea el movimiento con el saldo_despues correcto
        mov = MovimientoCredito.objects.create(
            cliente=self,
            venta=venta,
            tipo=tipo,
            monto=monto,
            saldo_despues=nuevo_saldo,
            fecha=timezone.now(),
            observaciones=observaciones,
        )

        # Actualiza saldo_actual del cliente
        self.saldo_actual = nuevo_saldo
        self.save(update_fields=["saldo_actual"])

        return mov


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
        Si se crea un movimiento directamente desde el admin,
        también queremos actualizar el saldo del cliente aquí.

        OJO: la lógica es casi la misma que en Cliente.registrar_movimiento_credito,
        para que el comportamiento sea consistente.
        """
        es_nuevo = self.pk is None

        if es_nuevo:
            cliente = self.cliente
            monto = Decimal(self.monto)

            if self.tipo == "COMPRA":
                if not cliente.puede_comprar_a_credito(monto):
                    raise ValidationError(
                        "El monto de la compra supera el cupo disponible del cliente."
                    )
                nuevo_saldo = cliente.saldo_actual + monto

            elif self.tipo == "ABONO":
                if monto <= 0:
                    raise ValidationError("El abono debe ser mayor que 0.")
                if monto > cliente.saldo_actual:
                    raise ValidationError(
                        "El abono no puede ser mayor que la deuda actual del cliente."
                    )
                nuevo_saldo = cliente.saldo_actual - monto

            elif self.tipo == "AJUSTE":
                nuevo_saldo = cliente.saldo_actual - monto

            else:
                raise ValidationError(f"Tipo de movimiento no soportado: {self.tipo}")

            # Guardamos el saldo que deja este movimiento
            self.saldo_despues = nuevo_saldo

            # Actualizamos saldo_actual del cliente
            cliente.saldo_actual = nuevo_saldo
            cliente.save(update_fields=["saldo_actual"])

        super().save(*args, **kwargs)
