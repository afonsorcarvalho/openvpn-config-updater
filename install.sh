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
    apt install -y python3 python3-pip
fi

# Verificar se pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "pip3 não está instalado. Instalando..."
    apt install -y python3-pip
fi

# Obter diretório atual
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Diretório de instalação: $SCRIPT_DIR"

# Instalar dependências Python
echo "Instalando dependências Python..."
cd "$SCRIPT_DIR"
pip3 install -r requirements.txt

# Tornar o script executável
chmod +x openvpn_certificate_updater.py

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
ExecStart=/usr/bin/python3 $SCRIPT_DIR/openvpn_certificate_updater.py
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
    if python3 openvpn_certificate_updater.py --help 2>/dev/null || python3 openvpn_certificate_updater.py 2>&1 | head -5; then
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
echo "2. Teste a execução: sudo python3 $SCRIPT_DIR/openvpn_certificate_updater.py"
echo "3. Verifique os logs: tail -f /var/log/openvpn_certificate_updater.log"
echo
echo "Documentação completa disponível em README.md"
echo
