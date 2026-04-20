from django.contrib import admin
from .models import login as User

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


# Register your models here.
