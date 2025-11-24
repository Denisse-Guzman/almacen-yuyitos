from decimal import Decimal

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

    # ---------- LÓGICA DE CRÉDITO EN EL CLIENTE ----------

    def obtener_saldo_actual(self) -> Decimal:
        """
        Devuelve el saldo actual del cliente
        leyendo el último MovimientoCredito.
        Si no tiene movimientos, el saldo es 0.
        """
        ultimo = self.movimientos_credito.order_by("-fecha", "-id").first()
        if ultimo:
            return ultimo.saldo_despues
        return Decimal("0.00")

    def puede_comprar_a_credito(self, monto: Decimal) -> bool:
        """
        Revisa si con este monto no se pasa del cupo máximo.
        """
        if not self.tiene_credito or not self.es_activo:
            return False

        saldo = self.obtener_saldo_actual()
        return (saldo + Decimal(monto)) <= self.cupo_maximo

    def registrar_movimiento_credito(
        self,
        tipo: str,
        monto: Decimal,
        venta=None,
        observaciones: str = "",
    ):
        """
        Crea un MovimientoCredito, calcula el nuevo saldo
        y actualiza también el campo saldo_actual del cliente.
        """
        saldo_actual = self.obtener_saldo_actual()

        if tipo == "COMPRA":
            nuevo_saldo = saldo_actual + Decimal(monto)
        elif tipo in ("ABONO", "AJUSTE"):
            nuevo_saldo = saldo_actual - Decimal(monto)
        else:
            raise ValueError(f"Tipo de movimiento no soportado: {tipo}")

        mov = MovimientoCredito.objects.create(
            cliente=self,
            venta=venta,
            tipo=tipo,
            monto=monto,
            saldo_despues=nuevo_saldo,
            fecha=timezone.now(),
            observaciones=observaciones,
        )

        # Actualizamos el campo saldo_actual para que se vea en el admin
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
        Cliente,
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
