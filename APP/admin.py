from django.contrib import admin
from .models import login, Cleintes

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
# Register your models here.
