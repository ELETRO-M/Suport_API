from datetime import datetime

x = input("data_inicio (YYYY-MM-DD HH:MM): ")
y = input("data_fim (YYYY-MM-DD HH:MM): ")

data_inicio = datetime.strptime(x, "%Y-%m-%d %H:%M")
data_fim = datetime.strptime(y, "%Y-%m-%d %H:%M")

diferenca = data_fim - data_inicio

horas = diferenca.total_seconds() / 3600
x = horas-datetime.now().hour
print(horas,x)