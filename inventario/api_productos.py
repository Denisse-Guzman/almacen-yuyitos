from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Producto
from cuentas.permisos import es_cajero_o_admin, es_bodeguero_o_admin

from django.views.decorators.http import require_POST
import json
from decimal import Decimal, InvalidOperation


def _producto_a_dict(producto: Producto):
    """
    Serializa un producto a dict simple para JSON.
    """
    return {
        "id": producto.id,
        "codigo_barras": producto.codigo_barras or "",
        "nombre": producto.nombre,
        "descripcion": producto.descripcion or "",
        "categoria": producto.categoria.nombre if producto.categoria else "Sin categoría",
        "categoria_id": producto.categoria.id if producto.categoria else None,
        "precio_compra": str(producto.precio_compra),
        "precio_venta": str(producto.precio_venta),
        "stock_actual": producto.stock_actual,
        "stock_minimo": producto.stock_minimo,
        "tiene_vencimiento": producto.tiene_vencimiento,
        "fecha_vencimiento": str(producto.fecha_vencimiento) if producto.fecha_vencimiento else None,
        "es_activo": producto.es_activo,
        "activo": producto.es_activo,
    }


# =========================
# LISTAR / CREAR PRODUCTOS
# =========================
@csrf_exempt
@login_required
@require_http_methods(["GET", "POST"])
def productos_collection(request):
    """
    GET  /api/productos/  -> lista productos
    POST /api/productos/  -> crea producto (solo bodeguero o admin)
    """
    # ---------- GET: listar ----------
    if request.method == "GET":
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

    # ---------- POST: crear ----------
    # Solo bodeguero o admin crean
    if not es_bodeguero_o_admin(request.user):
        return JsonResponse(
            {"error": "No tienes permisos para crear productos."},
            status=403,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "JSON inválido en el cuerpo de la solicitud."},
            status=400,
        )

    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return JsonResponse(
            {"error": "El campo 'nombre' es obligatorio."},
            status=400,
        )

    # Validar precios
    try:
        precio_compra = Decimal(str(data.get("precio_compra", 0)))
        precio_venta = Decimal(str(data.get("precio_venta", 0)))
    except (InvalidOperation, TypeError):
        return JsonResponse(
            {"error": "Los precios deben ser números válidos."},
            status=400,
        )

    if precio_venta <= 0:
        return JsonResponse(
            {"error": "El precio de venta debe ser mayor que 0."},
            status=400,
        )

    # Validar stock
    try:
        stock_actual = int(data.get("stock_actual", 0))
        stock_minimo = int(data.get("stock_minimo", 0))
    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "El stock debe ser un número entero."},
            status=400,
        )

    if stock_actual < 0:
        return JsonResponse(
            {"error": "El stock no puede ser negativo."},
            status=400,
        )

    # Validar código de barras único
    codigo_barras = (data.get("codigo_barras") or "").strip()
    if codigo_barras and Producto.objects.filter(codigo_barras=codigo_barras).exists():
        return JsonResponse(
            {"error": "Ya existe un producto con ese código de barras."},
            status=400,
        )

    # Manejar categoría por nombre (crear si no existe)
    from inventario.models import Categoria

    categoria_nombre = (data.get("categoria_nombre") or "").strip()
    categoria = None
    if categoria_nombre:
        categoria, _ = Categoria.objects.get_or_create(
            nombre=categoria_nombre,
            defaults={"esta_activa": True},
        )

    producto = Producto.objects.create(
        codigo_barras=codigo_barras if codigo_barras else None,
        nombre=nombre,
        descripcion=data.get("descripcion", ""),
        categoria=categoria,
        precio_compra=precio_compra,
        precio_venta=precio_venta,
        stock_actual=stock_actual,
        stock_minimo=stock_minimo,
        tiene_vencimiento=bool(data.get("tiene_vencimiento", False)),
        fecha_vencimiento=data.get("fecha_vencimiento") or None,
        es_activo=True,  # siempre activo al crear
    )

    return JsonResponse(
        {
            "mensaje": "Producto creado correctamente.",
            "producto": _producto_a_dict(producto),
        },
        status=201,
    )


# =========================
# DETALLE / STOCK
# =========================
@csrf_exempt
@login_required
@require_GET
def detalle_producto(request, producto_id: int):
    """
    Devuelve la info de un producto específico.
    """
    try:
        producto = Producto.objects.get(pk=producto_id)
    except Producto.DoesNotExist:
        return JsonResponse(
            {"error": "Producto no encontrado."},
            status=404,
        )

    return JsonResponse(_producto_a_dict(producto), status=200)


@csrf_exempt
@login_required
@require_GET
def stock_producto(request, producto_id: int):
    """
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


# =========================
# CATEGORÍAS
# =========================
@login_required
@require_http_methods(["GET"])
def listar_categorias(request):
    """Listar todas las categorías activas"""
    try:
        from .models import Categoria

        categorias = Categoria.objects.filter(esta_activa=True).order_by("nombre")

        results = [
            {
                "id": cat.id,
                "nombre": cat.nombre,
                "descripcion": cat.descripcion,
                "esta_activa": cat.esta_activa,
            }
            for cat in categorias
        ]

        return JsonResponse(
            {
                "count": len(results),
                "results": results,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"error": f"Error al listar categorías: {str(e)}"},
            status=500,
        )
