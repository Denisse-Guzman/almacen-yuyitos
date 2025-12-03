from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Producto
from cuentas.permisos import es_cajero_o_admin, es_bodeguero_o_admin


def _producto_a_dict(producto: Producto):
    """
    Serializa un producto a dict simple para JSON.
    Ajusta los campos según tu modelo real.
    """
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "descripcion": getattr(producto, "descripcion", ""),
        "precio_venta": str(producto.precio_venta),
        "stock_actual": producto.stock_actual,
        # En el modelo el campo es `es_activo`, la clave en el JSON la dejamos como "activo"
        "activo": getattr(producto, "es_activo", True),
    }


def _puede_ver_productos(user):
    """
    Permiso: puede ver productos si es Cajero, Bodeguero o Admin.
    """
    return es_cajero_o_admin(user) or es_bodeguero_o_admin(user)


@csrf_exempt
@login_required
@user_passes_test(_puede_ver_productos)
@require_GET
def listar_productos(request):
    """

    Lista productos, opcionalmente filtrando por nombre con ?q=
    """
    q = request.GET.get("q", "").strip()

    productos = Producto.objects.all()

    if q:
        productos = productos.filter(nombre__icontains=q)

    productos = productos.order_by("nombre")

    data = [_producto_a_dict(p) for p in productos]

    return JsonResponse(
        {
            "count": len(data),
            "results": data,
        },
        status=200,
    )


@csrf_exempt
@login_required
@user_passes_test(_puede_ver_productos)
@require_GET
def detalle_producto(request, producto_id: int):
    """

    Devuelve la info de un producto específico.
    """
    try:
        producto = Producto.objects.get(pk=producto_id)
    except Producto.DoesNotExist:
        return JsonResponse(
            {"error": "Producto no encontrado."},
            status=404,
        )

    return JsonResponse(
        _producto_a_dict(producto),
        status=200,
    )


@csrf_exempt
@login_required
@user_passes_test(_puede_ver_productos)
@require_GET
def stock_producto(request, producto_id: int):
    """


    Devuelve solo info de stock (útil para el POS).
    """
    try:
        producto = Producto.objects.get(pk=producto_id)
    except Producto.DoesNotExist:
        return JsonResponse(
            {"error": "Producto no encontrado."},
            status=404,
        )

    return JsonResponse(
        {
            "id": producto.id,
            "nombre": producto.nombre,
            "stock_actual": producto.stock_actual,
        },
        status=200,
    )
