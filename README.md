# CLACS Suporte API

Projeto Django + Django REST Framework criado a partir do documento `routes_suporte.pdf`.

## Stack

- Django
- Django REST Framework
- JWT com `simplejwt`
- PostgreSQL

## Estrutura principal

- `apps/usuarios`: autenticação, perfil e técnicos
- `apps/clientes`: gestão de clientes
- `apps/contratos`: contratos
- `apps/intervencoes`: intervenções, comentários, anexos e horas
- `apps/relatorios`: dashboards e relatórios
- `apps/notificacoes`: notificações
- `apps/sistema`: configurações do sistema
- `apps/configuracoes`: respostas, paginação, permissões e utilitários partilhados

## Como arrancar

1. Criar ambiente virtual.
2. Instalar dependências:
   `pip install -r requirements.txt`
3. Criar o ficheiro `.env` com base no `.env.example`.
4. Executar as migrações para gerar o ficheiro `db.sqlite3`.
5. Executar:
   `python manage.py makemigrations`
   `python manage.py migrate`
   `python manage.py createsuperuser`
   `python manage.py runserver`

## Base da API

- Base path: `/api/v1`
- Documentação OpenAPI: `/api/schema/`
- Swagger UI: `/api/docs/`

## Notas

- As respostas seguem o envelope `{ success, data, message, pagination }`.
- O projeto usa um modelo de utilizador customizado com perfis `admin`, `tecnico` e `cliente`.
- O PDF também descreve rotas de frontend; aqui foi implementada a camada de backend.
