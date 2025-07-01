#!/usr/bin/env python3

"""
EKR Deployment Configuration Validator
This script validates the services-config.yml file and deployment structure.
"""

import os
import sys
import yaml
import json
from pathlib import Path


def log_success(message):
    print(f"✅ {message}")


def log_error(message):
    print(f"❌ {message}")


def log_warning(message):
    print(f"⚠️  {message}")


def log_info(message):
    print(f"ℹ️  {message}")


def validate_yaml_file(file_path):
    """Validate that a YAML file is syntactically correct."""
    try:
        with open(file_path, 'r') as f:
            yaml.safe_load(f)
        return True
    except yaml.YAMLError as e:
        log_error(f"Invalid YAML in {file_path}: {e}")
        return False
    except FileNotFoundError:
        log_error(f"File not found: {file_path}")
        return False


def validate_services_config():
    """Validate the services configuration file."""
    config_file = Path("services-config.yml")
    
    if not config_file.exists():
        log_error("services-config.yml not found")
        return False
    
    log_info("Validating services-config.yml...")
    
    if not validate_yaml_file(config_file):
        return False
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Check required top-level sections
    required_sections = ['global', 'services', 'almalinux', 'deployment']
    for section in required_sections:
        if section not in config:
            log_error(f"Missing required section: {section}")
            return False
    
    log_success("All required sections present")
    
    # Validate global configuration
    global_config = config['global']
    required_global_fields = ['service_type', 'runtime', 'user', 'group', 'working_directory']
    for field in required_global_fields:
        if field not in global_config:
            log_error(f"Missing required global field: {field}")
            return False
    
    log_success("Global configuration is valid")
    
    # Validate services
    services = config['services']
    if not services:
        log_warning("No services defined in configuration")
        return True
    
    for service_name, service_config in services.items():
        if not validate_service_config(service_name, service_config):
            return False
    
    log_success(f"All {len(services)} services have valid configurations")
    return True


def validate_service_config(service_name, service_config):
    """Validate individual service configuration."""
    required_fields = ['name', 'description', 'port', 'main_file']
    for field in required_fields:
        if field not in service_config:
            log_error(f"Service {service_name}: Missing required field '{field}'")
            return False
    
    # Validate port is a number
    try:
        port = int(service_config['port'])
        if port < 1 or port > 65535:
            log_error(f"Service {service_name}: Port {port} is out of valid range (1-65535)")
            return False
    except (ValueError, TypeError):
        log_error(f"Service {service_name}: Port must be a valid number")
        return False
    
    # Check if service directory exists
    service_dir = Path(f"services/{service_name}")
    if not service_dir.exists():
        log_warning(f"Service {service_name}: Directory 'services/{service_name}' not found")
    else:
        # Check if main file exists
        main_file = service_dir / service_config['main_file']
        if not main_file.exists():
            log_warning(f"Service {service_name}: Main file '{service_config['main_file']}' not found")
    
    return True


def validate_deployment_structure():
    """Validate the deployment directory structure."""
    log_info("Validating deployment structure...")
    
    required_files = [
        "deployment/deploy-service.yml",
        "deployment/health-check.yml",
        "deployment/system-health-check.yml",
        "deployment/rollback-service.yml",
        "deployment/cleanup.yml",
        "deployment/ansible.cfg",
        "deployment/templates/systemd-service.j2",
        "deployment/templates/environment.j2",
        "deployment/templates/startup-script.j2",
        "deployment/scripts/deploy-manager.sh",
        "deployment/inventory/hosts.yml.example",
        ".github/workflows/deploy-almalinux.yml"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        log_error("Missing required files:")
        for file_path in missing_files:
            log_error(f"  - {file_path}")
        return False
    
    log_success("All required deployment files are present")
    
    # Validate Ansible playbooks
    playbook_files = [
        "deployment/deploy-service.yml",
        "deployment/health-check.yml",
        "deployment/system-health-check.yml",
        "deployment/rollback-service.yml",
        "deployment/cleanup.yml"
    ]
    
    for playbook in playbook_files:
        if not validate_yaml_file(playbook):
            return False
    
    log_success("All Ansible playbooks have valid YAML syntax")
    
    # Check if deployment script is executable
    deploy_script = Path("deployment/scripts/deploy-manager.sh")
    if not os.access(deploy_script, os.X_OK):
        log_warning("deployment/scripts/deploy-manager.sh is not executable")
        log_info("Run: chmod +x deployment/scripts/deploy-manager.sh")
    
    return True


def validate_github_workflow():
    """Validate the GitHub workflow file."""
    log_info("Validating GitHub workflow...")
    
    workflow_file = Path(".github/workflows/deploy-almalinux.yml")
    if not workflow_file.exists():
        log_error("GitHub workflow file not found")
        return False
    
    return validate_yaml_file(workflow_file)


def check_services_directory():
    """Check the services directory and compare with configuration."""
    log_info("Checking services directory...")
    
    services_dir = Path("services")
    if not services_dir.exists():
        log_error("Services directory not found")
        return False
    
    # Get actual service directories
    actual_services = set()
    for item in services_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            actual_services.add(item.name)
    
    log_info(f"Found {len(actual_services)} service directories: {', '.join(sorted(actual_services))}")
    
    # Get configured services
    config_file = Path("services-config.yml")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        configured_services = set(config.get('services', {}).keys())
        
        log_info(f"Found {len(configured_services)} configured services: {', '.join(sorted(configured_services))}")
        
        # Check for missing configurations
        missing_config = actual_services - configured_services
        if missing_config:
            log_warning(f"Services without configuration: {', '.join(sorted(missing_config))}")
        
        # Check for extra configurations
        extra_config = configured_services - actual_services
        if extra_config:
            log_warning(f"Configured services without directories: {', '.join(sorted(extra_config))}")
    
    return True


def main():
    """Main validation function."""
    print("🔍 EKR Deployment Configuration Validator")
    print("=" * 50)
    
    success = True
    
    # Run all validations
    validations = [
        ("Services Configuration", validate_services_config),
        ("Deployment Structure", validate_deployment_structure),
        ("GitHub Workflow", validate_github_workflow),
        ("Services Directory", check_services_directory),
    ]
    
    for name, validation_func in validations:
        print(f"\n📋 {name}")
        print("-" * 30)
        if not validation_func():
            success = False
    
    print("\n" + "=" * 50)
    if success:
        log_success("All validations passed! 🎉")
        log_info("Your EKR deployment configuration is ready.")
        print("\nNext steps:")
        print("1. Copy deployment/inventory/hosts.yml.example to deployment/inventory/hosts.yml")
        print("2. Configure your target servers in the inventory file")
        print("3. Set up GitHub secrets for deployment")
        print("4. Test deployment on staging environment")
    else:
        log_error("Some validations failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()