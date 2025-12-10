import json
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError

from clientes.models import Cliente
from inventario.models import Producto
from .models import Venta, DetalleVenta

from django.contrib.auth.decorators import login_required
from cuentas.permisos import es_cajero_o_admin

from django.db.models import Sum, Count
from django.utils import timezone


def _obtener_cliente(data):
    """
    Intenta obtener un cliente por cliente_id o rut.
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


@csrf_exempt
@login_required
@require_POST
def crear_venta(request):
    """
    Crea una venta (contado o crédito) con sus detalles.

    JSON esperado:

    {
        "cliente_id": 1,              // opcional (o "rut": "12.345.678-9")
        "nombre_cliente_libre": "Juan Pérez",  // opcional, solo si no hay cliente
        "es_credito": true,           // o false
        "observaciones": "Texto",     // opcional
        "detalles": [
            {
                "producto_id": 3,
                "cantidad": 2,
                "precio_unitario": "1500.00"   // opcional, si no se manda usa precio_venta
            },
            ...
        ]
    }
    """
    # ✅ Validar rol aquí para evitar redirect HTML
    if not es_cajero_o_admin(request.user):
        return JsonResponse(
            {"error": "No tienes permisos para registrar ventas."},
            status=403,
        )

    # 1) Parsear JSON
    try:
        raw_body = request.body
        encoding = request.encoding or "utf-8"
        try:
            body_str = raw_body.decode(encoding)
        except UnicodeDecodeError:
            body_str = raw_body.decode("latin-1")

        data = json.loads(body_str)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    # 2) Cliente (opcional, pero obligatorio si es crédito)
    cliente = _obtener_cliente(data)
    nombre_cliente_libre = (data.get("nombre_cliente_libre") or "").strip()

    es_credito = bool(data.get("es_credito", False))
    observaciones = (data.get("observaciones") or "").strip()

    if es_credito:
        # Para venta a crédito, el cliente es obligatorio
        if cliente is None:
            return JsonResponse(
                {
                    "error": (
                        "Para una venta a crédito debes indicar un cliente "
                        "(cliente_id o rut)."
                    )
                },
                status=400,
            )
        if not cliente.tiene_credito or not cliente.es_activo:
            return JsonResponse(
                {"error": "El cliente no tiene crédito habilitado o está inactivo."},
                status=400,
            )

    # 3) Detalles
    detalles_data = data.get("detalles")
    if not isinstance(detalles_data, list) or len(detalles_data) == 0:
        return JsonResponse(
            {"error": "La venta debe incluir al menos un detalle de producto."},
            status=400,
        )

    detalles_preparados = []
    total_estimado = Decimal("0.00")

    # 4) Validar y preparar cada detalle
    for idx, det in enumerate(detalles_data, start=1):
        producto_id = det.get("producto_id")
        cantidad_raw = det.get("cantidad", 1)
        precio_unit_raw = det.get("precio_unitario")

        if producto_id is None:
            return JsonResponse(
                {"error": f"En el detalle #{idx} falta 'producto_id'."},
                status=400,
            )

        try:
            producto = Producto.objects.get(pk=producto_id)
        except Producto.DoesNotExist:
            return JsonResponse(
                {"error": f"Producto con id {producto_id} no existe (detalle #{idx})."},
                status=404,
            )

        # cantidad
        try:
            cantidad = int(cantidad_raw)
        except (TypeError, ValueError):
            return JsonResponse(
                {"error": f"La 'cantidad' debe ser un entero válido (detalle #{idx})."},
                status=400,
            )

        if cantidad <= 0:
            return JsonResponse(
                {"error": f"La 'cantidad' debe ser mayor que 0 (detalle #{idx})."},
                status=400,
            )

        # precio_unitario
        if precio_unit_raw is not None:
            try:
                precio_unitario = Decimal(str(precio_unit_raw))
            except (InvalidOperation, TypeError):
                return JsonResponse(
                    {
                        "error": (
                            f"El 'precio_unitario' debe ser un número válido "
                            f"(detalle #{idx})."
                        )
                    },
                    status=400,
                )
        else:
            # usamos el precio_venta del producto
            precio_unitario = producto.precio_venta

        if precio_unitario <= 0:
            return JsonResponse(
                {"error": f"El precio_unitario debe ser mayor que 0 (detalle #{idx})."},
                status=400,
            )

        # Verificar stock disponible
        if not producto.hay_stock(cantidad):
            return JsonResponse(
                {
                    "error": (
                        f"No hay stock suficiente de '{producto.nombre}' "
                        f"para vender {cantidad} unidades (detalle #{idx})."
                    )
                },
                status=400,
            )

        subtotal = precio_unitario * cantidad
        total_estimado += subtotal

        detalles_preparados.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
            }
        )

    # 5) Si es crédito, validar cupo antes de grabar nada
    if es_credito and cliente:
        if not cliente.puede_comprar_a_credito(total_estimado):
            return JsonResponse(
                {
                    "error": (
                        "El total de la venta excede el cupo de crédito disponible "
                        "para este cliente."
                    )
                },
                status=400,
            )

    # 6) Crear la Venta
    venta = Venta.objects.create(
        cliente=cliente,
        nombre_cliente_libre=nombre_cliente_libre if cliente is None else "",
        es_credito=es_credito,
        observaciones=observaciones,
        total=Decimal("0.00"),  # se recalcula luego con los detalles
    )

    # 7) Crear detalles y ajustar stock/total
    try:
        for det in detalles_preparados:
            DetalleVenta.objects.create(
                venta=venta,
                producto=det["producto"],
                cantidad=det["cantidad"],
                precio_unitario=det["precio_unitario"],
            )

        # Recalcular total de la venta
        venta.refresh_from_db()
        venta.actualizar_total()

    except ValidationError as e:
        # Si algo falla (ej: stock), borramos la venta y devolvemos error
        venta.delete()
        return JsonResponse(
            {"error": e.messages},
            status=400,
        )

    # 8) Si es crédito, registrar movimiento COMPRA
    movimiento = None
    if es_credito and cliente:
        movimiento = cliente.registrar_movimiento_credito(
            tipo="COMPRA",
            monto=venta.total,
            venta=venta,
            observaciones=f"Compra a crédito (API) Venta #{venta.id}",
        )

    # 9) Armar respuesta
    detalles_resp = []
    for det in venta.detalles.select_related("producto"):
        detalles_resp.append(
            {
                "id": det.id,
                "producto_id": det.producto.id,
                "producto_nombre": det.producto.nombre,
                "cantidad": det.cantidad,
                "precio_unitario": str(det.precio_unitario),
                "subtotal": str(det.subtotal),
            }
        )

    resp = {
        "mensaje": "Venta creada correctamente.",
        "venta": {
            "id": venta.id,
            "fecha": venta.fecha.isoformat(),
            "cliente_id": venta.cliente.id if venta.cliente else None,
            "cliente_nombre": (
                venta.cliente.nombre
                if venta.cliente
                else (venta.nombre_cliente_libre or "")
            ),
            "es_credito": venta.es_credito,
            "total": str(venta.total),
            "observaciones": venta.observaciones,
        },
        "detalles": detalles_resp,
    }

    if movimiento:
        resp["movimiento_credito"] = {
            "id": movimiento.id,
            "tipo": movimiento.tipo,
            "monto": str(movimiento.monto),
            "saldo_despues": str(movimiento.saldo_despues),
            "fecha": movimiento.fecha.isoformat(),
            "observaciones": movimiento.observaciones,
        }

    return JsonResponse(resp, status=201)


@csrf_exempt
@login_required
@require_GET
def estadisticas_hoy(request):
    """
    Retorna estadísticas de ventas del día actual:
    - Total de ventas en dinero
    - Cantidad de transacciones
    Solo para Cajero o Admin.
    """
    if not es_cajero_o_admin(request.user):
        return JsonResponse(
            {"error": "No tienes permisos para ver estas estadísticas."},
            status=403,
        )

    # Obtener fecha de hoy (sin hora)
    hoy = timezone.now().date()

    # Consultar ventas del día
    ventas_hoy = Venta.objects.filter(
        fecha__date=hoy
    ).aggregate(
        total_ventas=Sum('total'),
        cantidad_ventas=Count('id')
    )

    # Retornar datos (manejar None si no hay ventas)
    return JsonResponse({
        'total_ventas': float(ventas_hoy['total_ventas'] or 0),
        'cantidad_ventas': ventas_hoy['cantidad_ventas'] or 0,
        'fecha': hoy.isoformat()
    })
