from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Cliente, MovimientoCredito
from .api_credito import _obtener_cliente


@require_GET
def obtener_saldo_cliente(request):
    """
    GET /api/creditos/saldo/?cliente_id=1
    GET /api/creditos/saldo/?rut=22.567.746-2

    Devuelve saldo_actual y disponible del cliente.
    """
    data = {
        "cliente_id": request.GET.get("cliente_id"),
        "rut": request.GET.get("rut"),
    }

    cliente = _obtener_cliente(data)
    if cliente is None:
        return JsonResponse(
            {"error": "Cliente no encontrado (cliente_id o rut inválido)."},
            status=404,
        )

    disponible = Decimal("0.00")
    if cliente.tiene_credito:
        try:
            disponible = cliente.cupo_maximo - cliente.saldo_actual
        except Exception:
            disponible = Decimal("0.00")

    return JsonResponse(
        {
            "cliente": {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "rut": cliente.rut,
                "tiene_credito": cliente.tiene_credito,
                "cupo_maximo": str(cliente.cupo_maximo),
                "saldo_actual": str(cliente.saldo_actual),
                "disponible": str(disponible),
            }
        }
    )


@require_GET
def listar_movimientos_credito(request):
    """
    GET /api/creditos/movimientos/?cliente_id=1&limit=10
    GET /api/creditos/movimientos/?rut=22.567.746-2&limit=20

    Lista los últimos movimientos de crédito de un cliente.
    """
    data = {
        "cliente_id": request.GET.get("cliente_id"),
        "rut": request.GET.get("rut"),
    }

    cliente = _obtener_cliente(data)
    if cliente is None:
        return JsonResponse(
            {"error": "Cliente no encontrado (cliente_id o rut inválido)."},
            status=404,
        )

    try:
        limit = int(request.GET.get("limit", 20))
    except ValueError:
        limit = 20

    movimientos = (
        MovimientoCredito.objects.filter(cliente=cliente)
        .order_by("-fecha", "-id")[:limit]
    )

    movs_data = []
    for m in movimientos:
        movs_data.append(
            {
                "id": m.id,
                "tipo": m.tipo,
                "monto": str(m.monto),
                "saldo_despues": str(m.saldo_despues),
                "fecha": m.fecha.isoformat(),
                "observaciones": m.observaciones,
                "venta_id": m.venta_id,
            }
        )

    return JsonResponse(
        {
            "cliente": {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "rut": cliente.rut,
            },
            "movimientos": movs_data,
        }
    )
