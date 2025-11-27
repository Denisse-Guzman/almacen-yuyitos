from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Vista de inicio de sesión.


    (rol cajero / bodeguero / admin):
    - Si GET: muestra formulario simple.
    - Si POST: autentica usuario y redirige.
    """

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        rol = request.POST.get("rol")  # opcional, lo usaremos después

        if not username or not password:
            messages.error(request, "Debe ingresar usuario y contraseña.")
        else:
            user = authenticate(request, username=username, password=password)
            if user is None:
                messages.error(request, "Usuario o contraseña incorrectos.")
            else:
                # validar rol contra grupos 
                if rol == "cajero" and not user.groups.filter(name="Cajero").exists():
                    messages.error(request, "Este usuario no tiene rol de Cajero.")
                elif rol == "bodeguero" and not user.groups.filter(
                    name="Bodeguero"
                ).exists():
                    messages.error(request, "Este usuario no tiene rol de Bodeguero.")
                elif rol == "admin" and not (
                    user.is_superuser or user.groups.filter(name="Admin").exists()
                ):
                    messages.error(request, "Este usuario no tiene rol de Admin.")
                else:
                    # ✅ Autenticado y con rol correcto
                    login(request, user)

                   
                    return redirect("/admin/")

    
    return render(request, "cuentas/login.html")


def logout_view(request):
    """
    Cierra la sesión y vuelve a la pantalla de login.
    """
    logout(request)
    return redirect("login")

