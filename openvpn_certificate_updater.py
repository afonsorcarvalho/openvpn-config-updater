#!/usr/bin/env python3
"""
Script para atualização automática de configurações OpenVPN
Verifica remotamente via FTP se há um arquivo .ovpn mais atual,
baixa e substitui o arquivo de configuração local se necessário.

Autor: Sistema de Atualização Automática
Data: 2024
"""

import os
import sys
import yaml
import ftplib
import logging
import shutil
import subprocess
import time
import socket
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib

class OpenVPNConfigUpdater:
    """
    Classe principal para gerenciar a atualização de configurações OpenVPN
    """
    
    def __init__(self, config_file: str = "config.yml"):
        """
        Inicializa o updater com arquivo de configuração
        
        Args:
            config_file (str): Caminho para o arquivo de configuração YAML
        """
        self.config_file = config_file
        self.config = self._load_config()
        self._setup_logging()
        
        # Validação de configurações
        self._validate_config()
        
        self.logger.info("OpenVPN Config Updater inicializado")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Carrega configurações do arquivo YAML
        
        Returns:
            Dict[str, Any]: Configurações carregadas
        """
        try:
            with open(self.config_file, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Erro ao processar arquivo YAML: {e}")
    
    def _setup_logging(self):
        """
        Configura o sistema de logging baseado nas configurações
        """
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())
        log_file = log_config.get('log_file', '/var/log/openvpn_certificate_updater.log')
        
        # Criar diretório de log se não existir
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Configurar logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _validate_config(self):
        """
        Valida se as configurações obrigatórias estão presentes
        """
        required_sections = ['ftp', 'openvpn']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Seção obrigatória '{section}' não encontrada no arquivo de configuração")
        
        # Validar configurações FTP
        ftp_config = self.config['ftp']
        required_ftp_keys = ['host', 'username', 'password']
        for key in required_ftp_keys:
            if key not in ftp_config:
                raise ValueError(f"Configuração FTP obrigatória '{key}' não encontrada")
        
        # Validar configurações OpenVPN
        ovpn_config = self.config['openvpn']
        required_ovpn_keys = ['remote_path', 'remote_filename', 'local_openvpn_path', 'local_config_filename']
        for key in required_ovpn_keys:
            if key not in ovpn_config:
                raise ValueError(f"Configuração OpenVPN obrigatória '{key}' não encontrada")
    
    def _connect_ftp(self) -> ftplib.FTP:
        """
        Conecta ao servidor FTP usando as configurações
        
        Returns:
            ftplib.FTP: Conexão FTP estabelecida
        """
        ftp_config = self.config['ftp']
        
        try:
            self.logger.info(f"Conectando ao servidor FTP: {ftp_config['host']}")
            ftp = ftplib.FTP()
            ftp.connect(ftp_config['host'], ftp_config.get('port', 21))
            ftp.login(ftp_config['username'], ftp_config['password'])
            
            if ftp_config.get('use_passive', True):
                ftp.set_pasv(True)
            
            self.logger.info("Conexão FTP estabelecida com sucesso")
            return ftp
            
        except ftplib.all_errors as e:
            self.logger.error(f"Erro ao conectar ao servidor FTP: {e}")
            raise
    
    def _get_remote_file_info(self, ftp: ftplib.FTP, remote_path: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações do arquivo remoto (tamanho, data de modificação)
        
        Args:
            ftp (ftplib.FTP): Conexão FTP
            remote_path (str): Caminho remoto
            filename (str): Nome do arquivo
            
        Returns:
            Optional[Dict[str, Any]]: Informações do arquivo ou None se não encontrado
        """
        try:
            ftp.cwd(remote_path)
            files = []
            ftp.retrlines('LIST', files.append)
            
            for file_info in files:
                # Parse da saída do comando LIST
                parts = file_info.split()
                if len(parts) >= 9 and parts[-1] == filename:
                    # Extrair tamanho e data de modificação
                    size = int(parts[4])
                    date_str = ' '.join(parts[5:8])  # Mês, dia, hora/ano
                    
                    return {
                        'size': size,
                        'date_str': date_str,
                        'filename': filename
                    }
            
            self.logger.warning(f"Arquivo {filename} não encontrado em {remote_path}")
            return None
            
        except ftplib.all_errors as e:
            self.logger.error(f"Erro ao obter informações do arquivo remoto: {e}")
            return None
    
    def _get_local_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações do arquivo local
        
        Args:
            file_path (str): Caminho do arquivo local
            
        Returns:
            Optional[Dict[str, Any]]: Informações do arquivo ou None se não encontrado
        """
        if not os.path.exists(file_path):
            self.logger.warning(f"Arquivo local não encontrado: {file_path}")
            return None
        
        stat_info = os.stat(file_path)
        return {
            'size': stat_info.st_size,
            'mtime': stat_info.st_mtime,
            'filename': os.path.basename(file_path)
        }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calcula hash MD5 do arquivo para verificação de integridade
        
        Args:
            file_path (str): Caminho do arquivo
            
        Returns:
            str: Hash MD5 do arquivo
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _download_ovpn_file(self, ftp: ftplib.FTP, remote_path: str, filename: str, local_path: str) -> bool:
        """
        Baixa o arquivo .ovpn do servidor FTP
        
        Args:
            ftp (ftplib.FTP): Conexão FTP
            remote_path (str): Caminho remoto
            filename (str): Nome do arquivo remoto
            local_path (str): Caminho local para salvar
            
        Returns:
            bool: True se download foi bem-sucedido
        """
        try:
            ftp.cwd(remote_path)
            
            # Criar diretório local se não existir
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Baixar arquivo
            self.logger.info(f"Baixando arquivo .ovpn: {filename}")
            with open(local_path, 'wb') as local_file:
                ftp.retrbinary(f'RETR {filename}', local_file.write)
            
            self.logger.info(f"Arquivo .ovpn baixado com sucesso: {local_path}")
            return True
            
        except ftplib.all_errors as e:
            self.logger.error(f"Erro ao baixar arquivo .ovpn: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Erro inesperado durante download: {e}")
            return False
    
    def _create_backup(self, file_path: str) -> bool:
        """
        Cria backup do arquivo de configuração atual
        
        Args:
            file_path (str): Caminho do arquivo a ser copiado
            
        Returns:
            bool: True se backup foi criado com sucesso
        """
        try:
            backup_config = self.config['openvpn'].get('backup_path')
            if not backup_config:
                self.logger.info("Backup não configurado, pulando criação de backup")
                return True
            
            # Criar diretório de backup se não existir
            os.makedirs(backup_config, exist_ok=True)
            
            # Nome do arquivo de backup com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            backup_file = os.path.join(backup_config, f"{filename}.backup_{timestamp}")
            
            shutil.copy2(file_path, backup_file)
            self.logger.info(f"Backup criado: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            return False
    
    def _check_openvpn_connectivity(self) -> bool:
        """
        Verifica se o OpenVPN está conectado e funcionando
        
        Returns:
            bool: True se OpenVPN está conectado
        """
        try:
            rollback_config = self.config.get('verification', {}).get('rollback', {})
            max_attempts = rollback_config.get('max_connection_attempts', 3)
            retry_interval = rollback_config.get('retry_interval', 10)
            timeout = rollback_config.get('connection_timeout', 30)
            
            self.logger.info("Verificando conectividade OpenVPN...")
            
            for attempt in range(1, max_attempts + 1):
                self.logger.info(f"Tentativa {attempt}/{max_attempts} de verificação de conectividade")
                
                # Verificar se o serviço está rodando
                service_name = self.config.get('verification', {}).get('openvpn_service_name', 'openvpn@client')
                
                try:
                    # Verificar status do serviço
                    result = subprocess.run(['systemctl', 'is-active', service_name], 
                                          capture_output=True, text=True, timeout=10)
                    
                    if result.returncode != 0 or result.stdout.strip() != 'active':
                        self.logger.warning(f"Serviço OpenVPN não está ativo: {result.stdout.strip()}")
                        if attempt < max_attempts:
                            time.sleep(retry_interval)
                            continue
                        return False
                    
                    # Aguardar um pouco para o OpenVPN estabilizar
                    time.sleep(5)
                    
                    # Verificar se há interface tun/tap ativa
                    result = subprocess.run(['ip', 'link', 'show'], 
                                          capture_output=True, text=True, timeout=10)
                    
                    if 'tun' in result.stdout or 'tap' in result.stdout:
                        self.logger.info("Interface VPN detectada - OpenVPN conectado")
                        return True
                    
                    # Verificar logs do OpenVPN para erros recentes
                    result = subprocess.run(['journalctl', '-u', service_name, '--since', '1 minute ago', '--no-pager'], 
                                          capture_output=True, text=True, timeout=15)
                    
                    if 'ERROR' in result.stdout or 'FATAL' in result.stdout:
                        self.logger.error("Erros detectados nos logs do OpenVPN")
                        if attempt < max_attempts:
                            time.sleep(retry_interval)
                            continue
                        return False
                    
                    # Se chegou até aqui, assumir que está funcionando
                    self.logger.info("OpenVPN aparenta estar funcionando")
                    return True
                    
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Timeout na verificação (tentativa {attempt})")
                except Exception as e:
                    self.logger.warning(f"Erro na verificação (tentativa {attempt}): {e}")
                
                if attempt < max_attempts:
                    self.logger.info(f"Aguardando {retry_interval} segundos antes da próxima tentativa...")
                    time.sleep(retry_interval)
            
            self.logger.error("Falha em todas as tentativas de verificação de conectividade")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro inesperado durante verificação de conectividade: {e}")
            return False
    
    def _rollback_configuration(self, backup_file: str, current_file: str) -> bool:
        """
        Faz rollback da configuração para o backup
        
        Args:
            backup_file (str): Caminho do arquivo de backup
            current_file (str): Caminho do arquivo atual
            
        Returns:
            bool: True se rollback foi bem-sucedido
        """
        try:
            self.logger.warning("Iniciando rollback da configuração...")
            
            if not os.path.exists(backup_file):
                self.logger.error(f"Arquivo de backup não encontrado: {backup_file}")
                return False
            
            # Remover arquivo atual
            if os.path.exists(current_file):
                os.remove(current_file)
            
            # Restaurar backup
            shutil.copy2(backup_file, current_file)
            os.chmod(current_file, 0o600)
            
            self.logger.info(f"Configuração restaurada do backup: {backup_file}")
            
            # Reiniciar serviço OpenVPN
            if self._restart_openvpn_service():
                self.logger.info("Rollback concluído com sucesso")
                return True
            else:
                self.logger.error("Falha ao reiniciar serviço após rollback")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro durante rollback: {e}")
            return False
    
    def _restart_openvpn_service(self) -> bool:
        """
        Reinicia o serviço OpenVPN
        
        Returns:
            bool: True se serviço foi reiniciado com sucesso
        """
        try:
            if not self.config.get('verification', {}).get('restart_openvpn', True):
                self.logger.info("Reinicialização do OpenVPN desabilitada na configuração")
                return True
            
            service_name = self.config.get('verification', {}).get('openvpn_service_name', 'openvpn')
            
            self.logger.info(f"Reiniciando serviço OpenVPN: {service_name}")
            
            # Tentar systemctl primeiro
            result = subprocess.run(['systemctl', 'restart', service_name], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info("Serviço OpenVPN reiniciado com sucesso via systemctl")
                return True
            else:
                # Tentar service como fallback
                self.logger.warning("systemctl falhou, tentando comando service")
                result = subprocess.run(['service', service_name, 'restart'], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    self.logger.info("Serviço OpenVPN reiniciado com sucesso via service")
                    return True
                else:
                    self.logger.error(f"Falha ao reiniciar serviço OpenVPN: {result.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout ao reiniciar serviço OpenVPN")
            return False
        except Exception as e:
            self.logger.error(f"Erro inesperado ao reiniciar serviço OpenVPN: {e}")
            return False
    
    def check_and_update_config(self) -> bool:
        """
        Verifica e atualiza a configuração OpenVPN se necessário
        
        Returns:
            bool: True se atualização foi realizada com sucesso ou não necessária
        """
        try:
            ovpn_config = self.config['openvpn']
            
            # Conectar ao FTP
            ftp = self._connect_ftp()
            
            try:
                # Obter informações do arquivo remoto
                remote_info = self._get_remote_file_info(
                    ftp, 
                    ovpn_config['remote_path'], 
                    ovpn_config['remote_filename']
                )
                
                if not remote_info:
                    self.logger.error("Não foi possível obter informações do arquivo .ovpn remoto")
                    return False
                
                # Obter informações do arquivo local
                local_file_path = os.path.join(ovpn_config['local_openvpn_path'], ovpn_config['local_config_filename'])
                local_info = self._get_local_file_info(local_file_path)
                
                # Se arquivo local não existe, fazer download
                if not local_info:
                    self.logger.info("Arquivo de configuração local não encontrado, fazendo download...")
                    return self._download_and_install_ovpn(ftp, ovpn_config, local_file_path)
                
                # Comparar tamanhos dos arquivos
                if remote_info['size'] != local_info['size']:
                    self.logger.info(f"Arquivo .ovpn remoto tem tamanho diferente. "
                                   f"Remoto: {remote_info['size']} bytes, "
                                   f"Local: {local_info['size']} bytes")
                    return self._download_and_install_ovpn(ftp, ovpn_config, local_file_path)
                
                # Se tamanhos são iguais, verificar hash para ter certeza
                self.logger.info("Tamanhos são iguais, verificando integridade...")
                
                # Baixar arquivo temporário para comparação
                temp_file = f"{local_file_path}.temp"
                if self._download_ovpn_file(ftp, ovpn_config['remote_path'], 
                                          ovpn_config['remote_filename'], temp_file):
                    
                    # Comparar hashes
                    local_hash = self._calculate_file_hash(local_file_path)
                    remote_hash = self._calculate_file_hash(temp_file)
                    
                    # Remover arquivo temporário
                    os.remove(temp_file)
                    
                    if local_hash != remote_hash:
                        self.logger.info("Hashes diferentes detectados, configuração será atualizada")
                        return self._download_and_install_ovpn(ftp, ovpn_config, local_file_path)
                    else:
                        self.logger.info("Configuração local está atualizada")
                        return True
                else:
                    self.logger.error("Falha ao baixar arquivo para verificação")
                    return False
                    
            finally:
                ftp.quit()
                
        except Exception as e:
            self.logger.error(f"Erro durante verificação e atualização: {e}")
            return False
    
    def _download_and_install_ovpn(self, ftp: ftplib.FTP, ovpn_config: Dict[str, Any], local_file_path: str) -> bool:
        """
        Baixa e instala o novo arquivo .ovpn como configuração
        
        Args:
            ftp (ftplib.FTP): Conexão FTP
            ovpn_config (Dict[str, Any]): Configurações OpenVPN
            local_file_path (str): Caminho do arquivo local
            
        Returns:
            bool: True se instalação foi bem-sucedida
        """
        try:
            # Criar backup se configurado
            backup_file = None
            if self.config.get('verification', {}).get('create_backup', True):
                if os.path.exists(local_file_path):
                    if not self._create_backup(local_file_path):
                        self.logger.warning("Falha ao criar backup, continuando com atualização...")
                    else:
                        # Encontrar o arquivo de backup mais recente
                        backup_config = self.config['openvpn'].get('backup_path')
                        if backup_config and os.path.exists(backup_config):
                            backup_files = [f for f in os.listdir(backup_config) 
                                          if f.startswith(os.path.basename(local_file_path)) and f.endswith('.backup_')]
                            if backup_files:
                                # Ordenar por data de modificação (mais recente primeiro)
                                backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_config, x)), reverse=True)
                                backup_file = os.path.join(backup_config, backup_files[0])
                                self.logger.info(f"Backup identificado: {backup_file}")
            
            # Baixar novo arquivo .ovpn
            temp_file = f"{local_file_path}.new"
            if not self._download_ovpn_file(ftp, ovpn_config['remote_path'], 
                                          ovpn_config['remote_filename'], temp_file):
                return False
            
            # Verificar se o arquivo baixado é válido (não está vazio)
            if os.path.getsize(temp_file) == 0:
                self.logger.error("Arquivo baixado está vazio")
                os.remove(temp_file)
                return False
            
            # Substituir arquivo antigo
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
            
            shutil.move(temp_file, local_file_path)
            
            # Definir permissões apropriadas (somente leitura para proprietário)
            os.chmod(local_file_path, 0o600)
            
            self.logger.info(f"Configuração OpenVPN atualizada com sucesso: {local_file_path}")
            
            # Reiniciar serviço OpenVPN se configurado
            if not self._restart_openvpn_service():
                self.logger.error("Falha ao reiniciar serviço OpenVPN")
                if backup_file and self.config.get('verification', {}).get('rollback', {}).get('auto_rollback', True):
                    self.logger.warning("Tentando rollback devido à falha no reinício do serviço")
                    return self._rollback_configuration(backup_file, local_file_path)
                return False
            
            # Verificar conectividade se configurado
            rollback_config = self.config.get('verification', {}).get('rollback', {})
            if rollback_config.get('check_connectivity', True):
                self.logger.info("Verificando conectividade após atualização...")
                
                if not self._check_openvpn_connectivity():
                    self.logger.error("Falha na verificação de conectividade")
                    
                    # Fazer rollback se configurado
                    if rollback_config.get('auto_rollback', True) and backup_file:
                        self.logger.warning("Executando rollback automático devido à falha de conectividade")
                        return self._rollback_configuration(backup_file, local_file_path)
                    else:
                        self.logger.error("Rollback automático desabilitado ou backup não disponível")
                        return False
                else:
                    self.logger.info("Verificação de conectividade bem-sucedida")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro durante instalação da configuração: {e}")
            # Remover arquivo temporário se existir
            temp_file = f"{local_file_path}.new"
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False


def main():
    """
    Função principal do script
    """
    try:
        # Verificar se arquivo de configuração foi especificado
        config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yml"
        
        if not os.path.exists(config_file):
            print(f"Erro: Arquivo de configuração não encontrado: {config_file}")
            print("Use: python3 openvpn_certificate_updater.py [config.yml]")
            sys.exit(1)
        
        # Criar e executar updater
        updater = OpenVPNConfigUpdater(config_file)
        
        print("Iniciando verificação de configuração OpenVPN...")
        success = updater.check_and_update_config()
        
        if success:
            print("Verificação concluída com sucesso")
            sys.exit(0)
        else:
            print("Erro durante verificação/atualização")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
