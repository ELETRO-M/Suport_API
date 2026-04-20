from django.contrib import admin
<<<<<<< HEAD
<<<<<<< HEAD
from .models import login as User
=======
from .models import login,Cleintes
>>>>>>> 89caac7 (V1.1 resolvido bugs da auth)
=======
from .models import login, Cleintes
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf

@admin.register(login)
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
<<<<<<< HEAD

=======
@admin.register(Cleintes)
class ClienteAdmin(admin.ModelAdmin):
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
    search_fields = ('email', 'empresa', 'status')
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf
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
