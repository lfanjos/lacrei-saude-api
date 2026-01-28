# Docker Setup - Lacrei Saúde API

## 🐳 Comandos Docker

### Configuração Inicial

1. **Instalar Docker Desktop** (se ainda não tiver):
   - [Docker Desktop para Windows](https://docs.docker.com/desktop/install/windows-install/)
   - Habilitar integração WSL 2

2. **Usar Makefile** (recomendado):
   ```bash
   make help  # Ver todos os comandos
   ```

### Desenvolvimento

```bash
# Iniciar ambiente completo
make dev

# Ver logs
make logs

# Parar serviços
make down

# Executar migrações
make migrate

# Abrir shell Django
make shell
```

### Comandos Manuais

```bash
# Desenvolvimento
docker-compose -f docker-compose.dev.yml up -d

# Produção
docker-compose up -d

# Parar tudo
docker-compose down

# Rebuild
docker-compose build --no-cache
```

## 🔧 Estrutura Docker

### Arquivos:
- `Dockerfile` - Imagem da aplicação
- `docker-compose.yml` - Produção (com Redis)
- `docker-compose.dev.yml` - Desenvolvimento
- `docker-entrypoint.sh` - Script de inicialização
- `.dockerignore` - Arquivos ignorados no build

### Serviços:
- **web**: Aplicação Django (porta 8000)
- **db**: PostgreSQL (porta 5432)
- **redis**: Cache/sessões (porta 6379)

### Volumes:
- `postgres_data` - Dados do PostgreSQL
- `static_volume` - Arquivos estáticos
- `media_volume` - Upload de arquivos
- `redis_data` - Dados do Redis

## 📋 URLs Locais

- **API**: http://localhost:8000/
- **Admin**: http://localhost:8000/admin/
- **Health Check**: http://localhost:8000/health/

## 🔍 Troubleshooting

### Problemas Comuns:

1. **Banco não conecta**:
   ```bash
   make db-logs  # Ver logs do PostgreSQL
   ```

2. **Porta ocupada**:
   ```bash
   sudo lsof -i :8000  # Ver processo na porta 8000
   ```

3. **Volumes corrompidos**:
   ```bash
   make clean  # Limpar tudo e recomeçar
   ```

4. **Rebuild completo**:
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   make dev
   ```

### Logs:
```bash
# Logs da aplicação
docker-compose logs -f web

# Logs do banco
docker-compose logs -f db

# Todos os logs
docker-compose logs -f
```

### Backup/Restore:
```bash
# Backup
make backup

# Restore
make restore FILE=backup_20240127.sql
```