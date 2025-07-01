# EKR AlmaLinux Deployment System

This directory contains a comprehensive deployment system for EKR (Extended Knowledge Repository) services on AlmaLinux systems. The deployment system is designed to be generic, configurable, and production-ready.

## 🏗️ Features

- **Generic OS Support**: Specifically designed for AlmaLinux 8/9 with adaptability to other RHEL-based systems
- **Flexible Service Detection**: Automatically detects changed services in the `services/` directory
- **Configurable Deployment**: Supports different service types (Python, Node.js, Go) through configuration
- **Package Manager Integration**: Uses dnf for AlmaLinux, pip for Python, npm for Node.js
- **Systemd Service Management**: Creates and manages systemd services automatically
- **Configuration-Driven**: All deployment parameters defined in `services-config.yml`
- **Error Handling**: Robust error handling and comprehensive logging
- **Rollback Support**: Automatic rollback on deployment failures
- **Health Checks**: Post-deployment health verification
- **Resource Management**: CPU and memory limits for services
- **Security**: Proper user isolation and security settings

## 📁 Directory Structure

```
deployment/
├── ansible.cfg                 # Ansible configuration
├── deploy-service.yml          # Main service deployment playbook
├── health-check.yml           # Service health check playbook
├── system-health-check.yml    # System-wide health check playbook
├── rollback-service.yml       # Service rollback playbook
├── cleanup.yml                # Cleanup and maintenance playbook
├── inventory/
│   └── hosts.yml.example      # Sample inventory file
├── templates/
│   ├── systemd-service.j2     # Systemd service template
│   ├── environment.j2         # Environment file template
│   └── startup-script.j2      # Service startup script template
└── scripts/
    └── deploy-manager.sh      # Deployment management script
```

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have the required tools installed:

```bash
# On your deployment machine (not the target server)
pip install ansible ansible-core PyYAML

# Verify installation
ansible --version
```

### 2. Configuration

1. **Copy and customize the inventory file:**
   ```bash
   cp deployment/inventory/hosts.yml.example deployment/inventory/hosts.yml
   # Edit hosts.yml with your server details
   ```

2. **Review and customize `services-config.yml`:**
   - Service-specific ports and configurations
   - Environment variables
   - Resource limits
   - Dependencies

3. **Set up SSH access to your AlmaLinux servers:**
   ```bash
   ssh-copy-id deploy@your-almalinux-server
   ```

### 3. GitHub Secrets

Configure the following secrets in your GitHub repository:

- `DEPLOY_SSH_PRIVATE_KEY`: SSH private key for deployment
- `DEPLOY_HOST`: Target server hostname/IP
- `DEPLOY_USER`: Deployment user on the target server

### 4. Deployment

The deployment can be triggered in several ways:

#### Automatic Deployment (Recommended)
- Push changes to the `main` or `develop` branch
- The GitHub workflow will automatically detect changed services and deploy them

#### Manual Deployment via GitHub Actions
- Go to Actions → Deploy EKR Services to AlmaLinux
- Click "Run workflow"
- Choose your options:
  - Force deploy all services
  - Target environment (staging/production)
  - Specific services to deploy

#### Command Line Deployment
```bash
# List available services
./deployment/scripts/deploy-manager.sh list

# Deploy a specific service
./deployment/scripts/deploy-manager.sh deploy database-api staging

# Run health check
./deployment/scripts/deploy-manager.sh health

# Rollback a service
./deployment/scripts/deploy-manager.sh rollback llm-query
```

## 📋 Service Configuration

Each service is configured in `services-config.yml`. Here's an example:

```yaml
services:
  my-service:
    name: "My Custom Service"
    description: "Description of my service"
    port: 8080
    main_file: "main.py"
    health_endpoint: "/health"
    dependencies:
      - "postgresql.service"
    environment_variables:
      DATABASE_URL: "${DATABASE_URL}"
      LOG_LEVEL: "INFO"
    resources:
      memory_limit: "512M"
      cpu_limit: "1.0"
```

### Service Types

The system supports multiple service types:

- **Python (default)**: FastAPI services with uvicorn
- **Node.js**: Express.js or other Node.js applications
- **Go**: Compiled Go applications
- **Generic**: Any executable service

## 🔧 Advanced Configuration

### Environment Variables

Environment variables can be set at multiple levels:
1. Global level in `services-config.yml`
2. Service-specific in `services-config.yml`
3. Server-specific in the inventory file
4. GitHub secrets for sensitive data

### Resource Limits

Configure CPU and memory limits for each service:

```yaml
resources:
  memory_limit: "1G"     # Memory limit (K, M, G)
  cpu_limit: "2.0"       # CPU limit (cores)
```

### Dependencies

Specify systemd service dependencies:

```yaml
dependencies:
  - "postgresql.service"
  - "redis.service"
  - "ekr-database-api.service"
```

### Health Checks

Configure health check parameters:

```yaml
health_check_timeout: 30      # Timeout in seconds
health_check_retries: 5       # Number of retries
health_check_interval: 10     # Interval between retries
```

## 🏥 Health Monitoring

The system includes comprehensive health monitoring:

### Service Health Checks
- HTTP endpoint health checks
- Systemd service status verification
- Port accessibility verification
- Log error detection

### System Health Checks
- CPU and memory usage monitoring
- Disk space monitoring
- Service status overview
- Network connectivity checks

### Running Health Checks

```bash
# Check specific service
ansible-playbook -i inventory/hosts.yml health-check.yml -e "service_name=database-api"

# System-wide health check
ansible-playbook -i inventory/hosts.yml system-health-check.yml

# Using the management script
./scripts/deploy-manager.sh health
```

## 🔄 Rollback System

The deployment system includes automatic rollback capabilities:

### Automatic Rollback
- Triggered on deployment failures
- Controlled by `rollback_on_failure` in configuration
- Uses the most recent backup

### Manual Rollback
```bash
# Via Ansible
ansible-playbook -i inventory/hosts.yml rollback-service.yml -e "service_name=my-service"

# Via management script
./scripts/deploy-manager.sh rollback my-service
```

### Backup Management
- Automatic backup before deployment
- Configurable retention period
- Cleanup of old backups

## 🧹 Maintenance

### Cleanup Tasks
The system includes automated cleanup:
- Old backup removal
- Log rotation
- Package cleanup
- Journal size management

```bash
# Run cleanup
ansible-playbook -i inventory/hosts.yml cleanup.yml

# Via management script
./scripts/deploy-manager.sh cleanup
```

## 🔒 Security

### User Isolation
- Services run under dedicated `ekr` user
- Proper file permissions
- No root privileges for services

### Systemd Security
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `ProtectSystem=strict`
- Read-write paths limited to necessary directories

### Network Security
- Firewall configuration for service ports
- SELinux integration (when enabled)

## 🐛 Troubleshooting

### Common Issues

1. **SSH Connection Issues**
   ```bash
   # Test SSH connection
   ssh -i ~/.ssh/id_rsa deploy@your-server
   
   # Check SSH key permissions
   chmod 600 ~/.ssh/id_rsa
   ```

2. **Service Won't Start**
   ```bash
   # Check service status
   systemctl status ekr-service-name
   
   # Check logs
   journalctl -u ekr-service-name -f
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using the port
   sudo ss -tulpn | grep :8080
   ```

4. **Permission Issues**
   ```bash
   # Check file ownership
   ls -la /opt/ekr/services/service-name/
   
   # Fix ownership if needed
   sudo chown -R ekr:ekr /opt/ekr/services/service-name/
   ```

### Log Locations

- Service logs: `/var/log/ekr/`
- Systemd logs: `journalctl -u ekr-service-name`
- Deployment logs: `/tmp/ansible.log`
- Rollback logs: `/var/log/ekr/rollback.log`

### Debug Mode

Enable debug mode by setting environment variables:

```bash
export ANSIBLE_DEBUG=1
export ANSIBLE_VERBOSITY=3

# Run deployment with debug
ansible-playbook -vvv -i inventory/hosts.yml deploy-service.yml -e "service_name=my-service"
```

## 📚 Additional Resources

- [Ansible Documentation](https://docs.ansible.com/)
- [AlmaLinux Documentation](https://docs.almalinux.org/)
- [Systemd Service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## 🤝 Contributing

1. Test changes in a staging environment first
2. Update documentation for any configuration changes
3. Follow the existing code style and structure
4. Add appropriate error handling and logging

## 📄 License

This deployment system is part of the EKR project and follows the same license terms.