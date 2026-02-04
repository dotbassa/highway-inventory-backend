#!/bin/bash

set -e

echo "Iniciando deployment de Highway Inventory API..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
NGINX_SITE="domain.cl"
DOMAIN="domain.cl"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if [ "$EUID" -ne 0 ]; then 
    print_error "Este script debe ejecutarse como root (usa sudo)"
    exit 1
fi

print_message "Verificando requisitos previos..."

if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose no está instalado"
    exit 1
fi

if ! command -v nginx &> /dev/null; then
    print_error "Nginx no está instalado"
    exit 1
fi

print_message "Todos los requisitos están instalados"

print_message "Directorio de la aplicación: $APP_DIR"

if [ ! -f "$APP_DIR/.env" ]; then
    print_error "No se encontró archivo .env en $APP_DIR"
    print_message "Por favor, crea el archivo .env antes de ejecutar este script"
    exit 1
fi

print_message "Construyendo y levantando contenedores..."
cd "$APP_DIR"

print_message "Deteniendo contenedores anteriores (si existen)..."
docker-compose down 2>/dev/null || true

print_message "Construyendo imágenes y levantando servicios..."
docker-compose up -d --build

print_message "Esperando a que los contenedores estén listos..."
sleep 5

if docker-compose ps | grep -q "Up"; then
    print_message "✓ Contenedores están corriendo"
else
    print_error "Los contenedores no están corriendo correctamente"
    docker-compose logs --tail=50
    exit 1
fi

print_message "Verificando logs de inicio..."
sleep 3
LOG_ERRORS=$(docker-compose logs api | grep -i "error\|exception\|failed" | grep -v "INFO" | grep -v "Starting" || true)
if [ -n "$LOG_ERRORS" ]; then
    print_warning "Se detectaron posibles errores en los logs:"
    echo "$LOG_ERRORS" | tail -5
fi

print_message "Verificando que la API responde..."
MAX_RETRIES=12
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost:8000/api/public/v1/health/ > /dev/null 2>&1; then
        print_message "✓ API está respondiendo correctamente"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            print_message "Intento $RETRY_COUNT/$MAX_RETRIES - Esperando 5 segundos..."
            sleep 5
        fi
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "La API no responde después de $MAX_RETRIES intentos"
    print_message "Últimos 30 logs de la API:"
    docker-compose logs --tail=30 api
    print_message ""
    print_message "Para ver logs en tiempo real: docker-compose logs -f api"
    exit 1
fi

echo ""
print_message "======================"
print_message "Deployment completado"
print_message "======================"
echo ""
print_message "Para ver logs:"
echo "   cd $APP_DIR"
echo "   docker-compose logs -f"
echo ""
print_message "Para detener los contenedores:"
echo "   cd $APP_DIR"
echo "   docker-compose down"
echo ""
