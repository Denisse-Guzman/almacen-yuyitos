from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Producto


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
        "activo": getattr(producto, "activo", True),
    }


@require_GET
def listar_productos(request):
    """
    GET /api/productos/
    GET /api/productos/?q=arroz

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


@require_GET
def detalle_producto(request, producto_id: int):
    """
    GET /api/productos/<producto_id>/

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


@require_GET
def ver_stock(request, producto_id: int):
    """
    GET /api/productos/<producto_id>/stock/

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
