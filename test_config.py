#!/usr/bin/env python3
"""
Script de teste para validar a configuração do OpenVPN Config Updater
"""

import os
import sys
import yaml
from pathlib import Path

def test_config_file(config_file="config.yml"):
    """
    Testa se o arquivo de configuração está válido e completo
    
    Args:
        config_file (str): Caminho para o arquivo de configuração
    """
    print(f"=== Testando arquivo de configuração: {config_file} ===\n")
    
    # Verificar se arquivo existe
    if not os.path.exists(config_file):
        print(f"❌ ERRO: Arquivo {config_file} não encontrado!")
        print("   Copie config.example.yml para config.yml e configure as opções.")
        return False
    
    try:
        # Carregar configuração
        with open(config_file, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        print("✅ Arquivo YAML carregado com sucesso")
        
        # Verificar seções obrigatórias
        required_sections = ['ftp', 'openvpn']
        for section in required_sections:
            if section not in config:
                print(f"❌ ERRO: Seção '{section}' não encontrada")
                return False
            print(f"✅ Seção '{section}' encontrada")
        
        # Verificar configurações FTP
        ftp_config = config['ftp']
        required_ftp_keys = ['host', 'username', 'password']
        for key in required_ftp_keys:
            if key not in ftp_config:
                print(f"❌ ERRO: Configuração FTP '{key}' não encontrada")
                return False
            print(f"✅ Configuração FTP '{key}': {ftp_config[key] if key != 'password' else '***'}")
        
        # Verificar configurações OpenVPN
        ovpn_config = config['openvpn']
        required_ovpn_keys = ['remote_path', 'local_openvpn_path', 'local_config_filename']
        for key in required_ovpn_keys:
            if key not in ovpn_config:
                print(f"❌ ERRO: Configuração OpenVPN '{key}' não encontrada")
                return False
            print(f"✅ Configuração OpenVPN '{key}': {ovpn_config[key]}")
        
        # Verificar se remote_filename foi removido (não é mais necessário)
        if 'remote_filename' in ovpn_config:
            print("⚠️  AVISO: 'remote_filename' não é mais necessário - o sistema busca automaticamente o arquivo .ovpn mais recente")
        
        # Verificar diretórios locais
        local_path = ovpn_config['local_openvpn_path']
        if os.path.exists(local_path):
            print(f"✅ Diretório OpenVPN local existe: {local_path}")
        else:
            print(f"⚠️  AVISO: Diretório OpenVPN local não existe: {local_path}")
        
        # Verificar arquivo de configuração local
        local_config_file = os.path.join(local_path, ovpn_config['local_config_filename'])
        if os.path.exists(local_config_file):
            print(f"✅ Arquivo de configuração local existe: {local_config_file}")
        else:
            print(f"⚠️  AVISO: Arquivo de configuração local não existe: {local_config_file}")
        
        # Verificar configurações de log
        log_config = config.get('logging', {})
        log_file = log_config.get('log_file', '/var/log/openvpn_config_updater.log')
        log_dir = os.path.dirname(log_file)
        
        if os.path.exists(log_dir):
            print(f"✅ Diretório de log existe: {log_dir}")
        else:
            print(f"⚠️  AVISO: Diretório de log não existe: {log_dir}")
        
        print("\n=== Resumo do Teste ===")
        print("✅ Configuração básica válida")
        print("📝 Verifique as configurações acima antes de usar o sistema")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ ERRO: Erro ao processar arquivo YAML: {e}")
        return False
    except Exception as e:
        print(f"❌ ERRO inesperado: {e}")
        return False

def test_dependencies():
    """
    Testa se as dependências Python estão instaladas
    """
    print("\n=== Testando Dependências Python ===\n")
    
    dependencies = [
        ('yaml', 'PyYAML'),
        ('ftplib', 'ftplib (built-in)'),
        ('hashlib', 'hashlib (built-in)'),
        ('logging', 'logging (built-in)'),
        ('pathlib', 'pathlib (built-in)'),
        ('subprocess', 'subprocess (built-in)'),
        ('socket', 'socket (built-in)'),
        ('time', 'time (built-in)')
    ]
    
    all_ok = True
    
    for module, package in dependencies:
        try:
            __import__(module)
            print(f"✅ {package} disponível")
        except ImportError:
            print(f"❌ ERRO: {package} não encontrado")
            all_ok = False
    
    return all_ok

def main():
    """
    Função principal do teste
    """
    print("OpenVPN Config Updater - Teste de Configuração")
    print("=" * 50)
    
    # Testar dependências
    deps_ok = test_dependencies()
    
    # Testar arquivo de configuração
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yml"
    config_ok = test_config_file(config_file)
    
    print("\n" + "=" * 50)
    if deps_ok and config_ok:
        print("✅ Todos os testes passaram! Sistema pronto para uso.")
        sys.exit(0)
    else:
        print("❌ Alguns testes falharam. Corrija os problemas antes de usar.")
        sys.exit(1)

if __name__ == "__main__":
    main()
