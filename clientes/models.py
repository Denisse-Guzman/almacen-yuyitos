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

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

    def puede_comprar_a_credito(self, monto: Decimal) -> bool:
        """
        Revisa si el cliente puede tomar este monto a crédito
        sin pasarse del cupo.
        """
        if monto is None:
            monto = Decimal("0.00")
        monto = Decimal(monto)

        if not self.tiene_credito or not self.es_activo:
            return False

        return (self.saldo_actual + monto) <= self.cupo_maximo

    def obtener_saldo_actual(self) -> Decimal:
        """
        Devuelve el saldo_actual almacenado en el cliente.
        (Lo dejamos como wrapper por si después quieres
        cambiar la lógica y leer desde movimientos).
        """
        return self.saldo_actual

    def registrar_movimiento_credito(self, tipo, monto, venta=None, observaciones=""):
        """
        Crea un MovimientoCredito y actualiza saldo_actual del cliente.
        Esta función es la que usa Venta.save() cuando es_credito = True.
        """
        from .models import MovimientoCredito  # referencia al modelo de abajo

        if monto is None:
            monto = Decimal("0.00")
        monto = Decimal(monto)

        saldo_antes = self.saldo_actual

        if tipo == "COMPRA":
            # Validamos cupo antes de registrar
            if not self.puede_comprar_a_credito(monto):
                raise ValueError("El monto supera el cupo de crédito del cliente.")
            saldo_despues = saldo_antes + monto

        elif tipo == "ABONO":
            saldo_despues = saldo_antes - monto

        elif tipo == "AJUSTE":
            # Interpretamos el ajuste como “fijar” el saldo en ese monto
            saldo_despues = monto

        else:
            raise ValueError(f"Tipo de movimiento no soportado: {tipo}")

        mov = MovimientoCredito.objects.create(
            cliente=self,
            venta=venta,
            tipo=tipo,
            monto=monto,
            saldo_despues=saldo_despues,
            fecha=timezone.now(),
            observaciones=observaciones or "",
        )

        # Actualizamos saldo_actual del cliente
        self.saldo_actual = saldo_despues
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
