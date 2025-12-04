from decimal import Decimal
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from inventario.models import Producto, Categoria


class BaseApiProductosTestCase(TestCase):
    """
    Base para pruebas de la API de productos.

    - Crea un usuario admin (superuser) y hace login
    - Crea una categoría y un producto de prueba
    """

    def setUp(self):
        self.client = Client()
        User = get_user_model()

        # Usuario con permisos altos (debería pasar es_admin)
        self.user = User.objects.create_user(
            username="admin_productos",
            password="test12345",
            is_staff=True,
            is_superuser=True,
        )

        logged_in = self.client.login(
            username="admin_productos",
            password="test12345",
        )
        self.assertTrue(logged_in, "No se pudo hacer login en el cliente de tests")

        # Categoría y producto base
        self.categoria = Categoria.objects.create(nombre="Bebidas")

        self.producto = Producto.objects.create(
            nombre="Coca Cola 1L",
            categoria=self.categoria,
            precio_compra=Decimal("1000.00"),
            precio_venta=Decimal("1500.00"),
            stock_actual=10,
            stock_minimo=2,
            es_activo=True,
        )


# ============================================================
# LISTAR PRODUCTOS
# ============================================================

class ApiProductosListarTests(BaseApiProductosTestCase):
    def test_listar_productos_devuelve_200_y_lista_con_campos_basicos(self):
        """
        GET /api/productos/ debería:
        - responder 200
        - devolver una lista JSON
        - incluir al menos un producto con campos básicos
        """
        url = "/api/productos/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

        producto_json = data[0]
        # Campos básicos definidos en _producto_a_dict
        for campo in [
            "id",
            "nombre",
            "codigo",
            "categoria_id",
            "categoria_nombre",
            "precio_compra",
            "precio_venta",
            "stock_actual",
            "stock_minimo",
            "tiene_vencimiento",
            "fecha_vencimiento",
            "es_activo",
        ]:
            self.assertIn(campo, producto_json)

    def test_listar_productos_filtrado_por_nombre(self):
        """
        GET /api/productos/?q=... debería filtrar por nombre (icontains).
        """
        # Creamos un producto con un nombre distinto
        Producto.objects.create(
            nombre="Fanta Naranja 1L",
            categoria=self.categoria,
            precio_compra=Decimal("900.00"),
            precio_venta=Decimal("1400.00"),
            stock_actual=5,
            stock_minimo=1,
            es_activo=True,
        )

        url = "/api/productos/?q=coca"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

        # Todos los productos devueltos deberían tener "coca" en el nombre (case-insensitive)
        for p in data:
            self.assertIn("nombre", p)
            self.assertIn("coca", p["nombre"].lower())


# ============================================================
# DETALLE DE PRODUCTO
# ============================================================

class ApiProductosDetalleTests(BaseApiProductosTestCase):
    def test_detalle_producto_existente_devuelve_200_y_datos_correctos(self):
        """
        GET /api/productos/<id>/ con un producto existente debería:
        - responder 200
        - devolver un objeto con los datos del producto
        """
        url = f"/api/productos/{self.producto.id}/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["id"], self.producto.id)
        self.assertEqual(data["nombre"], self.producto.nombre)
        self.assertEqual(
            Decimal(data["precio_venta"]),
            self.producto.precio_venta,
        )

    def test_detalle_producto_inexistente_devuelve_404(self):
        """
        GET /api/productos/<id>/ con un ID que no existe
        debería responder 404.
        """
        url = "/api/productos/9999/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# ============================================================
# STOCK DE PRODUCTO
# ============================================================

class ApiProductosStockTests(BaseApiProductosTestCase):
    def test_stock_producto_existente_devuelve_200_y_datos(self):
        """
        GET /api/productos/<id>/stock/ debería:
        - responder 200
        - devolver id, nombre y stock_actual del producto
        """
        url = f"/api/productos/{self.producto.id}/stock/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["id"], self.producto.id)
        self.assertEqual(data["nombre"], self.producto.nombre)
        self.assertEqual(data["stock_actual"], self.producto.stock_actual)

    def test_stock_producto_inexistente_devuelve_404(self):
        """
        GET /api/productos/<id>/stock/ con un ID inexistente
        debería responder 404.
        """
        url = "/api/productos/9999/stock/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# ============================================================
# CREAR PRODUCTO
# ============================================================

class ApiProductosCrearTests(BaseApiProductosTestCase):
    def test_crear_producto_valido_devuelve_201_y_crea_producto(self):
        """
        POST /api/productos/crear/ con datos válidos debería:
        - responder 201
        - crear un nuevo Producto en BD
        - devolver los datos del producto creado
        """
        url = "/api/productos/crear/"
        productos_antes = Producto.objects.count()

        payload = {
            "nombre": "Galletas de Soda",
            "categoria_nombre": "Snacks",
            "precio_compra": "500.00",
            "precio_venta": "800.00",
            "stock_actual": 20,
            "stock_minimo": 5,
            "tiene_vencimiento": False,
            "es_activo": True,
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Producto.objects.count(), productos_antes + 1)

        data = response.json()
        self.assertIn("producto", data)
        prod_json = data["producto"]

        self.assertEqual(prod_json["nombre"], "Galletas de Soda")
        self.assertEqual(prod_json["categoria_nombre"], "Snacks")
        self.assertEqual(prod_json["precio_venta"], "800.00")

    def test_crear_producto_sin_nombre_devuelve_400(self):
        """
        POST /api/productos/crear/ sin 'nombre' debería:
        - responder 400
        - no crear un producto nuevo
        """
        url = "/api/productos/crear/"
        productos_antes = Producto.objects.count()

        payload = {
            # "nombre" faltante
            "categoria_nombre": "Snacks",
            "precio_compra": "500.00",
            "precio_venta": "800.00",
            "stock_actual": 20,
            "stock_minimo": 5,
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Producto.objects.count(), productos_antes)


# ============================================================
# ACTUALIZAR PRODUCTO
# ============================================================

class ApiProductosActualizarTests(BaseApiProductosTestCase):
    def test_actualizar_producto_valido_modifica_campos(self):
        """
        POST /api/productos/<id>/actualizar/ con datos válidos debería:
        - responder 200
        - modificar los campos del producto en BD
        """
        url = f"/api/productos/{self.producto.id}/actualizar/"

        payload = {
            "nombre": "Coca Cola 1.5L",
            "precio_venta": "1800.00",
            "stock_actual": 25,
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, "Coca Cola 1.5L")
        self.assertEqual(self.producto.precio_venta, Decimal("1800.00"))
        self.assertEqual(self.producto.stock_actual, 25)

    def test_actualizar_producto_con_precio_venta_invalido_devuelve_400(self):
        """
        POST /api/productos/<id>/actualizar/ con precio_venta no numérico
        debería responder 400 y no cambiar el precio en BD.
        """
        url = f"/api/productos/{self.producto.id}/actualizar/"

        precio_original = self.producto.precio_venta

        payload = {
            "precio_venta": "no-numero",
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_venta, precio_original)

    def test_actualizar_producto_inexistente_devuelve_404(self):
        """
        POST /api/productos/9999/actualizar/ con un ID que no existe
        debería responder 404.
        """
        url = "/api/productos/9999/actualizar/"

        payload = {
            "nombre": "Producto Fantasma",
            "precio_venta": "1000.00",
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
