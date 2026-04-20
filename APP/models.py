from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from datetime import *
class Base(models.Model):
    create_data= models.DateTimeField(auto_now_add=True)
    update_data= models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True 
class login(Base):
    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    empresa = models.CharField(max_length=100)
    perfil = models.CharField(max_length=100, default='cliente', 
    choices=[('cliente', 'Cliente'), ('admin', 'Admin'), ('Tecnico', 'Tecnico')])
    contact = models.CharField(max_length=20, blank=True, null=True , default='')
    password = models.CharField(max_length=128)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def save(self, *args, **kwargs):
        # só faz hash se não estiver já hasheada
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)


    def __str__(self):
        return self.username
# Ainda esta a processar a parte de contratos, falta calcular o valor total com base no tipo de contrato e horas contratadas, e também a parte de horas disponiveis para o cliente.
class Cleintes(Base):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    empresa = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    nif = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,
        default='ativo',
        choices=[('ativo', 'Ativo'), ('inativo', 'Inativo')]
    )
    endereco = models.CharField(max_length=200)
    password = models.CharField(max_length=128)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
"""
class contarctos(Base):
    cliente = models.ForeignKey(Cleintes, on_delete=models.CASCADE)
    descricao = models.TextField()
    tipo = models.CharField(max_length=20, default='serviço', 
    choices=[('horas', 'Horas'), ('mensal', 'Mensal'), ('anual', 'Anual')])
    data_inicio = models.DateField(auto_now_add=True)
    hora_contratada = models.IntegerField()
    data_fim = models.DateField()
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='ativo', choices=[('ativo', 'Ativo'), ('inativo', 'Inativo')])
    def calcular_valor_total(self):
        data= self.data_fim - self.data_inicio
        horas= data.total_seconds() / 3600
        horasdisponiveis = horas - time.now().hour
    """    


       


