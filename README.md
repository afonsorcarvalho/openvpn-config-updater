# OpenVPN Config Updater

Script Python para atualização automática de configurações OpenVPN via FTP remoto.

## Descrição

Este script verifica periodicamente se há uma versão mais atual do arquivo `.ovpn` disponível em um servidor FTP remoto. Se encontrar uma versão mais recente, baixa o arquivo `.ovpn` e o coloca como configuração do OpenVPN (`/etc/openvpn/client.conf`), reiniciando automaticamente o serviço OpenVPN.

## Funcionalidades

- ✅ Conexão segura via FTP
- ✅ Verificação de integridade por tamanho e hash MD5
- ✅ Backup automático da configuração atual
- ✅ Reinicialização automática do serviço OpenVPN
- ✅ **Verificação de conectividade após atualização**
- ✅ **Rollback automático em caso de falha**
- ✅ Sistema de logging configurável
- ✅ Configuração centralizada via arquivo YAML
- ✅ Tratamento robusto de erros

## Requisitos

- Python 3.6 ou superior
- Acesso ao servidor FTP remoto
- Privilégios administrativos para modificar arquivos do OpenVPN
- Bibliotecas Python listadas em `requirements.txt`

## Instalação

1. **Clone ou baixe os arquivos:**
   ```bash
   git clone <repository-url>
   cd raspberry_update_certificate
   ```

2. **Instale as dependências:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure o arquivo `config.yml`:**
   - Edite as configurações do servidor FTP
   - Ajuste os caminhos dos arquivos OpenVPN
   - Configure opções de log e verificação

4. **Teste a configuração:**
   ```bash
   python3 openvpn_certificate_updater.py
   ```

## Configuração

### Arquivo config.yml

O arquivo `config.yml` concentra todas as configurações necessárias:

#### Configurações FTP
```yaml
ftp:
  host: "ftp.exemplo.com"      # Endereço do servidor FTP
  port: 21                     # Porta do servidor
  username: "usuario"          # Usuário FTP
  password: "senha"            # Senha FTP
  use_passive: true            # Modo passivo (recomendado)
  timeout: 30                  # Timeout em segundos
```

#### Configurações OpenVPN
```yaml
openvpn:
  remote_path: "/certificados/atual"     # Caminho remoto no FTP
  remote_filename: "alguma_coisa.ovpn"   # Nome do arquivo .ovpn remoto
  local_openvpn_path: "/etc/openvpn"     # Diretório local do OpenVPN
  local_config_filename: "client.conf"   # Nome do arquivo de configuração local
  backup_path: "/etc/openvpn/backup"     # Diretório para backups
```

#### Configurações de Log
```yaml
logging:
  level: "INFO"                           # Nível de log
  log_file: "/var/log/openvpn_certificate_updater.log"
  max_lines: 1000                        # Rotação de log
```

#### Configurações de Verificação
```yaml
verification:
  check_interval_hours: 24               # Intervalo de verificação
  create_backup: true                    # Criar backup antes de substituir a configuração
  restart_openvpn: true                  # Reiniciar serviço após atualização
  openvpn_service_name: "openvpn@client" # Nome do serviço OpenVPN
  
  # Configurações de rollback automático
  rollback:
    check_connectivity: true             # Verificar conectividade após atualização
    connection_timeout: 30               # Timeout para conexão (segundos)
    max_connection_attempts: 3           # Número de tentativas de verificação
    retry_interval: 10                   # Intervalo entre tentativas (segundos)
    auto_rollback: true                  # Rollback automático em caso de falha
```

## Uso

### Execução Manual
```bash
# Usando arquivo de configuração padrão (config.yml)
python3 openvpn_certificate_updater.py

# Especificando arquivo de configuração customizado
python3 openvpn_certificate_updater.py /caminho/para/config.yml
```

### Execução Automática (Cron)

Para executar automaticamente, adicione uma entrada no crontab:

```bash
# Editar crontab
crontab -e

# Adicionar linha para executar a cada 6 horas
0 */6 * * * /usr/bin/python3 /caminho/para/openvpn_certificate_updater.py

# Ou executar diariamente às 2:00
0 2 * * * /usr/bin/python3 /caminho/para/openvpn_certificate_updater.py
```

### Execução como Serviço Systemd

1. **Criar arquivo de serviço:**
   ```bash
   sudo nano /etc/systemd/system/openvpn-cert-updater.service
   ```

2. **Conteúdo do arquivo de serviço:**
   ```ini
   [Unit]
   Description=OpenVPN Certificate Updater
   After=network.target

   [Service]
   Type=oneshot
   ExecStart=/usr/bin/python3 /caminho/para/openvpn_certificate_updater.py
   User=root
   WorkingDirectory=/caminho/para/raspberry_update_certificate

   [Install]
   WantedBy=multi-user.target
   ```

3. **Criar timer para execução periódica:**
   ```bash
   sudo nano /etc/systemd/system/openvpn-cert-updater.timer
   ```

4. **Conteúdo do timer:**
   ```ini
   [Unit]
   Description=Run OpenVPN Certificate Updater every 6 hours
   Requires=openvpn-cert-updater.service

   [Timer]
   OnCalendar=*-*-* 00,06,12,18:00:00
   Persistent=true

   [Install]
   WantedBy=timers.target
   ```

5. **Ativar e iniciar:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable openvpn-cert-updater.timer
   sudo systemctl start openvpn-cert-updater.timer
   ```

## Logs

Os logs são gravados tanto no arquivo configurado quanto na saída padrão. Os níveis disponíveis são:
- `DEBUG`: Informações detalhadas para depuração
- `INFO`: Informações gerais (padrão)
- `WARNING`: Avisos sobre situações não críticas
- `ERROR`: Erros que impedem a execução
- `CRITICAL`: Erros críticos que podem causar falhas

### Localização dos Logs
- Arquivo: `/var/log/openvpn_certificate_updater.log` (configurável)
- Saída padrão: Console durante execução

## Verificação de Integridade

O script utiliza múltiplas camadas de verificação:

1. **Comparação de Tamanho**: Verifica se os arquivos têm tamanhos diferentes
2. **Verificação de Hash MD5**: Compara hashes para detectar diferenças mesmo com mesmo tamanho
3. **Validação de Arquivo**: Verifica se o arquivo baixado não está vazio

## Rollback Automático

O sistema inclui um mecanismo robusto de rollback automático para garantir que o OpenVPN sempre funcione:

### **Como Funciona:**

1. **Backup Automático**: Antes de qualquer atualização, cria backup da configuração atual
2. **Verificação de Conectividade**: Após atualização, verifica se o OpenVPN está funcionando
3. **Rollback Automático**: Se a verificação falhar, restaura automaticamente o backup

### **Verificações de Conectividade:**

- ✅ Status do serviço OpenVPN (`systemctl is-active`)
- ✅ Presença de interfaces VPN (`tun`/`tap`)
- ✅ Análise de logs do OpenVPN para erros
- ✅ Múltiplas tentativas com intervalos configuráveis

### **Configuração do Rollback:**

```yaml
verification:
  rollback:
    check_connectivity: true        # Ativar verificação
    connection_timeout: 30         # Timeout por tentativa
    max_connection_attempts: 3     # Número de tentativas
    retry_interval: 10             # Intervalo entre tentativas
    auto_rollback: true            # Rollback automático
```

### **Cenários de Rollback:**

- **Falha no Reinício**: Se o serviço OpenVPN não reiniciar
- **Falha de Conectividade**: Se o OpenVPN não conseguir conectar
- **Erros nos Logs**: Se houver erros críticos nos logs do OpenVPN
- **Interface VPN Ausente**: Se não houver interface `tun`/`tap` ativa

## Backup e Segurança

- **Backup Automático**: Cria backup da configuração atual antes da substituição
- **Permissões**: Define permissões seguras (600) para o novo arquivo de configuração
- **Rollback Automático**: Em caso de erro, restaura automaticamente o backup
- **Verificação de Integridade**: Múltiplas camadas de verificação antes e depois da atualização

## Solução de Problemas

### Erro de Conexão FTP
- Verifique as credenciais no `config.yml`
- Teste conectividade: `telnet ftp.exemplo.com 21`
- Verifique se o firewall permite conexões FTP

### Erro de Permissão
- Execute com privilégios administrativos: `sudo python3 openvpn_certificate_updater.py`
- Verifique se o usuário tem acesso aos diretórios do OpenVPN

### Erro de Serviço OpenVPN
- Verifique o nome do serviço: `systemctl list-units | grep openvpn`
- Ajuste `openvpn_service_name` no `config.yml`

### Rollback Manual
Se o rollback automático falhar, você pode fazer rollback manual:

```bash
# Parar o serviço OpenVPN
sudo systemctl stop openvpn@client

# Restaurar backup manualmente
sudo cp /etc/openvpn/backup/client.conf.backup_YYYYMMDD_HHMMSS /etc/openvpn/client.conf

# Reiniciar o serviço
sudo systemctl start openvpn@client
```

### Logs de Erro
```bash
# Verificar logs do sistema
sudo journalctl -u openvpn-cert-updater.service

# Verificar logs do script
tail -f /var/log/openvpn_config_updater.log

# Verificar logs do OpenVPN
sudo journalctl -u openvpn@client --since "10 minutes ago"
```

## Estrutura de Arquivos

```
raspberry_update_certificate/
├── openvpn_certificate_updater.py    # Script principal
├── config.yml                        # Arquivo de configuração
├── requirements.txt                  # Dependências Python
└── README.md                         # Esta documentação
```

## Contribuição

Para contribuir com melhorias:

1. Faça fork do repositório
2. Crie uma branch para sua feature
3. Implemente as mudanças com testes
4. Submeta um pull request

## Licença

Este projeto está sob licença MIT. Veja o arquivo LICENSE para detalhes.

## Suporte

Para suporte ou dúvidas:
- Abra uma issue no repositório
- Consulte os logs para diagnóstico
- Verifique a documentação do OpenVPN para configurações específicas
