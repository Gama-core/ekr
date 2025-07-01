# EKR AlmaLinux Deployment Guide

This guide walks you through setting up and deploying EKR services on AlmaLinux servers.

## 🎯 Overview

The EKR deployment system provides a complete solution for deploying FastAPI microservices on AlmaLinux 8/9 with:

- Automatic service detection
- Rolling deployments
- Health monitoring
- Automatic rollback
- Systemd integration
- Resource management
- Security hardening

## 📋 Prerequisites

### Target Server (AlmaLinux)
- AlmaLinux 8 or 9
- Minimum 4GB RAM, 2 CPU cores
- 20GB+ disk space
- Internet connectivity
- SSH access with sudo privileges

### Deployment Machine
- Python 3.8+
- Ansible 2.9+
- Git
- SSH client

## 🚀 Quick Setup

### 1. Server Preparation

On your AlmaLinux server:

```bash
# Update system
sudo dnf update -y

# Install required packages
sudo dnf install -y python3 python3-pip git curl wget

# Create deployment user
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG wheel deploy

# Set up SSH key access
sudo mkdir -p /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys

# Configure firewall
sudo firewall-cmd --permanent --add-port=8001-8020/tcp
sudo firewall-cmd --reload
```

### 2. Local Setup

On your deployment machine:

```bash
# Clone the repository
git clone https://github.com/Gama-core/ekr.git
cd ekr

# Install Ansible
pip3 install ansible ansible-core PyYAML

# Copy configuration files
cp deployment/inventory/hosts.yml.example deployment/inventory/hosts.yml
cp .env.example .env

# Edit configuration
nano deployment/inventory/hosts.yml  # Configure your servers
nano .env                           # Configure environment variables
```

### 3. Configuration

Edit `deployment/inventory/hosts.yml`:

```yaml
all:
  hosts:
    almalinux-staging:
      ansible_host: "YOUR_SERVER_IP"
      ansible_user: "deploy"
      ansible_ssh_private_key_file: "~/.ssh/id_rsa"
      ansible_python_interpreter: "/usr/bin/python3"
      target_environment: "staging"
```

### 4. Validation

Validate your configuration:

```bash
# Run validation script
python3 deployment/scripts/validate-config.py

# Test Ansible connectivity
cd deployment
ansible all -i inventory/hosts.yml -m ping
```

### 5. First Deployment

Deploy services manually:

```bash
# Deploy a single service
./deployment/scripts/deploy-manager.sh deploy database-api staging

# Deploy all services
./deployment/scripts/deploy-manager.sh deploy-all staging

# Check health
./deployment/scripts/deploy-manager.sh health
```

## 🔧 GitHub Actions Setup

### 1. Repository Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

```
DEPLOY_SSH_PRIVATE_KEY  # Your SSH private key (full content)
DEPLOY_HOST            # Target server IP/hostname
DEPLOY_USER            # Deployment user (e.g., "deploy")
```

### 2. Environment Variables

Add environment-specific secrets:

```
DATABASE_URL           # Database connection string
QWEN_API_KEY          # LLM API key
GOOGLE_API_KEY        # Google API key
GOOGLE_CSE_ID         # Google Custom Search Engine ID
ES_HOST_URL           # Elasticsearch host URL
ES_USERNAME           # Elasticsearch username
ES_PASSWORD           # Elasticsearch password
```

### 3. Workflow Triggers

The deployment workflow triggers on:
- Push to `main` or `develop` branches (when services/ directory changes)
- Manual trigger via GitHub Actions UI
- Pull requests to `main` branch (validation only)

## 📊 Monitoring and Maintenance

### Service Management

```bash
# Check service status
sudo systemctl status ekr-database-api

# View service logs
sudo journalctl -u ekr-database-api -f

# Restart service
sudo systemctl restart ekr-database-api
```

### System Health

```bash
# Run system health check
./deployment/scripts/deploy-manager.sh health

# View all EKR services
sudo systemctl list-units --type=service | grep ekr-
```

### Log Management

Logs are stored in:
- Service logs: `/var/log/ekr/`
- System logs: `journalctl -u ekr-service-name`
- Deployment logs: Ansible output

### Backup and Rollback

```bash
# Rollback a service
./deployment/scripts/deploy-manager.sh rollback service-name

# View backups
ls -la /opt/ekr/backups/

# Manual backup
sudo cp -r /opt/ekr/services/service-name /opt/ekr/backups/service-name-$(date +%Y%m%d_%H%M%S)
```

## 🔒 Security Considerations

### User Security
- Services run under dedicated `ekr` user
- No root privileges for services
- Proper file permissions

### Network Security
- Firewall rules for specific ports
- SELinux integration (if enabled)
- Internal communication only

### System Security
- Regular security updates
- SSH key-based authentication
- Service isolation

## 🐛 Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check service status
sudo systemctl status ekr-service-name

# Check logs
sudo journalctl -u ekr-service-name -n 50

# Check file permissions
ls -la /opt/ekr/services/service-name/
```

**Port Already in Use:**
```bash
# Find what's using the port
sudo ss -tulpn | grep :8001

# Kill process if needed
sudo kill -9 PID
```

**Deployment Fails:**
```bash
# Check SSH connectivity
ssh deploy@your-server

# Check Ansible inventory
ansible all -i inventory/hosts.yml -m ping

# Run deployment with debug
ansible-playbook -vvv -i inventory/hosts.yml deploy-service.yml -e "service_name=database-api"
```

**Health Check Fails:**
```bash
# Check service is running
curl http://localhost:8001/health

# Check service logs
sudo journalctl -u ekr-service-name -f

# Check network connectivity
ss -tulpn | grep :8001
```

### Debug Mode

Enable debug logging:

```bash
export ANSIBLE_DEBUG=1
export ANSIBLE_VERBOSITY=3

# Run with debug
./deployment/scripts/deploy-manager.sh deploy service-name staging
```

## 📈 Scaling and Performance

### Resource Tuning

Edit `services-config.yml`:

```yaml
resources:
  memory_limit: "2G"     # Increase memory
  cpu_limit: "4.0"       # Increase CPU cores
```

### Load Balancing

For high availability:
1. Deploy to multiple servers
2. Use a load balancer (nginx, HAProxy)
3. Configure health checks
4. Implement database replication

### Monitoring

Consider adding:
- Prometheus for metrics
- Grafana for dashboards
- Alertmanager for notifications
- Log aggregation (ELK stack)

## 🔄 Continuous Deployment

### GitOps Workflow

1. **Development**: Make changes in feature branches
2. **Testing**: Deploy to staging environment
3. **Review**: Create pull request
4. **Deployment**: Merge to main branch triggers production deployment
5. **Monitoring**: Monitor deployment success and service health

### Best Practices

- Always test in staging first
- Use feature flags for gradual rollouts
- Monitor deployment metrics
- Keep rollback plans ready
- Document configuration changes

## 📚 Additional Resources

- [AlmaLinux Documentation](https://docs.almalinux.org/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [Systemd Service Management](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs
3. Validate configuration
4. Check GitHub Issues
5. Contact the development team

---

**Happy Deploying!** 🚀