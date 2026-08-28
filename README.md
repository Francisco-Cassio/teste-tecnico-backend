# ⚙️ API de Gerenciamento de Consultas Médicas — Backend

API RESTful para gestão de clínicas médicas, especialistas, agendas e agendamento/cancelamento de consultas em tempo real, desenvolvida com **Django REST Framework**, **PostgreSQL** e **Docker**.

> [IMPORTANT !!!]
>
> **Interface Frontend (Vue 3):** Este backend possui uma interface web moderna e reativa desenvolvida em **Vue 3 + Tailwind CSS + Pinia** disponível em:
> 👉 **[Repositório Frontend (Vue 3 + Vite)](https://github.com/Francisco-Cassio/teste-tecnico-frontend)**

---

## 🚀 Tecnologias Utilizadas

O backend foi estruturado utilizando ferramentas modernas do ecossistema Python:

| Tecnologia | Finalidade |
| :--- | :--- |
| **Python 3.11+** | Linguagem principal do projeto |
| **Django** | Framework web principal |
| **Django REST Framework (DRF)** | Construção da API REST |
| **Simple JWT** | Autenticação baseada em tokens JWT |
| **drf-spectacular** | Documentação interativa OpenAPI 3.0 (Swagger UI e ReDoc) |
| **Django Filter** | Filtros dinâmicos via Query Parameters |
| **Django CORS Headers** | Gerenciamento de permissões de origens (CORS) |
| **Docker & Docker Compose** | Conteinerização e padronização de ambiente |
| **Gunicorn** | Servidor de aplicação WSGI em produção |
| **PostgreSQL 16+** | Banco de dados relacional principal |

---

## 🏗️ Arquitetura do Projeto

```text
teste-tecnico-backend/
├── core/                       # Configurações globais do Django
│   ├── settings.py             # Configurações de banco, JWT, CORS, DRF e Spectacular
│   ├── urls.py                 # Rotas principais, endpoints JWT e documentação OpenAPI
│   ├── wsgi.py / asgi.py       # Pontos de entrada para servidores WSGI/ASGI
├── consultas/                  # Aplicação principal de domínio
│   ├── admin.py                # Customização do Django Admin e auditoria de Soft Delete
│   ├── models.py               # Entidades de domínio e Soft Delete
│   ├── serializers.py          # Serializadores DRF com validações e representações aninhadas
│   ├── views.py                # ViewSets com actions de agendar/cancelar, filtros e locks
│   ├── services.py             # Regras de negócio, cálculo de vagas e geração em lote O(1)
│   ├── permissions.py          # Controle de Acesso Baseado em Papéis
│   ├── urls.py                 # Roteamento dos ViewSets via DefaultRouter
│   ├── tests.py                # Testes automatizados
│   └── migrations/             # Migrações versionadas do banco de dados
├── Dockerfile                  # Imagem Docker otimizada com Python 3.11-slim
├── docker-compose.yml          # Orquestração do PostgreSQL (com Healthcheck) e API
├── requirements.txt            # Dependências do projeto
└── .env.example                # Template de variáveis de ambiente
```

---

## 🎯 Recursos Implementados

### 👑 1. Painel Administrativo com Django Admin
O painel administrativo foi totalmente customizado para fornecer controle e auditoria completa da clínica.

#### Funcionalidades disponíveis:
* **Gestão de Usuários:** Exibição e edição direta do `tipo_acesso` (`cliente` ou `interno`).
* **Auditoria de Soft Delete:** Uso de `all_objects` para que os administradores visualizem tanto registros ativos quanto inativos.
* **Filtros e Buscas Rápidas:** Filtro por especialidade, status da consulta, data, especialista e flag de atividade.
* **Campos Calculados e Ordenação:** Exibição do especialista vinculado ao horário e ordenação cronológica.

---

### 🔐 2. Autenticação com JWT
Autenticação stateless baseada em **JSON Web Tokens** com distinção de papéis:
* **Perfil Interno (`interno`):** Permissão total para cadastrar, editar e excluir especialistas e agendas.
* **Perfil Cliente (`cliente`):** Acesso de leitura aos especialistas/horários disponíveis e permissão para agendar/cancelar suas próprias consultas.
* **Público (Não autenticado):** Leitura de especialistas e horários para consulta.

#### Exemplo de autenticação:
* **Obter Token:** `POST /api/token/` com `{"username": "...", "password": "..."}`
* **Atualizar Token:** `POST /api/token/refresh/` com `{"refresh": "..."}`
* **Utilização:** Header `Authorization: Bearer <seu_token_access>`

---

### 🧠 3. Camada de Serviços (`services.py`)
Centraliza as regras matemáticas e operacionais para geração de horários, isolando a lógica de negócio das views.

#### Regras implementadas:
* 🗓️ **Validação de Datas:** Garante que a data inicial seja menor ou igual à data final (`data_inicio <= data_fim`).
* ⏰ **Controle de Horário e Vagas:** Calcula a duração exata de cada consulta dividindo o intervalo (`hora_inicio` até `hora_encerramento`) pela quantidade de `vagas_por_dia`.
* ⚡ **Performance & Eliminação de N+1 Queries:** Busca em lote todos os horários já existentes no intervalo em **uma única query**, convertendo para um `set` de tuplas para validação em memória com complexidade $O(1)$.
* 📦 **Criação Atômica em Lote:** Utiliza `Horario.objects.bulk_create()` dentro de transação atômica (`transaction.atomic`).

#### Resposta de erro:
Lança `ValueError` ou `ValidationError` com mensagens descritivas caso haja incoerência nas datas ou horários.

---

### 🔄 4. Serializadores Avançados
Validação de entrada rigorosa e transformação de saída limpa.

* ✍️ **Escrita (POST / PUT / PATCH):**
  * Validações cruzadas de horários (`hora_inicio < hora_encerramento`).
  * `dias_semana` tipado como lista de inteiros (0 a 6).
  * Vagas diárias estritamente positivas (`vagas_por_dia > 0`).
* 📖 **Leitura (GET):**
  * `to_representation` customizado para aninhar dados do Especialista dentro da Agenda e dados da Agenda/Cliente dentro do Horário.
  * Formatação limpa de horas no padrão `HH:MM`.

---

### 🛡️ 5. Concorrência e Lock Pessimista (`select_for_update`)
* Prevenção de **Race Conditions**: No momento do agendamento ou cancelamento, a linha do horário no banco é bloqueada via `select_for_update()` dentro de uma transação `@transaction.atomic`.
* Impede que dois pacientes reservem a mesma vaga simultaneamente.

---

### 🗑️ 6. Soft Delete (Exclusão Lógica)
* `SoftDeleteModel` com campo `ativo` indexado (`db_index=True`).
* Exclusão em cascata inteligente: inativar um especialista inativa suas agendas; inativar uma agenda inativa seus horários disponíveis.
* `UniqueConstraint` condicional no PostgreSQL para garantir unicidade apenas entre registros ativos.

---

### 🗓️ 7. Cancelamento de Consultas
* Endpoint dedicado `POST /api/horarios/{id}/cancelar/`.
* **Regra de Autorização:** Clientes só podem cancelar consultas agendadas por eles mesmos; usuários internos podem cancelar qualquer agendamento.
* **Validação Temporal:** Bloqueio de cancelamento ou agendamento retroativo para datas/horas passadas usando `timezone.localtime()`.

---

## 🗺️ Endpoints da API

| Método | Endpoint | Descrição | Permissão |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/token/` | Obtenção de par de tokens JWT e dados do usuário | Público |
| `POST` | `/api/token/refresh/` | Renovação do Token de Acesso JWT | Público |
| `GET` | `/api/auth/me/` | Obter dados do usuário autenticado | Requer Autenticação |
| `POST` | `/api/auth/registro/` | Cadastro de novo usuário paciente (cliente) | Público |
| `GET` | `/api/especialistas/` | Listar especialistas cadastrados | Aberto / Leitura |
| `POST` | `/api/especialistas/` | Cadastrar novo especialista | Requer `INTERNO` |
| `GET` | `/api/especialistas/{id}/` | Detalhes de um especialista | Aberto / Leitura |
| `PUT/PATCH` | `/api/especialistas/{id}/` | Atualizar dados de um especialista | Requer `INTERNO` |
| `DELETE` | `/api/especialistas/{id}/` | Exclusão lógica (Soft Delete) de especialista | Requer `INTERNO` |
| `GET` | `/api/agendas/` | Listar agendas cadastradas | Aberto / Leitura |
| `POST` | `/api/agendas/` | Criar agenda (Gera horários para os próximos 30 dias) | Requer `INTERNO` |
| `GET` | `/api/agendas/{id}/` | Detalhes de uma agenda | Aberto / Leitura |
| `DELETE` | `/api/agendas/{id}/` | Exclusão lógica de agenda e horários livres | Requer `INTERNO` |
| `GET` | `/api/horarios/` | Listar horários de atendimento (com filtros) | Aberto / Leitura |
| `GET` | `/api/horarios/minhas_consultas/` | Listar consultas reservadas do usuário autenticado | Requer Autenticação |
| `POST` | `/api/horarios/{id}/agendar/` | Reservar vaga de consulta disponível | Requer Autenticação |
| `POST` | `/api/horarios/{id}/cancelar/` | Cancelar agendamento e liberar vaga | Requer Autenticação |
| `GET` | `/api/docs/` | Documentação interativa Swagger UI | Público |
| `GET` | `/api/redoc/` | Documentação interativa ReDoc | Público |

---

## 🔍 Filtros Dinâmicos

Na listagem de horários (`GET /api/horarios/`), é possível combinar os seguintes parâmetros via Query String:

* **Filtrar por Médico / Especialista:**
  ```http
  GET /api/horarios/?especialista_id=1
  ```
* **Filtrar por Data:**
  ```http
  GET /api/horarios/?data_consulta=2026-08-25
  ```
* **Filtrar por Status:**
  ```http
  GET /api/horarios/?status=disponivel
  ```
* **Filtro Combinado:**
  ```http
  GET /api/horarios/?especialista_id=1&data_consulta=2026-08-25&status=disponivel
  ```

---

## 📦 Instalação e Execução Local

### 🐳 Opção 1 — Docker (Recomendado)

#### Pré-requisitos:
* Docker e Docker Compose instalados.

#### Executar o projeto:
1. Clone o repositório e acesse a pasta raiz:
   ```bash
   git clone https://github.com/Francisco-Cassio/teste-tecnico-backend.git
   cd teste-tecnico-backend
   ```
2. Crie o arquivo `.env` a partir do exemplo:
   ```bash
   cp .env.example .env
   ```
3. Suba os containers com build:
   ```bash
   docker compose up --build -d
   ```
4. Aplique as migrações e crie um superusuário:
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```
5. O backend estará acessível em `http://localhost:8000`.

---

### 💻 Opção 2 — Ambiente Python Local

#### 1️⃣ Criar ambiente virtual:
* **Windows:**
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
* **Linux/macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

#### 2️⃣ Configurar variáveis de ambiente e dependências:
```bash
cp .env.example .env
pip install -r requirements.txt
```

#### 3️⃣ Executar migrações:
```bash
python manage.py migrate
```

#### 4️⃣ Criar superusuário:
```bash
python manage.py createsuperuser
```

#### 5️⃣ Iniciar servidor:
```bash
python manage.py runserver
```

---

## 🧪 Execução dos Testes Automatizados

O projeto conta com **testes automatizados** cobrindo serviços, models, autenticação, concorrência, soft delete e views:

```bash
# Via Docker:
docker compose exec web python manage.py test

# Localmente:
python manage.py test
```

---

## 🌐 Ambiente de Produção & Links Úteis

* 🔗 **URL Base da API:** `http://localhost:8000/api/`
* 🔗 **Painel Administrativo:** `http://localhost:8000/admin/`
* 🔗 **Documentação Swagger:** `http://localhost:8000/api/docs/`
* 🔗 **Documentação ReDoc:** `http://localhost:8000/api/redoc/`

---

## 🔑 Credenciais de Demonstração (Sugestão para Testes)

| Tipo de Usuário | Username | Senha | Perfil | Permissões |
| :--- | :--- | :--- | :--- | :--- |
| **Administrador** | `admin` | `admin123` | `interno` | Acesso total ao Django Admin e API |
| **Secretária / Atendente** | `recepcao` | `senha123` | `interno` | Criar/Editar Especialistas e Agendas |
| **Paciente** | `paciente_joao` | `senha123` | `cliente` | Visualizar horários, agendar e cancelar consultas próprias |

---

## 📌 Observações Técnicas
* **Garantia Transacional e ACID:** Uso de `@transaction.atomic` com locks pessimistas (`select_for_update`) sem *outer joins*, garantindo compatibilidade nativa com o PostgreSQL e prevenindo *race conditions* sob acessos concorrentes.
* **Paginação Determinística:** QuerySets com ordenação explícita (`order_by`), eliminando inconsistências e warnings na paginação de registros em listas extensas.
* **Respeito ao Fuso Horário:** Validações de data e hora baseadas em `django.utils.timezone.localtime()`, evitando discrepâncias entre servidores em UTC e o fuso local da clínica.
* **Orquestração e Inicialização Segura:** Container Django configurado com `depends_on` condicional ao `healthcheck` do PostgreSQL (`pg_isready`), garantindo que a aplicação só inicie após o banco estar 100% pronto para conexões.