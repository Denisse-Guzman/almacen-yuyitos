import datetime
from decimal import Decimal

from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import Venta, DetalleVenta

from django.contrib.auth.decorators import login_required, user_passes_test
from cuentas.permisos import es_admin


def _rango_fechas(request):
    """
    Lee fecha_desde y fecha_hasta desde el querystring (YYYY-MM-DD).
    Si no vienen, usa la fecha de hoy.
    Devuelve (inicio_datetime, fin_datetime, fecha_desde, fecha_hasta)
    """
    hoy = timezone.localdate()

    desde_str = request.GET.get("fecha_desde")
    hasta_str = request.GET.get("fecha_hasta")

    if not desde_str and not hasta_str:
        fecha_desde = hoy
        fecha_hasta = hoy
    else:
        fecha_desde = parse_date(desde_str) if desde_str else hoy
        fecha_hasta = parse_date(hasta_str) if hasta_str else hoy

        if fecha_desde is None:
            fecha_desde = hoy
        if fecha_hasta is None:
            fecha_hasta = hoy

    inicio_dt = datetime.datetime.combine(fecha_desde, datetime.time.min)
    fin_dt = datetime.datetime.combine(fecha_hasta, datetime.time.max)

    # Aseguramos que son "aware"
    if timezone.is_naive(inicio_dt):
        inicio_dt = timezone.make_aware(inicio_dt)
    if timezone.is_naive(fin_dt):
        fin_dt = timezone.make_aware(fin_dt)

    return inicio_dt, fin_dt, fecha_desde, fecha_hasta


@csrf_exempt
@login_required
@user_passes_test(es_admin)
@require_GET
def ventas_resumen(request):
    """
    GET /api/reportes/ventas-resumen/
    GET /api/reportes/ventas-resumen/?fecha_desde=2025-11-01&fecha_hasta=2025-11-26

    Entrega resumen global de ventas en el rango:
    - cantidad_ventas
    - total_monto
    - total_contado
    - total_credito
    """
    inicio_dt, fin_dt, fecha_desde, fecha_hasta = _rango_fechas(request)

    qs = Venta.objects.filter(fecha__range=(inicio_dt, fin_dt))

    agregados = qs.aggregate(
        cantidad_ventas=Count("id"),
        total_monto=Sum("total"),
        total_contado=Sum("total", filter=Q(es_credito=False)),
        total_credito=Sum("total", filter=Q(es_credito=True)),
    )

    # Normaliza Decimal a string
    def _str_dec(v):
        if v is None:
            return "0.00"
        if isinstance(v, Decimal):
            return str(v)
        return str(v)

    data = {
        "rango": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
        },
        "resumen": {
            "cantidad_ventas": agregados["cantidad_ventas"] or 0,
            "total_monto": _str_dec(agregados["total_monto"]),
            "total_contado": _str_dec(agregados["total_contado"]),
            "total_credito": _str_dec(agregados["total_credito"]),
        },
    }

    return JsonResponse(data, status=200)


@csrf_exempt
@login_required
@user_passes_test(es_admin)
@require_GET
def ventas_por_dia(request):
    """
    Devuelve una lista de días con:
    - fecha
    - cantidad_ventas
    - total_monto
    - total_contado
    - total_credito
    """
    inicio_dt, fin_dt, fecha_desde, fecha_hasta = _rango_fechas(request)

    qs = (
        Venta.objects.filter(fecha__range=(inicio_dt, fin_dt))
        .annotate(dia=TruncDate("fecha"))
        .values("dia")
        .annotate(
            cantidad_ventas=Count("id"),
            total_monto=Sum("total"),
            total_contado=Sum("total", filter=Q(es_credito=False)),
            total_credito=Sum("total", filter=Q(es_credito=True)),
        )
        .order_by("dia")
    )

    def _str_dec(v):
        if v is None:
            return "0.00"
        if isinstance(v, Decimal):
            return str(v)
        return str(v)

    resultados = []
    for fila in qs:
        resultados.append(
            {
                "fecha": fila["dia"].isoformat() if fila["dia"] else None,
                "cantidad_ventas": fila["cantidad_ventas"] or 0,
                "total_monto": _str_dec(fila["total_monto"]),
                "total_contado": _str_dec(fila["total_contado"]),
                "total_credito": _str_dec(fila["total_credito"]),
            }
        )

    data = {
        "rango": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
        },
        "dias": resultados,
    }
    return JsonResponse(data, status=200)


@csrf_exempt
@login_required
@user_passes_test(es_admin)
@require_GET
def productos_mas_vendidos(request):
    """
    Devuelve top N productos por cantidad vendida en el rango.
    GET /api/reportes/productos-mas-vendidos/?limit=10
    """
    inicio_dt, fin_dt, fecha_desde, fecha_hasta = _rango_fechas(request)

    try:
        limit = int(request.GET.get("limit", "10"))
    except ValueError:
        limit = 10

    qs = (
        DetalleVenta.objects.filter(venta__fecha__range=(inicio_dt, fin_dt))
        .values(
            "producto_id",
            "producto__nombre",
            "producto__codigo_barras",
        )
        .annotate(
            total_cantidad=Sum("cantidad"),
            total_monto=Sum("subtotal"),
        )
        .order_by("-total_cantidad", "producto__nombre")
    )

    qs = qs[:limit]

    def _str_dec(v):
        if v is None:
            return "0.00"
        if isinstance(v, Decimal):
            return str(v)
        return str(v)

    resultados = []
    for fila in qs:
        resultados.append(
            {
                "producto_id": fila["producto_id"],
                "nombre": fila["producto__nombre"],
                "codigo_barras": fila["producto__codigo_barras"],
                "total_cantidad": fila["total_cantidad"] or 0,
                "total_monto": _str_dec(fila["total_monto"]),
            }
        )

    data = {
        "rango": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
        },
        "productos": resultados,
    }
    return JsonResponse(data, status=200)


@csrf_exempt
@login_required
@user_passes_test(es_admin)
@require_http_methods(["GET"])
def ventas_por_categoria(request):
    """
    Devuelve ventas agrupadas por categoría (para el gráfico de torta/barras).
    GET /api/reportes/ventas-por-categoria/
    """
    ventas_categoria = DetalleVenta.objects.select_related(
        'producto', 'producto__categoria'
    ).values(
        categoria_nombre=F('producto__categoria__nombre')
    ).annotate(
        total_ventas=Sum('subtotal')
    ).order_by('-total_ventas')
    
    categorias = [{
        'categoria': item['categoria_nombre'] or 'Sin categoría',
        'total': float(item['total_ventas'] or 0)
    } for item in ventas_categoria]
    
    return JsonResponse({'categorias': categorias}, status=200)


@csrf_exempt
@login_required
@user_passes_test(es_admin)
@require_http_methods(["GET"])
def productos_mas_vendidos_mejorado(request):
    """
    Devuelve top 10 productos más vendidos (cantidad y total).
    GET /api/reportes/productos-top/
    """
    productos_top = DetalleVenta.objects.select_related(
        'producto'
    ).values(
        'producto__id', 'producto__nombre'
    ).annotate(
        cantidad_total=Sum('cantidad'),
        total_ventas=Sum('subtotal')
    ).order_by('-cantidad_total')[:10]
    
    productos = [{
        'id': item['producto__id'],
        'nombre': item['producto__nombre'],
        'cantidad': item['cantidad_total'],
        'total': float(item['total_ventas'] or 0)
    } for item in productos_top]
    
    return JsonResponse({'productos': productos}, status=200)
