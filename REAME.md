📦 Sistema POS – Almacén Yuyitos

Backend desarrollado en Django + MySQL, con módulos para punto de venta, inventario, clientes con crédito interno y gestión de ventas.
El proyecto está estructurado en apps independientes y expone una API limpia para ser consumida por un frontend POS.

🚀 Características principales
✔ Gestión de inventario

CRUD de productos y categorías

Control de stock (stock_actual, stock_minimo)

Manejo opcional de fecha de vencimiento

API de productos con filtro ?q=

✔ Punto de venta (POS)

Consulta de productos desde API

Consulta de stock

Creación de ventas con detalle de productos

Descuento automático de stock por venta

✔ Clientes con crédito interno

Registro de clientes con límite de crédito

Consulta de saldo y crédito disponible

Cálculo automático de deuda

API de clientes y créditos

✔ Ventas y Reportes

Registro de ventas

Detalle por producto

Control interno para evitar ventas sin detalle

Reportes vía API

🏗 Estructura del proyecto
almacen-yuyitos/
│ manage.py
│ requirements.txt
│ README.md
├── yuyitos/          ← Configuración global del proyecto
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── inventario/       ← Productos, Categorías, Stock + APIs
│   ├── models.py
│   ├── api_productos.py
│   ├── urls_api.py
│   └── admin.py
│
├── clientes/         ← Clientes, crédito interno + APIs
│   ├── models.py
│   ├── api_clientes.py
│   ├── api_credito.py
│   ├── api_consultas.py
│   ├── urls_api.py
│   └── admin.py
│
└── ventas/           ← Ventas, detalle, reportes
    ├── models.py
    ├── api_ventas.py
    ├── api_reportes.py
    ├── urls_api.py
    └── admin.py

⚙️ Requerimientos
Python & entorno

Python 3.10+

Virtualenv o venv

Base de datos

MySQL (desarrollo y producción)

Usuario y base recomendados:

DB_NAME = yuyitos_db
USER     = yuyitos
PASSWORD = tu_password
HOST     = localhost
PORT     = 3306

Dependencias (incluidas en requirements.txt)
Django
mysqlclient

🔧 Instalación del proyecto
1. Clonar el repositorio
git clone https://github.com/Denisse-Guzman/almacen-yuyitos.git
cd almacen-yuyitos

2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate   # Windows

3. Instalar dependencias
pip install -r requirements.txt

4. Configurar la base MySQL

Crear base de datos desde MySQL Workbench o terminal:

CREATE DATABASE yuyitos_db CHARACTER SET utf8mb4;
CREATE USER 'yuyitos'@'localhost' IDENTIFIED BY '123123';
GRANT ALL PRIVILEGES ON yuyitos_db.* TO 'yuyitos'@'localhost';
FLUSH PRIVILEGES;

5. Ejecutar migraciones
python manage.py migrate

6. Ejecutar servidor local
python manage.py runserver


API disponible en:

http://127.0.0.1:8000/api/

📡 Endpoints principales de la API
🟦 Inventario / Productos

(Base: /api/)

▸ Listar productos

GET /api/productos/
Filtros soportados:
/api/productos/?q=arroz

▸ Ver detalle de un producto

GET /api/productos/<id>/

▸ Ver stock

GET /api/productos/<id>/stock/

🟩 Clientes & Crédito interno
▸ Listar/obtener clientes

GET /api/clientes/
GET /api/clientes/<id>/

▸ Consultar saldo de crédito

GET /api/creditos/saldo/?cliente_id=<id>

Retorna:

{
  "cliente": {
    "id": 1,
    "nombre": "Nombre",
    "rut": "11.111.111-1",
    "cupo_maximo": "500000.00",
    "saldo_actual": "800.00",
    "disponible": "499200.00"
  }
}

🟥 Ventas
▸ Registrar venta

POST /api/ventas/registrar/
Cuerpo esperado:

{
  "cliente_id": 3,
  "items": [
    {"producto_id": 1, "cantidad": 2},
    {"producto_id": 4, "cantidad": 1}
  ]
}

▸ Reportes

GET /api/reportes/ventas/hoy/
GET /api/reportes/ventas/detalle/<id>/

👨‍💻 Desarrollo y estructura interna
✔ Separación por apps:

inventario → productos, categorías, stock

clientes → clientes, crédito, consultas

ventas → ventas, detalle de ventas, reportes

✔ Validación interna en Ventas (admin)

En DetalleVentaInlineFormSet se exige al menos un detalle para evitar ventas “vacías”.

✔ Métodos inteligentes en modelos

Productos tienen:

hay_stock()
descontar_stock()
aumentar_stock()


Clientes tienen lógica de saldo y crédito disponible (vista en API api_credito.py).

🧪 Migraciones, pruebas y datos iniciales

Crear superusuario:

python manage.py createsuperuser


Panel administrativo en:
http://127.0.0.1:8000/admin/

📄 Licencia

Este proyecto es de uso académico y profesional para portafolio del desarrollador.

📬 Autor

Denisse Guzman - Anais Diaz
Backend Developer / Full-stack / Analista Programador
GitHub: Denisse-Guzman