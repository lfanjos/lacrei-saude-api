# Makefile para Lacrei Saúde API
# ==============================

.PHONY: help build dev prod down clean logs test migrate shell

# Variáveis
PROJECT_NAME=lacrei-saude-api
DEV_COMPOSE_FILE=docker-compose.dev.yml
PROD_COMPOSE_FILE=docker-compose.yml

help: ## Mostrar esta ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Construir imagem Docker
	docker build -t $(PROJECT_NAME):latest .

dev: ## Iniciar ambiente de desenvolvimento
	docker-compose -f $(DEV_COMPOSE_FILE) up -d
	@echo "Aplicação rodando em: http://localhost:8000"
	@echo "Admin: http://localhost:8000/admin"

prod: ## Iniciar ambiente de produção
	docker-compose -f $(PROD_COMPOSE_FILE) up -d

down: ## Parar todos os serviços
	docker-compose -f $(DEV_COMPOSE_FILE) down
	docker-compose -f $(PROD_COMPOSE_FILE) down

clean: ## Limpar volumes e imagens não utilizadas
	docker-compose -f $(DEV_COMPOSE_FILE) down -v
	docker-compose -f $(PROD_COMPOSE_FILE) down -v
	docker system prune -f

logs: ## Visualizar logs da aplicação
	docker-compose -f $(DEV_COMPOSE_FILE) logs -f web

db-logs: ## Visualizar logs do banco
	docker-compose -f $(DEV_COMPOSE_FILE) logs -f db

test: ## Executar testes
	docker-compose -f $(DEV_COMPOSE_FILE) exec web python manage.py test

migrate: ## Executar migrações
	docker-compose -f $(DEV_COMPOSE_FILE) exec web python manage.py migrate

shell: ## Abrir shell Django
	docker-compose -f $(DEV_COMPOSE_FILE) exec web python manage.py shell

bash: ## Abrir bash no container
	docker-compose -f $(DEV_COMPOSE_FILE) exec web bash

db-shell: ## Conectar ao PostgreSQL
	docker-compose -f $(DEV_COMPOSE_FILE) exec db psql -U postgres -d lacrei_saude_db

backup: ## Fazer backup do banco
	docker-compose -f $(DEV_COMPOSE_FILE) exec db pg_dump -U postgres lacrei_saude_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Restaurar backup (usar: make restore FILE=backup.sql)
	docker-compose -f $(DEV_COMPOSE_FILE) exec -T db psql -U postgres lacrei_saude_db < $(FILE)

install: ## Instalar dependências localmente
	poetry install

run-local: ## Executar localmente (sem Docker)
	poetry run python manage.py runserver

test-local: ## Executar testes localmente
	poetry run python manage.py test

format: ## Formatar código
	poetry run black .
	poetry run isort .

lint: ## Verificar qualidade do código
	poetry run flake8 .

check: ## Verificar se há problemas
	poetry run python manage.py check