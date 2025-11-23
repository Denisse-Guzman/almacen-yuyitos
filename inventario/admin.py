from django.contrib import admin
from .models import Categoria, Producto


class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "esta_activa")
    search_fields = ("nombre",)
    list_filter = ("esta_activa",)


class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo_barras",
        "categoria",
        "precio_venta",
        "stock_actual",
        "stock_minimo",
        "es_activo",
    )
    search_fields = ("nombre", "codigo_barras")
    list_filter = ("categoria", "es_activo", "tiene_vencimiento")


admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Producto, ProductoAdmin)
