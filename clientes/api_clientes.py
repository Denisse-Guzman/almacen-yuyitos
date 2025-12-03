import json
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import Cliente

from django.contrib.auth.decorators import login_required, user_passes_test
from cuentas.permisos import es_cajero_o_admin

@csrf_exempt
@login_required
@user_passes_test(es_cajero_o_admin)
@require_GET
def lista_clientes(request):
    """

    Lista clientes activos, con búsqueda opcional por nombre, RUT o teléfono.
    """
    q = request.GET.get("q", "").strip()
    try:
        limit = int(request.GET.get("limit", 20))
    except ValueError:
        limit = 20

    try:
        offset = int(request.GET.get("offset", 0))
    except ValueError:
        offset = 0

    qs = Cliente.objects.filter(es_activo=True)

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(rut__icontains=q)
            | Q(telefono__icontains=q)
        )

    total = qs.count()
    clientes_data = []

    for c in qs.order_by("nombre")[offset:offset + limit]:
        clientes_data.append(
            {
                "id": c.id,
                "nombre": c.nombre,
                "rut": c.rut,
                "telefono": c.telefono,
                "tiene_credito": c.tiene_credito,
                "cupo_maximo": str(c.cupo_maximo),
                "saldo_actual": str(c.saldo_actual),
                "es_activo": c.es_activo,
            }
        )

    return JsonResponse(
        {
            "count": total,
            "results": clientes_data,
        }
    )


@require_GET
def detalle_cliente(request, cliente_id):
    """

    Devuelve el detalle de un cliente.
    """
    try:
        c = Cliente.objects.get(pk=cliente_id)
    except Cliente.DoesNotExist:
        return JsonResponse(
            {"error": "Cliente no encontrado."},
            status=404,
        )

    disponible = Decimal("0.00")
    if c.tiene_credito:
        try:
            disponible = c.cupo_maximo - c.saldo_actual
        except Exception:
            disponible = Decimal("0.00")

    data = {
        "id": c.id,
        "nombre": c.nombre,
        "rut": c.rut,
        "telefono": c.telefono,
        "email": c.email,
        "direccion": c.direccion,
        "tiene_credito": c.tiene_credito,
        "cupo_maximo": str(c.cupo_maximo),
        "saldo_actual": str(c.saldo_actual),
        "disponible": str(disponible),
        "es_activo": c.es_activo,
        "creado_en": c.creado_en.isoformat() if c.creado_en else None,
        "actualizado_en": c.actualizado_en.isoformat() if c.actualizado_en else None,
    }

    return JsonResponse({"cliente": data})


@csrf_exempt
@require_POST
def crear_cliente(request):
    """

    Body JSON:
    {
        "nombre": "Juan Pérez",
        "rut": "12.345.678-9",
        "telefono": "999999999",
        "email": "correo@ejemplo.cl",
        "direccion": "Dirección X",
        "tiene_credito": true,
        "cupo_maximo": "200000"
    }
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "JSON inválido en el cuerpo de la solicitud."},
            status=400,
        )

    nombre = (data.get("nombre") or "").strip()
    rut = (data.get("rut") or "").strip()

    if not nombre:
        return JsonResponse(
            {"error": "El campo 'nombre' es obligatorio."},
            status=400,
        )

    if not rut:
        return JsonResponse(
            {"error": "El campo 'rut' es obligatorio."},
            status=400,
        )

    # Validar que el RUT no esté repetido
    if Cliente.objects.filter(rut=rut).exists():
        return JsonResponse(
            {"error": "Ya existe un cliente con ese RUT."},
            status=400,
        )

    telefono = (data.get("telefono") or "").strip()
    email = (data.get("email") or "").strip()
    direccion = (data.get("direccion") or "").strip()

    tiene_credito = bool(data.get("tiene_credito", False))

    cupo_raw = data.get("cupo_maximo", "0")
    try:
        cupo_maximo = Decimal(str(cupo_raw))
    except (InvalidOperation, TypeError):
        return JsonResponse(
            {"error": "El campo 'cupo_maximo' debe ser un número válido."},
            status=400,
        )

    if cupo_maximo < 0:
        return JsonResponse(
            {"error": "El cupo máximo no puede ser negativo."},
            status=400,
        )

    cliente = Cliente.objects.create(
        nombre=nombre,
        rut=rut,
        telefono=telefono,
        email=email,
        direccion=direccion,
        tiene_credito=tiene_credito,
        cupo_maximo=cupo_maximo,
        # saldo_actual queda 0 por defecto
        es_activo=True,
    )

    disponible = cupo_maximo  # todavía no tiene deuda
    data_resp = {
        "id": cliente.id,
        "nombre": cliente.nombre,
        "rut": cliente.rut,
        "telefono": cliente.telefono,
        "email": cliente.email,
        "direccion": cliente.direccion,
        "tiene_credito": cliente.tiene_credito,
        "cupo_maximo": str(cliente.cupo_maximo),
        "saldo_actual": str(cliente.saldo_actual),
        "disponible": str(disponible),
        "es_activo": cliente.es_activo,
    }

    return JsonResponse(
        {
            "mensaje": "Cliente creado correctamente.",
            "cliente": data_resp,
        },
        status=201,
    )

