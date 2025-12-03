from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages

# Constantes de roles (en minúsculas)
ROLE_CAJERO = "cajero"
ROLE_BODEGUERO = "bodeguero"
ROLE_ADMIN = "admin"


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # normaliza el rol a minúsculas
        rol_seleccionado = (request.POST.get("rol") or "").strip().lower()

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Usuario o contraseña incorrectos.")
            return render(request, "cuentas/login.html")

        if not user.is_active:
            messages.error(request, "Usuario inactivo.")
            return render(request, "cuentas/login.html")

        # Loguea al usuario
        login(request, user)

        # nombres de grupos del usuario en minúsculas
        grupos = {g.lower() for g in user.groups.values_list("name", flat=True)}

        # Si el usuario selecciona un rol, debe pertenecer a ese grupo
        if rol_seleccionado and rol_seleccionado not in grupos:
            logout(request)
            messages.error(
                request,
                "No tienes permisos para ingresar como ese rol."
            )
            return render(request, "cuentas/login.html")

        # Redirección según rol (prioridad Admin > Bodeguero > Cajero)
        if ROLE_ADMIN in grupos:
            return redirect("dashboard_admin")
        elif ROLE_BODEGUERO in grupos:
            return redirect("dashboard_bodega")
        elif ROLE_CAJERO in grupos:
            return redirect("dashboard_caja")

        # Si llega aquí, el usuario no tiene ninguno de los 3 roles
        logout(request)
        messages.error(
            request,
            "Tu usuario no tiene un rol asignado. Contacta al administrador."
        )
        return render(request, "cuentas/login.html")

    # GET → mostrar formulario
    return render(request, "cuentas/login.html")


def _en_grupo(nombre_grupo):
    def check(user):
        return (
            user.is_authenticated
            and user.groups.filter(name__iexact=nombre_grupo).exists()
        )
    return check


@login_required
@user_passes_test(_en_grupo("Cajero"))
def dashboard_caja(request):
    return render(request, "cuentas/dashboard_caja.html")


@login_required
@user_passes_test(_en_grupo("Bodeguero"))
def dashboard_bodega(request):
    return render(request, "cuentas/dashboard_bodega.html")


@login_required
@user_passes_test(_en_grupo("Admin"))
def dashboard_admin(request):
    return render(request, "cuentas/dashboard_admin.html")


def logout_view(request):
    logout(request)
    return redirect("login")

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages



def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        rol_seleccionado = (request.POST.get("rol") or "").strip().lower()

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Usuario o contraseña incorrectos.")
            return render(request, "cuentas/login.html")

        if not user.is_active:
            messages.error(request, "Usuario inactivo.")
            return render(request, "cuentas/login.html")

        login(request, user)
        grupos = {g.lower() for g in user.groups.values_list("name", flat=True)}

        if rol_seleccionado and rol_seleccionado not in grupos:
            logout(request)
            messages.error(request, "No tienes permisos para ingresar como ese rol.")
            return render(request, "cuentas/login.html")

        # Redirección según rol
        if "admin" in grupos:
            return redirect("dashboard_admin")
        elif "bodeguero" in grupos:
            return redirect("dashboard_bodega")
        elif "cajero" in grupos:
            return redirect("dashboard_caja")

        logout(request)
        messages.error(request, "Tu usuario no tiene un rol asignado.")
        return render(request, "cuentas/login.html")

    return render(request, "cuentas/login.html")


@login_required
def dashboard_caja(request):
    # Verificar que el usuario tenga rol Cajero o Admin
    grupos = [g.name.lower() for g in request.user.groups.all()]
    if 'cajero' not in grupos and 'admin' not in grupos:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('login')
    
    return render(request, "cuentas/dashboard_caja.html")


@login_required
def dashboard_bodega(request):
    # Verificar que el usuario tenga rol Bodeguero o Admin
    grupos = [g.name.lower() for g in request.user.groups.all()]
    if 'bodeguero' not in grupos and 'admin' not in grupos:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('login')
    
    return render(request, "cuentas/dashboard_bodega.html")


@login_required
def dashboard_admin(request):
    # Verificar que el usuario tenga rol Admin
    grupos = [g.name.lower() for g in request.user.groups.all()]
    if 'admin' not in grupos:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('login')
    
    return render(request, "cuentas/dashboard_admin.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Sesión cerrada exitosamente.")
    return redirect("login")



from django.contrib.auth.decorators import login_required, user_passes_test

@login_required
def ingreso_mercaderia(request):
    """Vista para el ingreso de mercadería - Solo Bodeguero o Admin"""
    grupos = [g.name.lower() for g in request.user.groups.all()]
    
    if 'bodeguero' not in grupos and 'admin' not in grupos:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('login')
    
    return render(request, "bodega/ingreso_mercaderia.html")