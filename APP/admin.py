from django.contrib import admin
<<<<<<< HEAD
from .models import login as User
=======
from .models import login,Cleintes
>>>>>>> 89caac7 (V1.1 resolvido bugs da auth)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
     'id',
     'username',
     'email',
     'empresa',
     'password',
     'perfil',
     'contact', 
     'create_data',
     'update_data'
          )
    search_fields = ('email', 'empresa', 'perfil')

<<<<<<< HEAD

# Register your models here.
=======
@admin.register(Cleintes)
class ClientesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'email',
        'empresa',
        'contact',
        'nif',
        'status',
        'endereco',
        'password',
        'create_data',
        'update_data'
    )
    search_fields = ('email', 'name', 'empresa')
>>>>>>> 89caac7 (V1.1 resolvido bugs da auth)
