from django.contrib.auth.models import Group


def en_grupo(nombre_grupo: str):
    """
    Devuelve una función que verifica si el usuario está en el grupo dado.
    """
    def check(user):
        return user.is_authenticated and user.groups.filter(name=nombre_grupo).exists()
    return check


def es_cajero_o_admin(user):
    return user.is_authenticated and user.groups.filter(name__in=["Cajero", "Admin"]).exists()


def es_bodeguero_o_admin(user):
    return user.is_authenticated and user.groups.filter(name__in=["Bodeguero", "Admin"]).exists()


def es_admin(user):
    return user.is_authenticated and user.groups.filter(name="Admin").exists()
