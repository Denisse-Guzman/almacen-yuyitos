import json
from datetime import datetime
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.db.models import Sum

from .models import Venta, DetalleVenta


@require_GET
def reporte_ventas(request):
    """
    GET /api/reportes/ventas/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD

    Si no se envían parámetros, usa el día de hoy.
    """
    desde_str = request.GET.get("desde")
    hasta_str = request.GET.get("hasta")

    hoy = timezone.localdate()

    # Parseo de fechas
    if desde_str:
        try:
            desde = datetime.strptime(desde_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse(
                {"error": "Formato inválido para 'desde'. Use YYYY-MM-DD."},
                status=400,
            )
    else:
        desde = hoy

    if hasta_str:
        try:
            hasta = datetime.strptime(hasta_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse(
                {"error": "Formato inválido para 'hasta'. Use YYYY-MM-DD."},
                status=400,
            )
    else:
        hasta = hoy

    if hasta < desde:
        return JsonResponse(
            {"error": "'hasta' no puede ser menor que 'desde'."},
            status=400,
        )

    # Ventas del rango
    qs = Venta.objects.filter(
        fecha__date__gte=desde,
        fecha__date__lte=hasta,
    ).order_by("fecha")

    total_ventas = qs.count()
    total_monto = sum((v.total or Decimal("0.00")) for v in qs)

    # Agrupar por día
    ventas_por_dia = {}
    for v in qs:
        fecha_dia = v.fecha.date().isoformat()
        data = ventas_por_dia.setdefault(
            fecha_dia,
            {"fecha": fecha_dia, "cantidad": 0, "total": Decimal("0.00")},
        )
        data["cantidad"] += 1
        data["total"] += v.total or Decimal("0.00")

    ventas_por_dia_list = [
        {
            "fecha": d["fecha"],
            "cantidad": d["cantidad"],
            "total": str(d["total"]),
        }
        for d in ventas_por_dia.values()
    ]

    return JsonResponse(
        {
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat(),
            "total_ventas": total_ventas,
            "total_monto": str(total_monto),
            "ventas_por_dia": ventas_por_dia_list,
        }
    )

@require_GET
def productos_mas_vendidos(request):
    """
    GET /api/reportes/productos-mas-vendidos/?limit=10

    Devuelve los productos ordenados por cantidad vendida (DetalleVenta).
    """
    try:
        limit = int(request.GET.get("limit", "10"))
    except ValueError:
        limit = 10

    if limit <= 0:
        limit = 10

    detalles = (
        DetalleVenta.objects
        .values("producto_id", "producto__nombre")
        .annotate(total_cantidad=Sum("cantidad"))
        .order_by("-total_cantidad")
    )

    results = []
    for d in detalles[:limit]:
        results.append(
            {
                "producto_id": d["producto_id"],
                "nombre": d["producto__nombre"],
                "cantidad_vendida": d["total_cantidad"],
            }
        )

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        }
    )
