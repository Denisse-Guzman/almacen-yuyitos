from django.db import migrations


def crear_grupos_y_asignar(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    
    # Crear grupos
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    bodeguero_group, _ = Group.objects.get_or_create(name='Bodeguero')
    cajero_group, _ = Group.objects.get_or_create(name='Cajero')
    
    # Asignar grupo Admin al primer superusuario que encuentre
    superuser = User.objects.filter(is_superuser=True).first()
    if superuser:
        superuser.groups.add(admin_group)


def revertir(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['Admin', 'Bodeguero', 'Cajero']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(crear_grupos_y_asignar, revertir),
    ]