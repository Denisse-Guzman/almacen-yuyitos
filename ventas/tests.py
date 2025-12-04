from decimal import Decimal
import json
from datetime import timedelta


from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.contrib.auth import get_user_model
from django.utils import timezone

from clientes.models import Cliente
from .models import Venta, DetalleVenta
from inventario.models import Producto
from ventas.models import Venta

class BaseVentaTestCase(TestCase):
    def setUp(self):
        """
        Cliente base para pruebas de ventas.
        """
        self.cliente = Cliente.objects.create(
            nombre="Cliente Ventas",
            rut="44.444.444-4",
            tiene_credito=True,
            es_activo=True,
            cupo_maximo=Decimal("100000.00"),
            saldo_actual=Decimal("0.00"),
        )

class VentaCleanTests(BaseVentaTestCase):
    def test_venta_contado_con_cliente_registrado_valida_ok(self):
        """
        Venta al contado (es_credito=False) con cliente registrado
        y sin nombre_cliente_libre debe validar sin errores.
        """
        venta = Venta(
            cliente=self.cliente,
            nombre_cliente_libre="",
            es_credito=False,
            total=Decimal("10000.00"),
        )

        # full_clean() dispara el método clean() del modelo
        venta.full_clean()  # no debería lanzar excepción
    def test_venta_contado_con_nombre_libre_sin_cliente_valida_ok(self):
        """
        Venta al contado sin cliente pero con nombre_cliente_libre
        debe ser válida.
        """
        venta = Venta(
            cliente=None,
            nombre_cliente_libre="Cliente Libre Ventas",
            es_credito=False,
            total=Decimal("5000.00"),
        )

        venta.full_clean()  # no debería lanzar excepción
    def test_venta_contado_sin_cliente_ni_nombre_da_error(self):
        """
        Venta al contado sin cliente y sin nombre_cliente_libre
        debe lanzar ValidationError en 'cliente'.
        """
        venta = Venta(
            cliente=None,
            nombre_cliente_libre="",
            es_credito=False,
            total=Decimal("5000.00"),
        )

        with self.assertRaises(ValidationError) as ctx:
            venta.full_clean()

        errors = ctx.exception.error_dict
        self.assertIn("cliente", errors)
    def test_venta_credito_sin_cliente_da_error(self):
        """
        Venta a crédito sin cliente debe lanzar ValidationError
        en 'cliente'.
        """
        venta = Venta(
            cliente=None,
            nombre_cliente_libre="",
            es_credito=True,
            total=Decimal("20000.00"),
        )

        with self.assertRaises(ValidationError) as ctx:
            venta.full_clean()

        errors = ctx.exception.error_dict
        self.assertIn("cliente", errors)
    def test_venta_credito_con_nombre_libre_da_error(self):
        """
        Venta a crédito no debe permitir nombre_cliente_libre:
        solo clientes registrados.
        """
        venta = Venta(
            cliente=self.cliente,
            nombre_cliente_libre="No deberia ir",
            es_credito=True,
            total=Decimal("30000.00"),
        )

        with self.assertRaises(ValidationError) as ctx:
            venta.full_clean()

        errors = ctx.exception.error_dict
        self.assertIn("nombre_cliente_libre", errors)

class BaseApiVentasTestCase(TestCase):
    """
    Clase base para pruebas de la API de ventas.

    Prepara:
    - un usuario tipo cajero/admin (pasa login_required + user_passes_test)
    - un Cliente para asociar a ventas
    - opcionalmente un Producto (si falla la creación, algunos tests se marcarán como 'skipped')
    """

    def setUp(self):
        # Cliente HTTP de Django
        self.client = Client()

        # Usuario tipo "cajero/admin"
        self.user = User.objects.create_user(
            username="cajero_api",
            email="cajero@example.com",
            password="cajero123",
        )
class BaseApiVentasTestCase(TestCase):
    """
    Clase base para pruebas de la API de ventas.

    Prepara:
    - un usuario tipo cajero/admin (pasa login_required + user_passes_test)
    - un Cliente para asociar a ventas
    - un Producto de prueba con los campos obligatorios
    """

    def setUp(self):
        # Cliente HTTP de Django
        self.client = Client()

        # Usuario tipo "cajero/admin"
        self.user = User.objects.create_user(
            username="cajero_api",
            email="cajero@example.com",
            password="cajero123",
        )

        # Creamos (o reutilizamos) los grupos que usa es_cajero_o_admin
        grupo_cajero, _ = Group.objects.get_or_create(name="Cajero")
        grupo_admin, _ = Group.objects.get_or_create(name="Admin")

        # Metemos al usuario en al menos uno de esos grupos
        self.user.groups.add(grupo_cajero)   # o grupo_admin, como prefieras
        self.user.save()

        # Hacemos login con ese usuario
        logged_in = self.client.login(
            username="cajero_api", password="cajero123"
        )
        self.assertTrue(logged_in)

        # Cliente asociado a las ventas de prueba
        self.cliente = Cliente.objects.create(
            nombre="Cliente API Ventas",
            rut="66.666.666-6",
            tiene_credito=True,
            es_activo=True,
            cupo_maximo=Decimal("50000.00"),
            saldo_actual=Decimal("0.00"),
        )

        #  solo UNA creación de Producto, con todos los campos obligatorios
        self.producto = Producto.objects.create(
            nombre="Producto API Ventas",
            precio_compra=Decimal("1000.00"),
            precio_venta=Decimal("1500.00"),
        )


class ApiVentasCrearTests(BaseApiVentasTestCase):
    """
    Plan de pruebas para el endpoint:
    POST /api/ventas/crear/
    """
    def test_crear_venta_credito_valida_devuelve_201_y_actualiza_saldo_cliente(self):
        """
        Venta a CRÉDITO válida:

        - es_credito=True
        - cliente con cupo suficiente
        - debe devolver 201
        - debe crear una Venta con es_credito=True
        - debe aumentar el saldo_actual del cliente en el total de la venta
        """
        if self.producto is None:
            self.skipTest(
                "No se pudo crear Producto de prueba. "
                "Ajustar campos de Producto según el modelo real para habilitar este test."
            )

        # Nos aseguramos de que el cliente tenga harto cupo disponible
        self.cliente.saldo_actual = Decimal("0.00")
        self.cliente.cupo_maximo = Decimal("100000.00")
        self.cliente.save()

        saldo_inicial = self.cliente.saldo_actual
        ventas_antes = Venta.objects.count()

        url = "/api/ventas/crear/"

        # 2 unidades a 1500 => total esperado 3000
        payload = {
            "es_credito": True,
            "cliente_id": self.cliente.id,
            "detalles": [
                {
                    "producto_id": self.producto.id,
                    "cantidad": 2,
                    "precio_unitario": "1500.00",
                }
            ],
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Desde el plan de pruebas: esperamos 201
        self.assertEqual(response.status_code, 201)

        # Se debe haber creado exactamente una venta nueva
        self.assertEqual(Venta.objects.count(), ventas_antes + 1)

        # Tomamos la última venta creada
        venta = Venta.objects.latest("id")
        self.assertTrue(venta.es_credito)
        self.assertEqual(venta.cliente, self.cliente)

        # El total de la venta debería ser 3000 (2 x 1500)
        total_esperado = Decimal("3000.00")
        self.assertEqual(venta.total, total_esperado)

        # El saldo del cliente debe haber aumentado en ese total
        self.cliente.refresh_from_db()
        saldo_esperado = saldo_inicial + total_esperado
        self.assertEqual(self.cliente.saldo_actual, saldo_esperado)

    def test_crear_venta_credito_sin_cupo_suficiente_devuelve_400_y_no_crea_venta(self):
        """
        Venta a CRÉDITO cuando el cliente NO tiene cupo suficiente:

        - es_credito=True
        - saldo_actual cercano al cupo_maximo
        - el total de la venta excede el cupo
        - debe devolver 400
        - NO debe crear una Venta
        - NO debe modificar el saldo del cliente
        """
        if self.producto is None:
            self.skipTest(
                "No se pudo crear Producto de prueba. "
                "Ajustar campos de Producto según el modelo real para habilitar este test."
            )

        # Configuramos al cliente casi sin cupo
        self.cliente.cupo_maximo = Decimal("30000.00")
        self.cliente.saldo_actual = Decimal("29000.00")  # solo le quedan 1000
        self.cliente.save()

        saldo_inicial = self.cliente.saldo_actual
        ventas_antes = Venta.objects.count()

        url = "/api/ventas/crear/"

        # Intentamos una compra de 2 x 1500 => 3000 (excede el cupo disponible de 1000)
        payload = {
            "es_credito": True,
            "cliente_id": self.cliente.id,
            "detalles": [
                {
                    "producto_id": self.producto.id,
                    "cantidad": 2,
                    "precio_unitario": "1500.00",
                }
            ],
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Desde el plan de pruebas, esperamos 400 Bad Request
        self.assertEqual(response.status_code, 400)

        # No debe haberse creado una nueva venta
        self.assertEqual(Venta.objects.count(), ventas_antes)

        # El saldo del cliente NO debe cambiar
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, saldo_inicial)

    def test_crear_venta_contado_valida_devuelve_201_y_crea_venta(self):
        """
        Caso feliz (plan de pruebas):

        - Venta al contado (es_credito=False)
        - Con cliente registrado y un detalle válido
        - Debe devolver 201 y crear una Venta en BD.

        Nota: si no podemos crear un Producto de prueba, el test se marca como 'skipped'.
        """
        if self.producto is None:
            self.skipTest(
                "No se pudo crear Producto de prueba. "
                "Ajustar campos de Producto según el modelo real para habilitar este test."
            )

        url = "/api/ventas/crear/"
        ventas_antes = Venta.objects.count()

        payload = {
            "es_credito": False,
            "cliente_id": self.cliente.id,
            "detalles": [
                {
                    "producto_id": self.producto.id,
                    "cantidad": 2,
                    "precio_unitario": "1000.00",
                }
            ],
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Según el diseño del plan de pruebas, esperamos 201 (Created)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Venta.objects.count(), ventas_antes + 1)

    def test_crear_venta_sin_detalles_devuelve_400(self):
        """
        Si se envía una venta sin lista de detalles o con lista vacía,
        la API debe responder 400 (petición inválida).
        """
        url = "/api/ventas/crear/"

        payload = {
            "es_credito": False,
            "cliente_id": self.cliente.id,
            "detalles": [],  # sin detalles
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_crear_venta_detalle_sin_producto_id_devuelve_400(self):
        """
        Si un detalle no incluye 'producto_id',
        la API debe responder 400 indicando error en el detalle.
        """
        url = "/api/ventas/crear/"

        payload = {
            "es_credito": False,
            "cliente_id": self.cliente.id,
            "detalles": [
                {
                    # falta producto_id
                    "cantidad": 1,
                    "precio_unitario": "1000.00",
                }
            ],
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_crear_venta_detalle_con_producto_inexistente_devuelve_400(self):
        """
        Si 'producto_id' apunta a un Producto que no existe,
        la API debe responder 400 con un mensaje de error.
        """
        url = "/api/ventas/crear/"

        payload = {
            "es_credito": False,
            "cliente_id": self.cliente.id,
            "detalles": [
                {
                    "producto_id": 999999,  # ID que asumimos no existe
                    "cantidad": 1,
                    "precio_unitario": "1000.00",
                }
            ],
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_crear_venta_credito_sin_cliente_devuelve_400(self):
        """
        Venta a crédito sin cliente asociado debe ser rechazada:
        - es_credito=True
        - cliente_id ausente o None
        """
        if self.producto is None:
            self.skipTest(
                "No se pudo crear Producto de prueba. "
                "Ajustar campos de Producto según el modelo real para habilitar este test."
            )

        url = "/api/ventas/crear/"

        payload = {
            "es_credito": True,
            "cliente_id": None,
            "nombre_cliente_libre": "Cliente sin registro",
            "detalles": [
                {
                    "producto_id": self.producto.id,
                    "cantidad": 1,
                    "precio_unitario": "2000.00",
                }
            ],
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_crear_venta_con_json_invalido_devuelve_400(self):
        """
        Si el cuerpo de la petición no es JSON válido,
        la API debería responder 400.
        """
        url = "/api/ventas/crear/"

        response = self.client.post(
            url,
            data="esto-no-es-json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

class ApiVentasEstadisticasHoyTests(BaseApiVentasTestCase):
    """
    Plan de pruebas para:
    GET /api/ventas/estadisticas/hoy/
    """

    def test_estadisticas_hoy_sin_ventas_devuelve_ceros(self):
        """
        Si no hay ventas registradas para el día de hoy,
        la API debe devolver:
        - total_ventas = 0.0
        - cantidad_ventas = 0
        - fecha = hoy en formato ISO (YYYY-MM-DD)
        """
        url = "/api/ventas/estadisticas/hoy/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        hoy = timezone.now().date().isoformat()

        self.assertEqual(data.get("total_ventas"), 0.0)
        self.assertEqual(data.get("cantidad_ventas"), 0)
        self.assertEqual(data.get("fecha"), hoy)

    def test_estadisticas_hoy_con_varias_ventas_suma_totales(self):
        """
        Si hay varias ventas hoy, la API debe:
        - sumar correctamente el total de todas las ventas
        - contar cuántas ventas se hicieron
        """
        # Creamos 2 ventas para hoy
        Venta.objects.create(
            cliente=self.cliente,
            nombre_cliente_libre="",
            es_credito=False,
            total=Decimal("10000.00"),
        )
        Venta.objects.create(
            cliente=self.cliente,
            nombre_cliente_libre="",
            es_credito=False,
            total=Decimal("25000.00"),
        )

        url = "/api/ventas/estadisticas/hoy/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Debe haber 2 ventas
        self.assertEqual(data.get("cantidad_ventas"), 2)

        # total_ventas se envía como float
        self.assertAlmostEqual(data.get("total_ventas"), 35000.0, places=2)

        hoy = timezone.now().date().isoformat()
        self.assertEqual(data.get("fecha"), hoy)

class BaseApiReportesTestCase(TestCase):
    """
    Base para pruebas de la API de reportes.

    - Crea un usuario con rol Admin (para pasar es_admin)
    - Inicia sesión en self.client
    - Crea algunas ventas de prueba en días distintos
    """

    def setUp(self):
        User = get_user_model()

        # Usuario de pruebas
        self.user = User.objects.create_user(
            username="admin_reportes",
            password="testpass123",
            is_staff=True,
        )

        # Aseguramos que exista el grupo "Admin" y se lo asignamos
        grupo_admin, _ = Group.objects.get_or_create(name="Admin")
        self.user.groups.add(grupo_admin)

        # Login en el cliente de pruebas
        logged_in = self.client.login(
            username="admin_reportes",
            password="testpass123",
        )
        self.assertTrue(logged_in, "No se pudo hacer login en el cliente de reportes")

        # Fechas base
        self.hoy = timezone.now()
        self.ayer = self.hoy - timedelta(days=1)

        # Ventas de prueba:
        # - 2 ventas hoy (1 contado, 1 crédito)
        # - 1 venta ayer (contado)

        self.venta_hoy_contado = Venta.objects.create(
            nombre_cliente_libre="Cliente Contado Hoy",
            es_credito=False,
            total=Decimal("10000.00"),
            fecha=self.hoy,
        )

        self.venta_hoy_credito = Venta.objects.create(
            nombre_cliente_libre="Cliente Crédito Hoy",
            es_credito=True,
            total=Decimal("5000.00"),
            fecha=self.hoy,
        )

        self.venta_ayer_contado = Venta.objects.create(
            nombre_cliente_libre="Cliente Ayer Contado",
            es_credito=False,
            total=Decimal("2000.00"),
            fecha=self.ayer,
        )

class ApiReportesVentasResumenTests(BaseApiReportesTestCase):
    def test_ventas_resumen_sin_parametros_devuelve_resumen_del_dia_actual(self):
        """
        GET /api/reportes/ventas-resumen/ sin parámetros:

        - Debe responder 200
        - Debe considerar solo las ventas del día actual
        - cantidad_ventas: 2 (contado + crédito de hoy)
        - total_monto: 15000.00
        - total_contado: 10000.00
        - total_credito: 5000.00
        """
        response = self.client.get("/api/reportes/ventas-resumen/")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Verificamos que venga la estructura esperada
        self.assertIn("rango", data)
        self.assertIn("resumen", data)

        resumen = data["resumen"]

        # Solo deberían contarse las ventas de HOY (2 ventas)
        self.assertEqual(resumen["cantidad_ventas"], 2)
        self.assertEqual(resumen["total_monto"], "15000.00")
        self.assertEqual(resumen["total_contado"], "10000.00")
        self.assertEqual(resumen["total_credito"], "5000.00")

    def test_ventas_resumen_sin_ventas_devuelve_ceros(self):
        """
        Si no hay ventas en el rango, el endpoint debe:

        - Responder 200
        - Devolver cantidad_ventas = 0
        - Totales en "0.00"
        """
        # Borramos las ventas de la base de pruebas
        Venta.objects.all().delete()

        response = self.client.get("/api/reportes/ventas-resumen/")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("resumen", data)
        resumen = data["resumen"]

        self.assertEqual(resumen["cantidad_ventas"], 0)
        self.assertEqual(resumen["total_monto"], "0.00")
        self.assertEqual(resumen["total_contado"], "0.00")
        self.assertEqual(resumen["total_credito"], "0.00")

class ApiReportesVentasPorDiaTests(BaseApiReportesTestCase):
    def test_ventas_por_dia_en_rango_devuelve_un_elemento_por_dia(self):
        """
        GET /api/reportes/ventas-por-dia/?fecha_desde=...&fecha_hasta=...

        Con las ventas de setUp():
        - Ayer: 1 venta contado por 2000.00
        - Hoy:  2 ventas (contado 10000.00, crédito 5000.00) → 15000.00 total
        """
        fecha_desde = self.ayer.date().isoformat()
        fecha_hasta = self.hoy.date().isoformat()

        response = self.client.get(
            "/api/reportes/ventas-por-dia/",
            {
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("dias", data)

        dias = data["dias"]
        # Deberíamos tener 2 días: ayer y hoy
        self.assertEqual(len(dias), 2)

        # Lo más cómodo: indexar por fecha
        por_fecha = {d["fecha"]: d for d in dias}

        # Día de ayer
        dia_ayer = por_fecha[fecha_desde]
        self.assertEqual(dia_ayer["cantidad_ventas"], 1)
        self.assertEqual(dia_ayer["total_monto"], "2000.00")
        self.assertEqual(dia_ayer["total_contado"], "2000.00")
        self.assertEqual(dia_ayer["total_credito"], "0.00")

        # Día de hoy
        dia_hoy = por_fecha[fecha_hasta]
        self.assertEqual(dia_hoy["cantidad_ventas"], 2)
        self.assertEqual(dia_hoy["total_monto"], "15000.00")
        self.assertEqual(dia_hoy["total_contado"], "10000.00")
        self.assertEqual(dia_hoy["total_credito"], "5000.00")

    def test_ventas_por_dia_sin_ventas_devuelve_lista_vacia(self):
        """
        Si no hay ventas en el rango, 'dias' debe ser una lista vacía.
        """
        Venta.objects.all().delete()

        fecha_hoy = timezone.now().date().isoformat()

        response = self.client.get(
            "/api/reportes/ventas-por-dia/",
            {
                "fecha_desde": fecha_hoy,
                "fecha_hasta": fecha_hoy,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("dias", data)
        self.assertEqual(data["dias"], [])

from django.urls import reverse

# =====================================================
# PRUEBAS: /api/reportes/productos-mas-vendidos/
# =====================================================

class ApiReportesProductosMasVendidosTests(BaseApiVentasTestCase):
    """
    Plan de pruebas para:
    GET /api/reportes/productos-mas-vendidos/
    """

    def test_productos_mas_vendidos_sin_ventas_devuelve_lista_vacia(self):
        """
        Si no hay DetalleVenta en el rango consultado, el endpoint debería:
        - responder 200
        - devolver una lista vacía en 'productos'
        - incluir metadatos de rango en 'rango'
        """
        url = "/api/reportes/productos-mas-vendidos/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Estructura básica
        self.assertIn("rango", data)
        self.assertIn("productos", data)

        productos = data["productos"]
        self.assertIsInstance(productos, list)
        self.assertEqual(len(productos), 0)

    def test_productos_mas_vendidos_incluye_rango_fechas_filtrado(self):
        """
        Si se envían fecha_desde y fecha_hasta, el endpoint debería:
        - responder 200
        - respetar la estructura con 'rango' y 'productos'
        - reflejar el rango solicitado en 'rango'
        (No validamos la lógica de filtrado, solo la forma de la respuesta).
        """
        url = "/api/reportes/productos-mas-vendidos/"
        params = {
            "fecha_desde": "2025-01-01",
            "fecha_hasta": "2025-01-31",
        }

        response = self.client.get(url, params)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("rango", data)
        self.assertIn("productos", data)

        rango = data["rango"]
        self.assertIn("fecha_desde", rango)
        self.assertIn("fecha_hasta", rango)

        # Opcional: comprobar que son strings tipo fecha
        self.assertEqual(rango["fecha_desde"], params["fecha_desde"])
        self.assertEqual(rango["fecha_hasta"], params["fecha_hasta"])

        self.assertIsInstance(data["productos"], list)


# =====================================================
# PRUEBAS: /api/reportes/ventas-por-categoria/
# =====================================================

class ApiReportesVentasPorCategoriaTests(BaseApiVentasTestCase):
    """
    Plan de pruebas para:
    GET /api/reportes/ventas-por-categoria/
    """

    def test_ventas_por_categoria_sin_ventas_devuelve_lista_vacia(self):
        """
        Si no hay ventas registradas, el endpoint debería:
        - responder 200
        - devolver 'categorias' como lista vacía
        """
        url = "/api/reportes/ventas-por-categoria/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("categorias", data)
        categorias = data["categorias"]

        self.assertIsInstance(categorias, list)
        self.assertEqual(len(categorias), 0)

    def test_ventas_por_categoria_respuesta_tiene_campos_basicos(self):
        """
        Aun sin datos reales, verificamos que cada categoría devuelta
        tenga los campos básicos esperados:
        - 'categoria'
        - 'cantidad_ventas'
        - 'total_monto'
        Para este test, no garantizamos que existan elementos; si la lista
        está vacía, el test igual pasa por estructura.
        """
        url = "/api/reportes/ventas-por-categoria/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("categorias", data)

        categorias = data["categorias"]
        self.assertIsInstance(categorias, list)

        for cat in categorias:
            self.assertIn("categoria", cat)
            self.assertIn("cantidad_ventas", cat)
            self.assertIn("total_monto", cat)


# =====================================================
# PRUEBAS: /api/reportes/productos-mas-vendidos-mejorado/
# =====================================================

class ApiReportesProductosMasVendidosMejoradoTests(BaseApiVentasTestCase):
    """
    Plan de pruebas para:
    GET /api/reportes/productos-mas-vendidos-mejorado/
    """

    def test_productos_mas_vendidos_mejorado_devuelve_200_y_lista(self):
        """
        Un GET simple debería:
        - responder 200
        - devolver un JSON con clave 'productos'
        - donde 'productos' es una lista (posiblemente vacía)
        """
        url = "/api/reportes/productos-mas-vendidos-mejorado/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("productos", data)

        productos = data["productos"]
        self.assertIsInstance(productos, list)

    def test_productos_mas_vendidos_mejorado_elementos_tienen_campos_basicos(self):
        """
        Para cada producto devuelto, esperamos al menos:
        - 'id'
        - 'nombre'
        - 'cantidad'
        - 'total'
        Si la lista está vacía, el test pasa igual.
        """
        url = "/api/reportes/productos-mas-vendidos-mejorado/"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("productos", data)

        productos = data["productos"]
        self.assertIsInstance(productos, list)

        for prod in productos:
            self.assertIn("id", prod)
            self.assertIn("nombre", prod)
            self.assertIn("cantidad", prod)
            self.assertIn("total", prod)

