#!/bin/bash

# Script de instalação para OpenVPN Certificate Updater
# Este script facilita a instalação e configuração do sistema

set -e

echo "=== OpenVPN Certificate Updater - Instalação ==="
echo

# Verificar se está sendo executado como root
if [ "$EUID" -ne 0 ]; then
    echo "Este script deve ser executado como root (use sudo)"
    exit 1
fi

# Verificar se Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "Python 3 não está instalado. Instalando..."
    apt update
    apt install -y python3 python3-pip python3-venv python3-full
fi

# Verificar se python3-venv está disponível
if ! python3 -m venv --help &> /dev/null; then
    echo "python3-venv não está disponível. Instalando..."
    apt install -y python3-venv python3-full
fi

# Obter diretório atual
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Diretório de instalação: $SCRIPT_DIR"

# Criar e ativar ambiente virtual Python
echo "Criando ambiente virtual Python..."
cd "$SCRIPT_DIR"

# Verificar se venv já existe
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Ambiente virtual criado"
else
    echo "Ambiente virtual já existe"
fi

# Ativar ambiente virtual e instalar dependências
echo "Ativando ambiente virtual e instalando dependências..."
source venv/bin/activate
pip install --upgrade pip

# Verificar se a instalação foi bem-sucedida
if pip install -r requirements.txt; then
    echo "✅ Dependências instaladas com sucesso no ambiente virtual"
else
    echo "❌ Erro ao instalar dependências"
    exit 1
fi

# Tornar os scripts executáveis
chmod +x openvpn_certificate_updater.py
chmod +x run_updater.sh
chmod +x test_config.py

# Criar diretórios necessários
echo "Criando diretórios necessários..."
mkdir -p /var/log
mkdir -p /etc/openvpn/backup

# Configurar permissões
echo "Configurando permissões..."
chown root:root openvpn_certificate_updater.py
chmod 755 openvpn_certificate_updater.py

# Verificar se arquivo de configuração existe
if [ ! -f "config.yml" ]; then
    echo "AVISO: Arquivo config.yml não encontrado!"
    echo "Por favor, configure o arquivo config.yml antes de usar o sistema."
    echo
fi

# Perguntar se deseja configurar como serviço systemd
read -p "Deseja configurar como serviço systemd para execução automática? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Configurando serviço systemd..."
    
    # Criar arquivo de serviço
    cat > /etc/systemd/system/openvpn-cert-updater.service << EOF
[Unit]
Description=OpenVPN Certificate Updater
After=network.target

[Service]
Type=oneshot
ExecStart=$SCRIPT_DIR/run_updater.sh
User=root
WorkingDirectory=$SCRIPT_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Criar arquivo de timer
    cat > /etc/systemd/system/openvpn-cert-updater.timer << EOF
[Unit]
Description=Run OpenVPN Certificate Updater every 6 hours
Requires=openvpn-cert-updater.service

[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Recarregar systemd e ativar timer
    systemctl daemon-reload
    systemctl enable openvpn-cert-updater.timer
    systemctl start openvpn-cert-updater.timer
    
    echo "Serviço systemd configurado com sucesso!"
    echo "O sistema será executado automaticamente a cada 6 horas."
    echo
    echo "Comandos úteis:"
    echo "  systemctl status openvpn-cert-updater.timer    # Status do timer"
    echo "  systemctl list-timers | grep openvpn           # Verificar próximas execuções"
    echo "  systemctl stop openvpn-cert-updater.timer      # Parar execução automática"
fi

# Teste de configuração
echo "Testando configuração..."
if [ -f "config.yml" ]; then
    echo "Executando teste de configuração..."
    source venv/bin/activate
    if python test_config.py; then
        echo "✓ Configuração básica OK"
    else
        echo "⚠ Possíveis problemas na configuração. Verifique o arquivo config.yml"
    fi
else
    echo "⚠ Arquivo config.yml não encontrado. Configure antes de usar."
fi

echo
echo "=== Instalação Concluída ==="
echo
echo "Próximos passos:"
echo "1. Configure o arquivo config.yml com suas credenciais FTP"
echo "2. Teste a configuração: sudo $SCRIPT_DIR/run_updater.sh test_config.py"
echo "3. Execute o updater: sudo $SCRIPT_DIR/run_updater.sh"
echo "4. Verifique os logs: tail -f /var/log/openvpn_config_updater.log"
echo
echo "📝 IMPORTANTE: Use sempre './run_updater.sh' em vez de executar o Python diretamente"
echo "   O wrapper script ativa automaticamente o ambiente virtual"
echo
echo "Documentação completa disponível em README.md"
echo
