from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    esta_activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    codigo_barras = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Código de barras o PLU (opcional)",
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
    )

    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)

    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)

    tiene_vencimiento = models.BooleanField(default=False)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    es_activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
