from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'tiene_credito', 'cupo_maximo', 'saldo_actual', 'es_activo')
    list_filter = ('tiene_credito', 'es_activo')
    search_fields = ('nombre', 'rut')

