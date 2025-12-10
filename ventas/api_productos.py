from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from inventario.models import Producto


def _producto_to_dict(prod: Producto):
    return {
        "id": prod.id,
        "nombre": prod.nombre,
        "descripcion": prod.descripcion or "",
        "precio_venta": str(prod.precio_venta),
        "stock_actual": prod.stock_actual,
        "activo": prod.es_activo,
    }


@csrf_exempt
@require_GET
def lista_productos(request):
    """
    Lista productos activos, con filtro opcional por nombre o descripción.
    GET /api/pos/productos/?q=...
    (ruta exacta depende de tus urls.py)
    """
    q = request.GET.get("q", "").strip()

    qs = Producto.objects.filter(es_activo=True)

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(descripcion__icontains=q)
        )

    results = [_producto_to_dict(p) for p in qs.order_by("nombre")]

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        },
        status=200,
    )


@csrf_exempt
@require_GET
def detalle_producto(request, producto_id: int):
    """
    Devuelve detalle de un producto activo.
    Si no existe, responde JSON 404 (no HTML).
    """
    try:
        prod = Producto.objects.get(pk=producto_id, es_activo=True)
    except Producto.DoesNotExist:
        return JsonResponse(
            {"error": "Producto no encontrado."},
            status=404,
        )

    return JsonResponse(_producto_to_dict(prod), status=200)


@csrf_exempt
@require_GET
def stock_producto(request, producto_id: int):
    """
    Devuelve solo el stock de un producto activo.
    Si no existe, responde JSON 404 (no HTML).
    """
    try:
        prod = Producto.objects.get(pk=producto_id, es_activo=True)
    except Producto.DoesNotExist:
        return JsonResponse(
            {"error": "Producto no encontrado."},
            status=404,
        )

    return JsonResponse(
        {
            "id": prod.id,
            "nombre": prod.nombre,
            "stock_actual": prod.stock_actual,
        },
        status=200,
    )
