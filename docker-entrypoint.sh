#!/bin/bash
# Docker entrypoint script para Lacrei Saúde API
# ===============================================

set -e

# Aguardar o banco de dados estar disponível (apenas se configurado)
DB_HOST=${DB_HOST:-""}
DB_PORT=${DB_PORT:-""}

if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
  echo "Aguardando banco de dados em $DB_HOST:$DB_PORT..."
  until nc -z "$DB_HOST" "$DB_PORT"; do
    echo "Aguardando conexão com banco..."
    sleep 1
  done
  echo "Banco de dados disponível!"
else
  echo "Variáveis DB_HOST/DB_PORT não definidas, pulando verificação do banco."
fi

# Executar migrações (apenas se não for um teste simples)
if [ "$1" != "python" ] || [ "$2" != "--version" ]; then
  echo "Executando migrações..."
  python manage.py migrate --noinput
else
  echo "Teste simples detectado, pulando migrações."
fi

# Coletar arquivos estáticos (apenas se não for desenvolvimento ou teste simples)
if [ "$1" != "python" ] || [ "$2" != "--version" ]; then
  if [ "$DEBUG" != "True" ]; then
      echo "Coletando arquivos estáticos..."
      python manage.py collectstatic --noinput
  else
      echo "Pulando collectstatic em modo DEBUG"
  fi
else
  echo "Teste simples detectado, pulando collectstatic."
fi

# Executar comando passado como argumento
echo "Iniciando aplicação..."
exec "$@"