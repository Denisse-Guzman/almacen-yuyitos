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
    Ajusta los campos según tu modelo real.
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



def _puede_ver_productos(user):
    """
    Permiso: puede ver productos si es Cajero, Bodeguero o Admin.
    """
    return es_cajero_o_admin(user) or es_bodeguero_o_admin(user)


@csrf_exempt
@login_required
@user_passes_test(_puede_ver_productos)
@require_GET
def listar_productos(request):
    """

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


@csrf_exempt
@login_required
@user_passes_test(_puede_ver_productos)
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

    return JsonResponse(
        _producto_a_dict(producto),
        status=200,
    )


@csrf_exempt
@login_required
@user_passes_test(_puede_ver_productos)
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

@csrf_exempt
@login_required
@user_passes_test(es_bodeguero_o_admin)
@require_POST
def crear_producto(request):
    """
    Crea un nuevo producto.
    
    POST /api/productos/crear/
    
    Body JSON:
    {
        "codigo_barras": "123456",
        "nombre": "Coca Cola 2.0 lt",
        "descripcion": "Bebida gaseosa",
        "categoria_nombre": "Bebidas",  // Ahora es nombre de categoría
        "precio_compra": "1000",
        "precio_venta": "1800",
        "stock_actual": 50,
        "stock_minimo": 10,
        "tiene_vencimiento": false,
        "fecha_vencimiento": null,
        "es_activo": true
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
        # Buscar o crear la categoría
        categoria, created = Categoria.objects.get_or_create(
            nombre=categoria_nombre,
            defaults={'esta_activa': True}
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
        fecha_vencimiento=data.get("fecha_vencimiento"),
        es_activo=bool(data.get("es_activo", True)),
    )

    return JsonResponse(
        {
            "mensaje": "Producto creado correctamente.",
            "producto": _producto_a_dict(producto),
        },
        status=201,
    )


@csrf_exempt
@login_required
@user_passes_test(es_bodeguero_o_admin)
@require_POST
def actualizar_producto(request, producto_id: int):
    """
    Actualiza un producto existente.
    
    POST /api/productos/<producto_id>/actualizar/
    
    Body JSON: (mismo formato que crear_producto)
    """
    try:
        producto = Producto.objects.get(pk=producto_id)
    except Producto.DoesNotExist:
        return JsonResponse(
            {"error": "Producto no encontrado."},
            status=404,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "JSON inválido en el cuerpo de la solicitud."},
            status=400,
        )

    # Actualizar nombre
    nombre = (data.get("nombre") or "").strip()
    if nombre:
        producto.nombre = nombre
    
    # Actualizar descripción
    if "descripcion" in data:
        producto.descripcion = data.get("descripcion", "")

    # Actualizar código de barras (validar que sea único)
    if "codigo_barras" in data:
        codigo_barras = (data.get("codigo_barras") or "").strip()
        if codigo_barras:
            # Verificar que no exista otro producto con ese código
            existe = Producto.objects.filter(codigo_barras=codigo_barras).exclude(pk=producto_id).exists()
            if existe:
                return JsonResponse(
                    {"error": "Ya existe otro producto con ese código de barras."},
                    status=400,
                )
            producto.codigo_barras = codigo_barras
        else:
            producto.codigo_barras = None

    # Actualizar precios
    if "precio_compra" in data:
        try:
            producto.precio_compra = Decimal(str(data.get("precio_compra")))
        except (InvalidOperation, TypeError):
            return JsonResponse(
                {"error": "El precio de compra debe ser un número válido."},
                status=400,
            )

    if "precio_venta" in data:
        try:
            precio_venta = Decimal(str(data.get("precio_venta")))
            if precio_venta <= 0:
                return JsonResponse(
                    {"error": "El precio de venta debe ser mayor que 0."},
                    status=400,
                )
            producto.precio_venta = precio_venta
        except (InvalidOperation, TypeError):
            return JsonResponse(
                {"error": "El precio de venta debe ser un número válido."},
                status=400,
            )

    # Actualizar stock
    if "stock_actual" in data:
        try:
            stock = int(data.get("stock_actual"))
            if stock < 0:
                return JsonResponse(
                    {"error": "El stock no puede ser negativo."},
                    status=400,
                )
            producto.stock_actual = stock
        except (ValueError, TypeError):
            return JsonResponse(
                {"error": "El stock debe ser un número entero."},
                status=400,
            )

    if "stock_minimo" in data:
        try:
            producto.stock_minimo = int(data.get("stock_minimo", 0))
        except (ValueError, TypeError):
            pass

    # Actualizar categoría por nombre
    if "categoria_nombre" in data:
        categoria_nombre = (data.get("categoria_nombre") or "").strip()
        if categoria_nombre:
            from inventario.models import Categoria
            # Buscar o crear la categoría
            categoria, created = Categoria.objects.get_or_create(
                nombre=categoria_nombre,
                defaults={'esta_activa': True}
            )
            producto.categoria = categoria
        else:
            producto.categoria = None

    # Actualizar vencimiento
    if "tiene_vencimiento" in data:
        producto.tiene_vencimiento = bool(data.get("tiene_vencimiento"))
    
    if "fecha_vencimiento" in data:
        producto.fecha_vencimiento = data.get("fecha_vencimiento")

    # Actualizar estado activo
    if "es_activo" in data:
        producto.es_activo = bool(data.get("es_activo"))

    producto.save()

    return JsonResponse(
        {
            "mensaje": "Producto actualizado correctamente.",
            "producto": _producto_a_dict(producto),
        },
        status=200,
    )


@csrf_exempt
@login_required
@user_passes_test(es_bodeguero_o_admin)
@require_POST
def eliminar_producto(request, producto_id: int):
    """
    Desactiva un producto (eliminación lógica).
    
    POST /api/productos/<producto_id>/eliminar/
    
    Body JSON:
    {
        "eliminar_permanente": false  // opcional, por defecto false
    }
    """
    try:
        producto = Producto.objects.get(pk=producto_id)
    except Producto.DoesNotExist:
        return JsonResponse(
            {"error": "Producto no encontrado."},
            status=404,
        )

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    eliminar_permanente = data.get("eliminar_permanente", False)

    if eliminar_permanente:
        # Eliminación física (solo si el admin lo permite)
        nombre_producto = producto.nombre
        producto.delete()
        return JsonResponse(
            {
                "mensaje": f"Producto '{nombre_producto}' eliminado permanentemente.",
            },
            status=200,
        )
    else:
        # Eliminación lógica (desactivar)
        producto.es_activo = False
        producto.save()
        return JsonResponse(
            {
                "mensaje": f"Producto '{producto.nombre}' desactivado correctamente.",
                "producto": _producto_a_dict(producto),
            },
            status=200,
        )

@login_required
@require_http_methods(["GET"])
def listar_categorias(request):
    """Listar todas las categorías activas"""
    try:
        from .models import Categoria
        
        categorias = Categoria.objects.filter(esta_activa=True).order_by('nombre')
        
        results = [
            {
                "id": cat.id,
                "nombre": cat.nombre,
                "descripcion": cat.descripcion,
                "esta_activa": cat.esta_activa
            }
            for cat in categorias
        ]
        
        return JsonResponse({
            "count": len(results),
            "results": results
        })
        
    except Exception as e:
        return JsonResponse(
            {"error": f"Error al listar categorías: {str(e)}"},
            status=500
        )