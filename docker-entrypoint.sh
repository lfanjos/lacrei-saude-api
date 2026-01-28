#!/bin/bash
# Docker entrypoint script para Lacrei Saúde API
# ===============================================

set -e

# Aguardar o banco de dados estar disponível
echo "Aguardando banco de dados..."
until nc -z $DB_HOST $DB_PORT; do
  echo "Aguardando conexão com banco..."
  sleep 1
done
echo "Banco de dados disponível!"

# Executar migrações
echo "Executando migrações..."
python manage.py migrate --noinput

# Coletar arquivos estáticos (apenas se não for desenvolvimento)
if [ "$DEBUG" != "True" ]; then
    echo "Coletando arquivos estáticos..."
    python manage.py collectstatic --noinput
else
    echo "Pulando collectstatic em modo DEBUG"
fi

# Executar comando passado como argumento
echo "Iniciando aplicação..."
exec "$@"