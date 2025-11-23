from django.db import models

from django.db import models

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

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

