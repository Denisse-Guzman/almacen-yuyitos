import json
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Proveedor, OrdenCompra, DetalleOrdenCompra
from inventario.models import Producto

from django.contrib.auth.decorators import login_required, user_passes_test
from cuentas.permisos import es_bodeguero_o_admin

@csrf_exempt
@login_required
@user_passes_test(es_bodeguero_o_admin)
@require_POST
def ingreso_mercaderia(request):
    """
    POST /api/proveedores/ingreso-mercaderia/

    JSON esperado:

    {
        "proveedor_id": 1,                // opcional
        "nombre_proveedor_libre": "XXX",  // opcional si hay proveedor_id
        "observaciones": "Texto opcional",
        "detalles": [
            {
                "producto_id": 1,
                "cantidad": 10,
                "costo_unitario": "1000.00"
            },
            ...
        ]
    }
    """
    # 1) Parsear JSON
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "JSON inválido en el cuerpo de la solicitud."},
            status=400,
        )

    proveedor = None
    proveedor_id = data.get("proveedor_id")
    nombre_proveedor_libre = (data.get("nombre_proveedor_libre") or "").strip()
    observaciones = (data.get("observaciones") or "").strip()

    # 2) Proveedor
    if proveedor_id is not None:
        try:
            proveedor = Proveedor.objects.get(pk=proveedor_id)
        except Proveedor.DoesNotExist:
            return JsonResponse(
                {"error": f"Proveedor con id {proveedor_id} no existe."},
                status=404,
            )

    if proveedor is None and not nombre_proveedor_libre:
        return JsonResponse(
            {
                "error": (
                    "Debe indicar 'proveedor_id' válido o 'nombre_proveedor_libre'."
                )
            },
            status=400,
        )

    # 3) Detalles
    detalles_data = data.get("detalles")
    if not isinstance(detalles_data, list) or len(detalles_data) == 0:
        return JsonResponse(
            {"error": "Debe incluir al menos un detalle de producto."},
            status=400,
        )

    detalles_preparados = []

    for idx, det in enumerate(detalles_data, start=1):
        producto_id = det.get("producto_id")
        cantidad_raw = det.get("cantidad")
        costo_unit_raw = det.get("costo_unitario")

        if producto_id is None:
            return JsonResponse(
                {"error": f"En el detalle #{idx} falta 'producto_id'."},
                status=400,
            )

        try:
            producto = Producto.objects.get(pk=producto_id)
        except Producto.DoesNotExist:
            return JsonResponse(
                {
                    "error": (
                        f"Producto con id {producto_id} no existe (detalle #{idx})."
                    )
                },
                status=404,
            )

        # cantidad
        try:
            cantidad = int(cantidad_raw)
        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "error": (
                        f"La 'cantidad' debe ser un entero válido (detalle #{idx})."
                    )
                },
                status=400,
            )

        if cantidad <= 0:
            return JsonResponse(
                {"error": f"La 'cantidad' debe ser mayor que 0 (detalle #{idx})."},
                status=400,
            )

        # costo_unitario
        if costo_unit_raw is None:
            return JsonResponse(
                {
                    "error": (
                        f"El campo 'costo_unitario' es obligatorio (detalle #{idx})."
                    )
                },
                status=400,
            )

        try:
            costo_unitario = Decimal(str(costo_unit_raw))
        except (InvalidOperation, TypeError):
            return JsonResponse(
                {
                    "error": (
                        f"El 'costo_unitario' debe ser un número válido "
                        f"(detalle #{idx})."
                    )
                },
                status=400,
            )

        if costo_unitario <= 0:
            return JsonResponse(
                {
                    "error": (
                        f"El 'costo_unitario' debe ser mayor que 0 (detalle #{idx})."
                    )
                },
                status=400,
            )

        detalles_preparados.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "costo_unitario": costo_unitario,
            }
        )

    # 4) Crear la Orden de Compra
    oc = OrdenCompra.objects.create(
        proveedor=proveedor,
        nombre_proveedor_libre=nombre_proveedor_libre if proveedor is None else "",
        observaciones=observaciones,
        total=0,
    )

    # 5) Crear detalles y aumentar stock
    for det in detalles_preparados:
        DetalleOrdenCompra.objects.create(
            orden=oc,
            producto=det["producto"],
            cantidad=det["cantidad"],
            costo_unitario=det["costo_unitario"],
        )
        # Aumentar stock del producto
        # Asumimos que Producto tiene método aumentar_stock(cantidad)
        det["producto"].aumentar_stock(det["cantidad"])

    # 6) Recalcular total de la orden
    oc.recalcular_total()

    # 7) Armar respuesta
    detalles_resp = []
    for det in oc.detalles.select_related("producto"):
        detalles_resp.append(
            {
                "id": det.id,
                "producto_id": det.producto.id,
                "producto_nombre": det.producto.nombre,
                "cantidad": det.cantidad,
                "costo_unitario": str(det.costo_unitario),
                "subtotal": str(det.subtotal),
            }
        )

    resp = {
        "mensaje": "Ingreso de mercadería registrado correctamente.",
        "orden_compra": {
            "id": oc.id,
            "fecha": oc.fecha.isoformat(),
            "proveedor_id": oc.proveedor.id if oc.proveedor else None,
            "proveedor_nombre": (
                oc.proveedor.nombre
                if oc.proveedor
                else (oc.nombre_proveedor_libre or "")
            ),
            "total": str(oc.total),
            "observaciones": oc.observaciones,
        },
        "detalles": detalles_resp,
    }

    return JsonResponse(resp, status=201)
