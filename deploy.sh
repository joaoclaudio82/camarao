#!/bin/bash
# ─────────────────────────────────────────────────────────
#  ShrimpScan – Script de deploy (Railway / Render / VPS)
# ─────────────────────────────────────────────────────────
set -e

echo "🦐  ShrimpScan Deploy Script v2.1"
echo "=================================="

# 1. Verificar Docker
if ! command -v docker &>/dev/null; then
  echo "❌ Docker não encontrado. Instale em: https://docs.docker.com/get-docker/"
  exit 1
fi

# 2. Verificar docker-compose
if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
  echo "❌ docker-compose não encontrado."
  exit 1
fi

# 3. Criar diretórios de dados persistentes
mkdir -p data uploads
echo "✅ Diretórios criados."

# 4. Build e start
echo "🔨 Fazendo build da imagem..."
docker compose build --no-cache

echo "🚀 Iniciando container..."
docker compose up -d

echo ""
echo "✅ ShrimpScan rodando em: http://localhost:8000"
echo "📋 Logs: docker compose logs -f"
echo "🛑 Parar: docker compose down"
echo ""

# 5. Aguardar healthcheck
echo "⏳ Aguardando serviço iniciar..."
for i in {1..12}; do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Serviço saudável!"
    break
  fi
  sleep 5
done
