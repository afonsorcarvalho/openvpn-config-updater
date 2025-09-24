#!/bin/bash

# Script wrapper para executar o OpenVPN Config Updater com ambiente virtual
# Este script ativa automaticamente o ambiente virtual antes de executar o updater

# Obter diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verificar se ambiente virtual existe
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "❌ Ambiente virtual não encontrado em $SCRIPT_DIR/venv"
    echo "Execute primeiro: sudo ./install.sh"
    exit 1
fi

# Ativar ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source "$SCRIPT_DIR/venv/bin/activate"

# Verificar se ativação foi bem-sucedida
if [ $? -ne 0 ]; then
    echo "❌ Erro ao ativar ambiente virtual"
    exit 1
fi

# Executar o updater com todos os argumentos passados
echo "🚀 Executando OpenVPN Config Updater..."
python3 "$SCRIPT_DIR/openvpn_certificate_updater.py" "$@"

# Capturar código de saída
EXIT_CODE=$?

# Desativar ambiente virtual
deactivate

# Retornar código de saída do script Python
exit $EXIT_CODE
