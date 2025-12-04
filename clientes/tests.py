from decimal import Decimal

import json 

from unittest.mock import patch 

from django.test import TestCase
from django.core.exceptions import ValidationError

from clientes.models import Cliente, MovimientoCredito

from django.contrib.auth import get_user_model

from clientes.models import Cliente, MovimientoCredito

class BaseCreditoTestCase(TestCase):
    def setUp(self):
        """
        Cliente base para pruebas de crédito.
        """
        self.cliente = Cliente.objects.create(
            nombre="Cliente de Prueba",
            rut="11.111.111-1",
            tiene_credito=True,
            es_activo=True,
            cupo_maximo=Decimal("100000.00"),
            saldo_actual=Decimal("20000.00"),
        )


class ClientePuedeComprarCreditoTests(BaseCreditoTestCase):
    def test_puede_comprar_cuando_tiene_credito_activo_y_no_excede_cupo(self):
        """
        Debe devolver True cuando:
        - el cliente tiene_credito=True
        - el cliente es_activo=True
        - saldo_actual + monto <= cupo_maximo
        """
        # Con los valores de setUp():
        # saldo_actual = 20000
        # cupo_maximo = 100000
        # Si intenta comprar por 30000 -> 20000 + 30000 = 50000 <= 100000
        monto = Decimal("30000.00")

        puede = self.cliente.puede_comprar_a_credito(monto)

        self.assertTrue(puede)

    def test_no_puede_comprar_si_no_tiene_credito(self):
        """
        Debe devolver False si el cliente tiene_credito=False,
        aunque el monto sea razonable y no exceda el cupo.
        """
        monto = Decimal("10000.00")

        self.cliente.tiene_credito = False
        self.cliente.save()

        puede = self.cliente.puede_comprar_a_credito(monto)

        self.assertFalse(puede)

    def test_no_puede_comprar_si_cliente_inactivo(self):
        """
        Debe devolver False si el cliente está inactivo (es_activo=False),
        aunque tenga crédito y el monto no exceda el cupo.
        """
        monto = Decimal("15000.00")

        self.cliente.es_activo = False
        self.cliente.save()

        puede = self.cliente.puede_comprar_a_credito(monto)

        self.assertFalse(puede)

    def test_no_puede_comprar_si_excede_cupo_maximo(self):
        """
        Debe devolver False cuando saldo_actual + monto > cupo_maximo.
        """
        self.cliente.saldo_actual = Decimal("90000.00")
        self.cliente.cupo_maximo = Decimal("100000.00")
        self.cliente.save()

        monto = Decimal("20000.00")  # 90000 + 20000 = 110000 > 100000

        puede = self.cliente.puede_comprar_a_credito(monto)

        self.assertFalse(puede)


class ClienteRegistrarMovimientoCompraTests(BaseCreditoTestCase):
    def test_compra_valida_incrementa_saldo_y_crea_movimiento(self):
        """
        Una compra válida debe:
        - aumentar saldo_actual del cliente
        - crear un MovimientoCredito tipo COMPRA
        - dejar saldo_despues igual al nuevo saldo del cliente
        """
        saldo_inicial = self.cliente.saldo_actual  # 20000
        monto = Decimal("15000.00")

        movimiento = self.cliente.registrar_movimiento_credito(
            tipo="COMPRA",
            monto=monto,
            venta=None,
            observaciones="Compra de prueba",
        )

        self.cliente.refresh_from_db()
        saldo_esperado = saldo_inicial + monto

        self.assertEqual(self.cliente.saldo_actual, saldo_esperado)
        self.assertIsInstance(movimiento, MovimientoCredito)
        self.assertEqual(movimiento.tipo, "COMPRA")
        self.assertEqual(movimiento.monto, monto)
        self.assertEqual(movimiento.saldo_despues, saldo_esperado)
        self.assertEqual(movimiento.cliente, self.cliente)

    def test_compra_que_excede_cupo_lanza_validation_error(self):
        """
        Si la compra excede el cupo máximo, se debe lanzar ValidationError
        y NO debe cambiar el saldo del cliente.
        """
        self.cliente.cupo_maximo = Decimal("30000.00")
        self.cliente.saldo_actual = Decimal("25000.00")
        self.cliente.save()

        saldo_inicial = self.cliente.saldo_actual
        monto = Decimal("10000.00")  # 25000 + 10000 = 35000 > 30000

        with self.assertRaises(ValidationError):
            self.cliente.registrar_movimiento_credito(
                tipo="COMPRA",
                monto=monto,
                venta=None,
                observaciones="Compra que excede el cupo",
            )

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, saldo_inicial)

class ClienteRegistrarMovimientoAbonoTests(BaseCreditoTestCase):
    def test_abono_valido_disminuye_saldo_y_crea_movimiento(self):
        """
        Un abono válido debe:
        - disminuir el saldo_actual del cliente
        - crear un MovimientoCredito tipo ABONO
        - dejar saldo_despues igual al nuevo saldo del cliente
        """
        # Dejamos al cliente con una deuda más grande para ver bien el cambio
        self.cliente.saldo_actual = Decimal("30000.00")
        self.cliente.save()

        saldo_inicial = self.cliente.saldo_actual  # 30000
        monto = Decimal("10000.00")  # abona 10.000

        # Ejecutamos la lógica que queremos probar
        movimiento = self.cliente.registrar_movimiento_credito(
            tipo="ABONO",
            monto=monto,
            venta=None,  # para abonos manuales, suele ser None
            observaciones="Abono de prueba",
        )

        # Refrescamos desde la BD
        self.cliente.refresh_from_db()
        saldo_esperado = saldo_inicial - monto  # 30000 - 10000 = 20000

        # 1) El saldo del cliente debe haber bajado
        self.assertEqual(self.cliente.saldo_actual, saldo_esperado)

        # 2) El movimiento debe ser correcto
        self.assertIsInstance(movimiento, MovimientoCredito)
        self.assertEqual(movimiento.tipo, "ABONO")
        self.assertEqual(movimiento.monto, monto)
        self.assertEqual(movimiento.saldo_despues, saldo_esperado)
        self.assertEqual(movimiento.cliente, self.cliente)

    def test_abono_con_monto_menor_o_igual_cero_lanza_validation_error(self):
        """
        Un abono con monto <= 0 debe lanzar ValidationError
        y no debe cambiar el saldo del cliente.
        """
        # Importamos aquí por si acaso (aunque también podrías tenerlo arriba del archivo)
        from django.core.exceptions import ValidationError

        # Dejo un saldo inicial cualquiera
        self.cliente.saldo_actual = Decimal("20000.00")
        self.cliente.save()
        saldo_inicial = self.cliente.saldo_actual

        # Probamos dos montos inválidos: 0 y negativo
        for monto_str in ["0", "-1000"]:
            with self.subTest(monto=monto_str):
                monto = Decimal(monto_str)

                with self.assertRaises(ValidationError):
                    self.cliente.registrar_movimiento_credito(
                        tipo="ABONO",
                        monto=monto,
                        venta=None,
                        observaciones="Abono inválido (monto <= 0)",
                    )

                # Verificamos que el saldo no haya cambiado después del intento
                self.cliente.refresh_from_db()
                self.assertEqual(self.cliente.saldo_actual, saldo_inicial)

class BaseApiCreditoTestCase(BaseCreditoTestCase):
    """
    Base para pruebas de la API de crédito.

    - Crea un cliente de prueba (viene de BaseCreditoTestCase)
    - Crea un usuario tipo admin/cajero
    - Inicia sesión con ese usuario en self.client
    """

    def setUp(self):
        # Llamamos primero al setUp de BaseCreditoTestCase
        super().setUp()

        User = get_user_model()

        # Creamos un usuario con permisos altos
        self.user = User.objects.create_user(
            username="cajero_api",
            password="testpass123",
            is_staff=True,      # suele bastar para muchos checks
            is_superuser=True,  # por si es_cajero_o_admin revisa esto
        )

        # Iniciamos sesión en el test client
        logged_in = self.client.login(
            username="cajero_api",
            password="testpass123",
        )

        # Si algo sale mal, mejor que el test lo marque como fallo
        self.assertTrue(logged_in, "No se pudo hacer login en el cliente de tests")

class ApiCreditoAbonarTests(BaseApiCreditoTestCase):
    def test_abono_api_valido_devuelve_201_y_actualiza_saldo(self):
        """
        Un POST válido a /api/creditos/abonar/ debe:
        - responder 201
        - disminuir el saldo_actual del cliente
        - devolver datos del cliente y del movimiento
        """
        # Saldo inicial que viene de BaseCreditoTestCase
        saldo_inicial = self.cliente.saldo_actual  # 20000 por defecto

        monto_str = "5000.00"

        payload = {
            "cliente_id": self.cliente.id,
            "monto": monto_str,
            "observaciones": "Abono API de prueba",
        }

        # 🔧 Parcheamos es_cajero_o_admin SOLO en este test para que siempre devuelva True
        with patch("clientes.api_credito.es_cajero_o_admin", return_value=True):
            response = self.client.post(
                "/api/creditos/abonar/",
                data=json.dumps(payload),
                content_type="application/json",
            )

        # 1) Verificamos el status HTTP
        self.assertEqual(response.status_code, 201)

        # 2) Verificamos el cuerpo de la respuesta
        data = response.json()

        # Debe traer info del cliente y del movimiento
        self.assertIn("cliente", data)
        self.assertIn("movimiento", data)

        cliente_json = data["cliente"]
        movimiento_json = data["movimiento"]

        # 3) Verificamos que el saldo del cliente haya bajado en BD
        self.cliente.refresh_from_db()
        saldo_esperado = saldo_inicial - Decimal(monto_str)

        self.assertEqual(self.cliente.saldo_actual, saldo_esperado)

        # 4) Verificamos consistencia con el JSON de respuesta
        self.assertEqual(Decimal(cliente_json["saldo_actual"]), saldo_esperado)
        self.assertEqual(movimiento_json["tipo"], "ABONO")
        self.assertEqual(Decimal(movimiento_json["monto"]), Decimal(monto_str))
        self.assertEqual(
            Decimal(movimiento_json["saldo_despues"]),
            saldo_esperado,
        )

    def test_abono_api_cliente_inexistente_devuelve_404(self):
        """
        Si se envía un cliente_id que no existe,
        la API debería responder 404 y no modificar nada.
        """
        # Elegimos un ID alto que no exista en BD de pruebas
        cliente_id_inexistente = 9999
        monto_str = "5000.00"

        payload = {
            "cliente_id": cliente_id_inexistente,
            "monto": monto_str,
            "observaciones": "Abono con cliente inexistente",
        }

        # Guardamos el saldo del cliente válido que tenemos en setUp
        saldo_original = self.cliente.saldo_actual

        response = self.client.post(
            "/api/creditos/abonar/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Desde el punto de vista del plan de pruebas, LO ESPERADO es 404
        self.assertEqual(response.status_code, 404)

        # La implementación actual puede no hacer esto todavía,
        # pero el plan de pruebas dice que NO se debe tocar el saldo
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, saldo_original)

        # Opcional: podríamos comprobar que el JSON tenga un mensaje de error
        # data = response.json()
        # self.assertIn("detail", data)

    def test_abono_api_monto_no_numerico_devuelve_400(self):
        """
        Si se envía un monto no numérico,
        la API debería responder 400 y no modificar el saldo.
        """
        saldo_inicial = self.cliente.saldo_actual

        payload = {
            "cliente_id": self.cliente.id,
            "monto": "abc",  # valor no convertible a Decimal
            "observaciones": "Abono con monto inválido",
        }

        response = self.client.post(
            "/api/creditos/abonar/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Desde el punto de vista del plan de pruebas,
        # lo ESPERADO es un 400 Bad Request
        self.assertEqual(response.status_code, 400)

        # El saldo no debería cambiar
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, saldo_inicial)

        # Opcional en el plan: se podría esperar un mensaje de error en el JSON
        # data = response.json()
        # self.assertIn("error", data)

class ApiCreditoSaldoTests(BaseApiCreditoTestCase):
    def test_saldo_api_cliente_existente_devuelve_200_y_datos_correctos(self):
        """
        Un GET a /api/creditos/saldo/ con cliente_id válido debería:
        - responder 200
        - devolver datos del cliente incluyendo saldo_actual correcto
        """
        # Aseguramos un saldo conocido
        self.cliente.saldo_actual = Decimal("12345.00")
        self.cliente.save()

        response = self.client.get(
            "/api/creditos/saldo/",
            {"cliente_id": self.cliente.id},
        )

        # Desde el punto de vista del plan de pruebas, lo ESPERADO es 200
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Debe traer un objeto cliente con al menos id, nombre y saldo_actual
        self.assertIn("cliente", data)
        cliente_json = data["cliente"]

        self.assertEqual(cliente_json["id"], self.cliente.id)
        self.assertEqual(cliente_json["nombre"], self.cliente.nombre)
        self.assertEqual(
            Decimal(cliente_json["saldo_actual"]),
            Decimal("12345.00"),
        )

    def test_saldo_api_cliente_existente_devuelve_200_y_datos_correctos(self):
        """
        Un GET a /api/creditos/saldo/ con cliente_id válido debería:
        - responder 200
        - devolver datos del cliente incluyendo saldo_actual correcto
        """
        self.cliente.saldo_actual = Decimal("12345.00")
        self.cliente.save()

        response = self.client.get(
            "/api/creditos/saldo/",
            {"cliente_id": self.cliente.id},
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("cliente", data)
        cliente_json = data["cliente"]

        self.assertEqual(cliente_json["id"], self.cliente.id)
        self.assertEqual(cliente_json["nombre"], self.cliente.nombre)
        self.assertEqual(
            Decimal(cliente_json["saldo_actual"]),
            Decimal("12345.00"),
        )

    def test_saldo_api_cliente_inexistente_devuelve_404(self):
        """
        Si se consulta el saldo de un cliente_id que no existe,
        la API debería responder 404 y no modificar nada en BD.
        """
        # Elegimos un ID que no existe en la BD de pruebas
        cliente_id_inexistente = 9999

        # Guardamos el saldo del cliente real, para comprobar que no cambie
        saldo_original = self.cliente.saldo_actual

        response = self.client.get(
            "/api/creditos/saldo/",
            {"cliente_id": cliente_id_inexistente},
        )

        # Desde el plan de pruebas, lo esperado es 404 Not Found
        self.assertEqual(response.status_code, 404)

        # Aseguramos que el saldo del cliente real no fue modificado
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, saldo_original)

    def test_saldo_api_sin_parametros_devuelve_400(self):
        """
        Si se consulta /api/creditos/saldo/ sin cliente_id ni rut,
        la API debería responder 400 (petición inválida).
        """
        # Guardamos el saldo del cliente real para verificar que no cambie
        saldo_original = self.cliente.saldo_actual

        # Llamamos al endpoint SIN parámetros
        response = self.client.get("/api/creditos/saldo/")

        # Desde el punto de vista del plan de pruebas, lo esperado es 400
        self.assertEqual(response.status_code, 400)

        # No debería cambiar el saldo de ningún cliente
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, saldo_original)

        # Opcional: podríamos esperar un mensaje de error en el JSON
        # data = response.json()
        # self.assertIn("error", data)

class ApiCreditoMovimientosTests(BaseApiCreditoTestCase):
    def test_movimientos_api_cliente_con_movimientos_devuelve_200_y_lista(self):
        """
        Un GET a /api/creditos/movimientos/ con un cliente que tiene
        movimientos de crédito debería:
        - responder 200
        - devolver datos del cliente
        - devolver una lista de movimientos con al menos 1 elemento
        """
        # Creamos algunos movimientos de prueba usando la propia lógica del modelo
        # Partimos del saldo inicial definido en BaseCreditoTestCase (20000)
        compra_monto = Decimal("10000.00")
        abono_monto = Decimal("5000.00")

        # COMPRA: debería subir saldo a 30000
        self.cliente.registrar_movimiento_credito(
            tipo="COMPRA",
            monto=compra_monto,
            venta=None,
            observaciones="Compra de prueba para movimientos API",
        )

        # ABONO: debería bajar saldo a 25000
        self.cliente.registrar_movimiento_credito(
            tipo="ABONO",
            monto=abono_monto,
            venta=None,
            observaciones="Abono de prueba para movimientos API",
        )

        # Ahora llamamos al endpoint de movimientos
        response = self.client.get(
            "/api/creditos/movimientos/",
            {"cliente_id": self.cliente.id},
        )

        # Desde el punto de vista del plan de pruebas, lo ESPERADO es 200
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Debe venir info del cliente y una lista de movimientos
        self.assertIn("cliente", data)
        self.assertIn("movimientos", data)

        cliente_json = data["cliente"]
        movimientos = data["movimientos"]

        # Verificamos que el cliente sea el correcto
        self.assertEqual(cliente_json["id"], self.cliente.id)
        self.assertEqual(cliente_json["nombre"], self.cliente.nombre)

        # Debe haber al menos 2 movimientos (la compra y el abono que creamos)
        self.assertGreaterEqual(len(movimientos), 2)

        # Revisamos que la estructura de cada movimiento tenga los campos clave
        for mov in movimientos:
            self.assertIn("id", mov)
            self.assertIn("tipo", mov)
            self.assertIn("monto", mov)
            self.assertIn("saldo_despues", mov)
            self.assertIn("fecha", mov)
            # venta_id y observaciones pueden ser None, pero la clave debe existir
            self.assertIn("venta_id", mov)
            self.assertIn("observaciones", mov)

    def test_movimientos_api_cliente_sin_movimientos_devuelve_200_y_lista_vacia(self):
        """
        Si el cliente no tiene movimientos de crédito,
        /api/creditos/movimientos/ debería:
        - responder 200
        - devolver una lista vacía de movimientos
        """
        # Aseguramos que no existan movimientos en BD
        MovimientoCredito.objects.all().delete()

        response = self.client.get(
            "/api/creditos/movimientos/",
            {"cliente_id": self.cliente.id},
        )

        # Desde el plan de pruebas, lo esperado es 200 OK
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Debe venir la clave "movimientos" y ser una lista vacía
        self.assertIn("movimientos", data)
        movimientos = data["movimientos"]
        self.assertIsInstance(movimientos, list)
        self.assertEqual(len(movimientos), 0)

    def test_movimientos_api_cliente_inexistente_devuelve_404(self):
        """
        Si se consulta /api/creditos/movimientos/ con un cliente_id que no existe,
        la API debería responder 404 y no modificar nada en BD.
        """
        cliente_id_inexistente = 9999

        # Guardamos el saldo de nuestro cliente real para asegurarnos de que no cambie
        saldo_original = self.cliente.saldo_actual

        response = self.client.get(
            "/api/creditos/movimientos/",
            {"cliente_id": cliente_id_inexistente},
        )

        # Desde el plan de pruebas, lo esperado es 404 Not Found
        self.assertEqual(response.status_code, 404)

        # El saldo del cliente real no debería cambiar
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, saldo_original)

    def test_movimientos_api_sin_parametros_devuelve_400(self):
        """
        Si se llama a /api/creditos/movimientos/ sin cliente_id ni rut,
        la API debería responder 400 (petición inválida).
        """
        saldo_original = self.cliente.saldo_actual

        response = self.client.get("/api/creditos/movimientos/")

        # Desde el punto de vista del plan, lo esperado es 400 Bad Request
        self.assertEqual(response.status_code, 400)

        # No debería cambiar el saldo de ningún cliente
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_actual, saldo_original)

class ApiCreditoClientesConDeudaTests(BaseApiCreditoTestCase):
    def test_clientes_con_deuda_devuelve_200_y_solo_clientes_con_saldo_positivo(self):
        """
        /api/creditos/clientes-con-deuda/ debería:
        - responder 200
        - devolver solo clientes con saldo_actual > 0
        """
        # Cliente base de BaseCreditoTestCase: saldo_actual = 20000 (tiene deuda)
        cliente_con_deuda = self.cliente

        # Creamos otro cliente con deuda
        cliente_con_deuda_2 = Cliente.objects.create(
            nombre="Cliente Deudor 2",
            rut="22.222.222-2",
            tiene_credito=True,
            es_activo=True,
            cupo_maximo=Decimal("50000.00"),
            saldo_actual=Decimal("10000.00"),
        )

        # Y un cliente SIN deuda (saldo 0)
        cliente_sin_deuda = Cliente.objects.create(
            nombre="Cliente Sin Deuda",
            rut="33.333.333-3",
            tiene_credito=True,
            es_activo=True,
            cupo_maximo=Decimal("50000.00"),
            saldo_actual=Decimal("0.00"),
        )

        response = self.client.get("/api/creditos/clientes-con-deuda/")

        # Desde el plan de pruebas, lo esperado es 200 OK
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Esperamos una lista de clientes con deuda
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

        ids = {c["id"] for c in data}
        nombres = {c["nombre"] for c in data}

        # Deben estar los dos con deuda
        self.assertIn(cliente_con_deuda.id, ids)
        self.assertIn(cliente_con_deuda_2.id, ids)

        # No debería estar el cliente sin deuda
        self.assertNotIn(cliente_sin_deuda.id, ids)
        self.assertNotIn("Cliente Sin Deuda", nombres)

class ClienteDatosBasicosTests(TestCase):
    def test_crear_cliente_con_datos_minimos(self):
        """
        Crear un cliente con nombre y rut debe:
        - guardar sin errores
        - dejar campos opcionales vacíos
        - inicializar flags y campos de crédito con valores por defecto
        """
        cliente = Cliente.objects.create(
            nombre="Cliente Prueba Básico",
            rut="12.345.678-9",
        )

        # Se asigna un ID en BD
        self.assertIsNotNone(cliente.id)

        # Datos básicos
        self.assertEqual(cliente.nombre, "Cliente Prueba Básico")
        self.assertEqual(cliente.rut, "12.345.678-9")

        # Campos opcionales vacíos
        self.assertEqual(cliente.telefono, "")
        self.assertEqual(cliente.email, "")
        self.assertEqual(cliente.direccion, "")

        # Flags y crédito por defecto
        self.assertFalse(cliente.tiene_credito)
        self.assertEqual(cliente.cupo_maximo, Decimal("0"))
        self.assertEqual(cliente.saldo_actual, Decimal("0"))
        self.assertTrue(cliente.es_activo)

    def test_rut_unico_no_permite_clientes_duplicados(self):
        """
        El campo rut tiene unique=True.
        Intentar crear dos clientes con el mismo rut debe producir un error.
        """
        from django.db import IntegrityError

        Cliente.objects.create(
            nombre="Cliente 1",
            rut="11.111.111-1",
        )

        # Al crear otro con el mismo RUT debería dispararse una IntegrityError
        with self.assertRaises(IntegrityError):
            Cliente.objects.create(
                nombre="Cliente 2",
                rut="11.111.111-1",
            )

    def test_str_cliente_muestra_nombre_y_rut(self):
        """
        __str__ del cliente debe devolver 'Nombre (RUT)'.
        """
        cliente = Cliente.objects.create(
            nombre="Cliente String",
            rut="22.222.222-2",
        )

        self.assertEqual(str(cliente), "Cliente String (22.222.222-2)")
