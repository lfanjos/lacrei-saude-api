# 🏥 Lacrei Saúde API

[![CI/CD Pipeline](https://github.com/lfanjos/lacrei-saude-api/actions/workflows/ci.yml/badge.svg)](https://github.com/lfanjos/lacrei-saude-api/actions/workflows/ci.yml)
[![Code Quality](https://github.com/lfanjos/lacrei-saude-api/actions/workflows/quality.yml/badge.svg)](https://github.com/lfanjos/lacrei-saude-api/actions/workflows/quality.yml)
[![Coverage](https://img.shields.io/badge/coverage-55.5%25-yellow.svg)](./COVERAGE_REPORT.md)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/django-6.0+-green.svg)](https://djangoproject.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **API RESTful para gerenciamento de consultas médicas focada em diversidade e inclusão na saúde LGBTQIA+**

## 📋 Sobre o Projeto

A **Lacrei Saúde API** é uma plataforma desenvolvida para facilitar o agendamento e gerenciamento de consultas médicas, com foco especial no atendimento respeitoso e inclusivo à comunidade LGBTQIA+. A API oferece funcionalidades completas para:

- 👥 **Gestão de Profissionais** - Cadastro e gerenciamento de profissionais de saúde
- 📅 **Agendamento de Consultas** - Sistema completo de agendamento e controle
- 🔐 **Autenticação Segura** - JWT + controle de acesso baseado em perfis
- 🛡️ **Segurança Avançada** - OWASP Top 10, rate limiting, sanitização
- 📊 **Monitoramento** - Logs, métricas e análise de performance

## 🚀 Quick Start

### Pré-requisitos

- **Python 3.12+**
- **Docker & Docker Compose**
- **Poetry** (gerenciamento de dependências)
- **Git**

### 🐳 Executar com Docker (Recomendado)

```bash
# Clonar o repositório
git clone https://github.com/lfanjos/lacrei-saude-api.git
cd lacrei-saude-api

# Iniciar os serviços
docker-compose up -d

# Aplicar migrações
docker-compose exec web python manage.py migrate

# Criar superusuário
docker-compose exec web python manage.py createsuperuser

# Acessar a API
open http://localhost:8001/api/v1/
```

### 🐍 Executar Localmente

```bash
# Instalar dependências
poetry install

# Configurar banco de dados
createdb lacrei_saude_db

# Aplicar migrações
poetry run python manage.py migrate

# Iniciar servidor
poetry run python manage.py runserver
```

## 📚 Documentação da API

| Endpoint | Descrição |
|----------|-----------|
| 📖 `/api/docs/` | Documentação Swagger/OpenAPI |
| 🔧 `/api/redoc/` | Documentação ReDoc |
| ⚕️ `/api/v1/profissionais/` | CRUD de Profissionais |
| 📅 `/api/v1/consultas/` | CRUD de Consultas |
| 🔐 `/api/auth/` | Autenticação e Autorização |
| 🛡️ `/api/security/` | Endpoints de Segurança |
| 📊 `/api/monitoring/` | Monitoramento e Métricas |

## 🏗️ Arquitetura

```
📁 lacrei-saude-api/
├── 🔐 authentication/     # Autenticação e autorização
├── ⚕️ profissionais/     # Gestão de profissionais de saúde  
├── 📅 consultas/         # Sistema de consultas
├── 🛡️ lacrei_saude/      # Core da aplicação + segurança
├── 🐳 docker/            # Configurações Docker
├── 🧪 .github/workflows/ # CI/CD pipelines
└── 📊 htmlcov/           # Relatórios de cobertura
```

## 🔬 Qualidade e Testes

### 🧪 Executar Testes

```bash
# Todos os testes
docker-compose exec web pytest

# Com cobertura
docker-compose exec web pytest --cov=. --cov-report=html

# Apenas testes de segurança
docker-compose exec web pytest -m security

# Performance dos testes
docker-compose exec web pytest --benchmark-only
```

### 📊 Métricas de Qualidade

| Métrica | Atual | Meta |
|---------|-------|------|
| **Cobertura de Testes** | 55.5% | 80% |
| **Testes de Segurança** | ✅ 6 módulos | ✅ OWASP Top 10 |
| **Lint Score** | ✅ Flake8 | ✅ PEP 8 |
| **Type Hints** | 🔄 Parcial | ✅ 90% |

### 🛡️ Segurança

- ✅ **OWASP Top 10** - Cobertura completa
- ✅ **Injection Protection** - SQL, NoSQL, Command
- ✅ **Authentication** - JWT + refresh tokens
- ✅ **Authorization** - RBAC + API Keys
- ✅ **Rate Limiting** - Proteção contra força bruta
- ✅ **Input Sanitization** - XSS e validação
- ✅ **Session Security** - Headers de segurança

## 🚀 CI/CD Pipeline

### 🔄 Workflows Automáticos

#### **Pipeline Principal (`.github/workflows/ci.yml`)**
```mermaid
graph LR
    A[🔍 Lint] --> B[🧪 Tests]
    B --> C[🏗️ Build]
    C --> D[🐳 Docker]
    D --> E[🚀 Deploy]
```

#### **Gates de Qualidade (`.github/workflows/quality.yml`)**
```mermaid
graph TD
    A[🎨 Code Style] --> F[📊 Quality Gate]
    B[🔒 Security] --> F
    C[🧮 Complexity] --> F
    D[📚 Documentation] --> F
    E[🏷️ Type Hints] --> F
```

### ✅ Etapas do CI/CD

| Etapa | Ferramenta | Objetivo |
|-------|------------|----------|
| **🔍 Lint** | black, flake8, isort | Qualidade do código |
| **🛡️ Security** | safety, bandit | Vulnerabilidades |
| **🧪 Tests** | pytest + coverage | Funcionalidade |
| **🏗️ Build** | poetry build | Empacotamento |
| **🐳 Docker** | docker build | Containerização |
| **🚀 Deploy** | GitHub Actions | Automação |

### 📊 Badges de Status

Para adicionar badges ao seu README:

```markdown
[![CI/CD](https://github.com/SEU_USUARIO/lacrei-saude-api/actions/workflows/ci.yml/badge.svg)](https://github.com/SEU_USUARIO/lacrei-saude-api/actions)
[![Coverage](https://codecov.io/gh/SEU_USUARIO/lacrei-saude-api/branch/main/graph/badge.svg)](https://codecov.io/gh/SEU_USUARIO/lacrei-saude-api)
```

## 🔧 Configuração de Ambiente

### Variáveis de Ambiente Obrigatórias

```bash
# Django Core
SECRET_KEY=sua-chave-secreta-super-segura
DEBUG=False
ALLOWED_HOSTS=lacrei-saude-api.com,www.lacrei-saude-api.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/lacrei_saude_db

# Security  
CORS_ALLOWED_ORIGINS=https://lacrei-saude.com
JWT_SECRET_KEY=sua-jwt-secret-key
```

### GitHub Secrets (Obrigatórios)

| Secret | Descrição |
|--------|-----------|
| `DJANGO_SECRET_KEY` | Chave secreta do Django |
| `DATABASE_URL` | URL de conexão do banco |
| `DOCKER_USERNAME` | Usuário Docker Hub (opcional) |
| `DOCKER_PASSWORD` | Token Docker Hub (opcional) |

## 👥 Contribuição

### 🔄 Fluxo de Desenvolvimento

1. **Fork** do repositório
2. **Criar branch**: `git checkout -b feature/nova-funcionalidade`
3. **Commit**: `git commit -m "feat: adiciona nova funcionalidade"`
4. **Push**: `git push origin feature/nova-funcionalidade`
5. **Pull Request** com descrição detalhada

### 📏 Padrões de Código

```bash
# Antes de commitar
poetry run black .        # Formatação
poetry run isort .        # Ordenação de imports  
poetry run flake8 .       # Linting
poetry run pytest        # Testes
```

### 📝 Commits Semânticos

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `style:` Formatação
- `refactor:` Refatoração
- `test:` Testes
- `chore:` Tarefas de manutenção

## 🚀 Deploy

### 🐳 Docker Production

```bash
# Build da imagem
docker build -t lacrei-saude-api:latest .

# Run em produção
docker run -d \
  --name lacrei-api \
  -p 8000:8000 \
  -e SECRET_KEY=$SECRET_KEY \
  -e DATABASE_URL=$DATABASE_URL \
  lacrei-saude-api:latest
```

### ☁️ Deploy na AWS/Heroku

Ver documentação específica em [`DEPLOYMENT.md`](./DEPLOYMENT.md)

## 📞 Suporte

- 📧 **Email**: lfanjosus@gmail.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/lfanjos/lacrei-saude-api/issues)
- 📖 **Wiki**: [Documentação Completa](https://github.com/lfanjos/lacrei-saude-api/wiki)

## 📄 Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- **Lacrei Saúde** - Pela missão de inclusão na saúde
- **Comunidade LGBTQIA+** - Pela inspiração e feedback
- **Django Community** - Pela excelente framework
- **Open Source Contributors** - Pelas bibliotecas utilizadas

---

**💜 Desenvolvido com amor para uma saúde mais inclusiva**

![Lacrei Saúde](https://img.shields.io/badge/Lacrei%20Saúde-Inclusão%20na%20Saúde-purple?style=for-the-badge)