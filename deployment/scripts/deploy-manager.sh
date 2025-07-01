#!/bin/bash

# EKR Deployment Management Script
# This script provides utility functions for managing EKR service deployments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
CONFIG_FILE="${PROJECT_ROOT}/services-config.yml"
DEPLOYMENT_DIR="${SCRIPT_DIR}/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    log_info "Checking requirements..."
    
    local missing_tools=()
    
    if ! command -v ansible &> /dev/null; then
        missing_tools+=("ansible")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    if ! command -v yq &> /dev/null && ! python3 -c "import yaml" &> /dev/null; then
        missing_tools+=("python3-yaml")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install the missing tools and try again."
        exit 1
    fi
    
    log_success "All requirements satisfied"
}

# List available services
list_services() {
    log_info "Available EKR services:"
    if [ -f "$CONFIG_FILE" ]; then
        python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
    services = config.get('services', {})
    for name, conf in services.items():
        print(f'  - {name}: {conf.get(\"description\", \"No description\")} (Port: {conf.get(\"port\", \"Unknown\")})')
"
    else
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
}

# Validate service configuration
validate_service() {
    local service_name="$1"
    
    if [ -z "$service_name" ]; then
        log_error "Service name is required"
        return 1
    fi
    
    log_info "Validating service: $service_name"
    
    # Check if service exists in config
    python3 -c "
import yaml
import sys
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
    services = config.get('services', {})
    if '$service_name' not in services:
        print('Service $service_name not found in configuration')
        sys.exit(1)
    
    service_config = services['$service_name']
    required_fields = ['name', 'port', 'main_file']
    
    for field in required_fields:
        if field not in service_config:
            print(f'Missing required field: {field}')
            sys.exit(1)
    
    print('Service configuration is valid')
"
    
    if [ $? -eq 0 ]; then
        log_success "Service $service_name configuration is valid"
        return 0
    else
        log_error "Service $service_name configuration is invalid"
        return 1
    fi
}

# Deploy a single service
deploy_service() {
    local service_name="$1"
    local environment="${2:-staging}"
    
    if [ -z "$service_name" ]; then
        log_error "Service name is required"
        return 1
    fi
    
    validate_service "$service_name" || return 1
    
    log_info "Deploying service: $service_name to $environment"
    
    cd "$DEPLOYMENT_DIR"
    
    ansible-playbook -i inventory/hosts.yml deploy-service.yml \
        -e "service_name=$service_name" \
        -e "target_environment=$environment" \
        -e "deployment_timestamp=$(date +%Y%m%d_%H%M%S)" \
        -v
    
    if [ $? -eq 0 ]; then
        log_success "Service $service_name deployed successfully"
        
        # Run health check
        log_info "Running health check..."
        ansible-playbook -i inventory/hosts.yml health-check.yml \
            -e "service_name=$service_name" \
            -v
        
        if [ $? -eq 0 ]; then
            log_success "Health check passed for $service_name"
        else
            log_warning "Health check failed for $service_name"
            return 1
        fi
    else
        log_error "Failed to deploy service $service_name"
        return 1
    fi
}

# Rollback a service
rollback_service() {
    local service_name="$1"
    
    if [ -z "$service_name" ]; then
        log_error "Service name is required"
        return 1
    fi
    
    log_warning "Rolling back service: $service_name"
    
    cd "$DEPLOYMENT_DIR"
    
    ansible-playbook -i inventory/hosts.yml rollback-service.yml \
        -e "service_name=$service_name" \
        -v
    
    if [ $? -eq 0 ]; then
        log_success "Service $service_name rolled back successfully"
    else
        log_error "Failed to rollback service $service_name"
        return 1
    fi
}

# System health check
system_health() {
    log_info "Running system health check..."
    
    cd "$DEPLOYMENT_DIR"
    
    ansible-playbook -i inventory/hosts.yml system-health-check.yml -v
    
    if [ $? -eq 0 ]; then
        log_success "System health check completed"
    else
        log_warning "System health check detected issues"
        return 1
    fi
}

# Cleanup old deployments
cleanup() {
    log_info "Running cleanup..."
    
    cd "$DEPLOYMENT_DIR"
    
    ansible-playbook -i inventory/hosts.yml cleanup.yml -v
    
    if [ $? -eq 0 ]; then
        log_success "Cleanup completed"
    else
        log_warning "Cleanup completed with warnings"
        return 1
    fi
}

# Show usage
usage() {
    echo "EKR Deployment Management Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  list                           List available services"
    echo "  validate SERVICE_NAME          Validate service configuration"
    echo "  deploy SERVICE_NAME [ENV]      Deploy a service (ENV: staging|production)"
    echo "  rollback SERVICE_NAME          Rollback a service"
    echo "  health                         Run system health check"
    echo "  cleanup                        Clean up old deployments"
    echo "  check                          Check requirements"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 deploy database-api staging"
    echo "  $0 rollback llm-query"
    echo "  $0 health"
    echo ""
}

# Main command handling
case "${1:-}" in
    "list")
        check_requirements
        list_services
        ;;
    "validate")
        check_requirements
        validate_service "$2"
        ;;
    "deploy")
        check_requirements
        deploy_service "$2" "$3"
        ;;
    "rollback")
        check_requirements
        rollback_service "$2"
        ;;
    "health")
        check_requirements
        system_health
        ;;
    "cleanup")
        check_requirements
        cleanup
        ;;
    "check")
        check_requirements
        ;;
    "help"|"-h"|"--help")
        usage
        ;;
    *)
        echo "Unknown command: ${1:-}"
        echo ""
        usage
        exit 1
        ;;
esac