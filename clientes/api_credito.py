import json
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from .models import Cliente, MovimientoCredito

from django.contrib.auth.decorators import login_required, user_passes_test
from cuentas.permisos import es_cajero_o_admin
from cuentas.permisos import es_admin
def _obtener_cliente(data):
    """
    Intenta obtener un cliente por cliente_id o rut.
    data puede venir de JSON (POST) o de request.GET (dict).
    """
    cliente_id = data.get("cliente_id")
    rut = data.get("rut")

    if cliente_id is not None:
        try:
            return Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            return None

    if rut:
        try:
            return Cliente.objects.get(rut=rut)
        except Cliente.DoesNotExist:
            return None

    return None


# =========================
# 1) ABONAR CRÉDITO 
# =========================
@csrf_exempt
@login_required
@user_passes_test(es_cajero_o_admin)
@require_POST
def abonar_credito(request):
    """
    Endpoint para registrar un abono al crédito de un cliente.

    POST /api/creditos/abonar/

    Body JSON:
    {
        "cliente_id": 3,   // o "rut": "12.345.678-9"
        "monto": "5000",
        "observaciones": "Pago en efectivo"
    }
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "JSON inválido en el cuerpo de la solicitud."},
            status=400,
        )

    cliente = _obtener_cliente(data)
    if cliente is None:
        return JsonResponse(
            {"error": "Cliente no encontrado (cliente_id o rut inválido)."},
            status=404,
        )

    monto_raw = data.get("monto")
    if monto_raw is None:
        return JsonResponse(
            {"error": "El campo 'monto' es obligatorio."},
            status=400,
        )

    try:
        monto = Decimal(str(monto_raw))
    except (InvalidOperation, TypeError):
        return JsonResponse(
            {"error": "El campo 'monto' debe ser un número válido."},
            status=400,
        )

    if monto <= 0:
        return JsonResponse(
            {"error": "El monto debe ser mayor que 0."},
            status=400,
        )

    observaciones = data.get("observaciones", "").strip()

    # Usa el método en Cliente
    try:
        movimiento = cliente.registrar_movimiento_credito(
            tipo="ABONO",
            monto=monto,
            venta=None,
            observaciones=observaciones or "Abono registrado por API",
        )
    except Exception as e:
        # Devuelve el mensaje de error como JSON
        return JsonResponse(
            {"error": [str(e)]},
            status=400,
        )

    return JsonResponse(
        {
            "mensaje": "Abono registrado correctamente.",
            "cliente": {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "rut": cliente.rut,
                "saldo_actual": str(cliente.saldo_actual),
            },
            "movimiento": {
                "id": movimiento.id,
                "tipo": movimiento.tipo,
                "monto": str(movimiento.monto),
                "saldo_despues": str(movimiento.saldo_despues),
                "fecha": movimiento.fecha.isoformat(),
                "observaciones": movimiento.observaciones,
            },
        },
        status=201,
    )


# =========================
# 2) VER SALDO DE UN CLIENTE
# =========================
@csrf_exempt
@login_required
@user_passes_test(es_cajero_o_admin)
@require_GET
def ver_saldo(request):
    """
    Consulta el saldo y cupo de un cliente.

    """
    data = {
        "cliente_id": request.GET.get("cliente_id"),
        "rut": request.GET.get("rut"),
    }

    if not data["cliente_id"] and not data["rut"]:
        return JsonResponse(
            {"error": "Debe enviar 'cliente_id' o 'rut' como parámetro."},
            status=400,
        )

    cliente = _obtener_cliente(data)
    if cliente is None:
        return JsonResponse(
            {"error": "Cliente no encontrado."},
            status=404,
        )

    # cliente.saldo_actual o cliente.obtener_saldo_actual()
    saldo = cliente.saldo_actual
    cupo = cliente.cupo_maximo
    disponible = cupo - saldo

    return JsonResponse(
        {
            "cliente": {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "rut": cliente.rut,
                "tiene_credito": cliente.tiene_credito,
                "cupo_maximo": str(cupo),
                "saldo_actual": str(saldo),
                "disponible": str(disponible),
            }
        },
        status=200,
    )


# =========================
# 3) LISTAR MOVIMIENTOS DE CRÉDITO
# =========================
@csrf_exempt
@login_required
@user_passes_test(es_cajero_o_admin)
@require_GET
def listar_movimientos(request):
    """
    Lista los movimientos de crédito de un cliente.

    """
    data = {
        "cliente_id": request.GET.get("cliente_id"),
        "rut": request.GET.get("rut"),
    }

    if not data["cliente_id"] and not data["rut"]:
        return JsonResponse(
            {"error": "Debe enviar 'cliente_id' o 'rut' como parámetro."},
            status=400,
        )

    cliente = _obtener_cliente(data)
    if cliente is None:
        return JsonResponse(
            {"error": "Cliente no encontrado."},
            status=404,
        )

    # límite de resultados
    try:
        limit = int(request.GET.get("limit", 20))
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 100))  # entre 1 y 100

    movimientos_qs = cliente.movimientos_credito.order_by("-fecha", "-id")[:limit]

    movimientos = []
    for mov in movimientos_qs:
        movimientos.append(
            {
                "id": mov.id,
                "tipo": mov.tipo,
                "monto": str(mov.monto),
                "saldo_despues": str(mov.saldo_despues),
                "fecha": mov.fecha.isoformat(),
                "venta_id": mov.venta_id,
                "observaciones": mov.observaciones,
            }
        )

    return JsonResponse(
        {
            "cliente": {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "rut": cliente.rut,
            },
            "movimientos": movimientos,
        },
        status=200,
    )

@login_required
@user_passes_test(es_admin)
@require_GET

def clientes_con_deuda(request):
    """

    Lista los clientes con saldo_actual > 0, ordenados por deuda.
    """
    qs = Cliente.objects.filter(saldo_actual__gt=0).order_by("-saldo_actual")

    results = []
    for c in qs:
        disponible = c.cupo_maximo - c.saldo_actual
        results.append(
            {
                "id": c.id,
                "nombre": c.nombre,
                "rut": c.rut,
                "saldo_actual": str(c.saldo_actual),
                "cupo_maximo": str(c.cupo_maximo),
                "disponible": str(disponible),
            }
        )

    return JsonResponse(
        {
            "count": len(results),
            "results": results,
        }
    )
