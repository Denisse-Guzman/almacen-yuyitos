from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET
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


@require_GET
def lista_productos(request):
    """
    GET /api/productos/
    GET /api/productos/?q=texto

    Lista productos activos, con filtro opcional por nombre o descripción.
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
        }
    )


@require_GET
def detalle_producto(request, producto_id: int):
    """
    GET /api/productos/<producto_id>/
    """
    try:
        prod = Producto.objects.get(pk=producto_id, es_activo=True)
    except Producto.DoesNotExist:
        raise Http404("Producto no encontrado")

    return JsonResponse(_producto_to_dict(prod))


@require_GET
def stock_producto(request, producto_id: int):
    """
    GET /api/productos/<producto_id>/stock/
    """
    try:
        prod = Producto.objects.get(pk=producto_id, es_activo=True)
    except Producto.DoesNotExist:
        raise Http404("Producto no encontrado")

    return JsonResponse(
        {
            "id": prod.id,
            "nombre": prod.nombre,
            "stock_actual": prod.stock_actual,
        }
    )
