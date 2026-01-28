-- Script de inicialização do banco PostgreSQL
-- ============================================

-- Garantir que o banco existe
SELECT 'CREATE DATABASE lacrei_saude_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lacrei_saude_db');

-- Configurar extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Configurar timezone
SET timezone = 'America/Sao_Paulo';