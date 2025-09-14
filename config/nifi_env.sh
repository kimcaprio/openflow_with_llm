#!/bin/bash

# NiFi Environment Configuration
# This script sets up the environment variables for Apache NiFi

# NiFi Installation Path
export NIFI_HOME="/Users/kikim/Downloads/nifi-2.4.0"

# NiFi Configuration
export NIFI_PID_DIR="${NIFI_HOME}/run"
export NIFI_LOG_DIR="${NIFI_HOME}/logs"
export NIFI_CONF_DIR="${NIFI_HOME}/conf"

# Java Configuration
export JAVA_HOME="${JAVA_HOME:-$(/usr/libexec/java_home)}"
export NIFI_JVM_HEAP_INIT="512m"
export NIFI_JVM_HEAP_MAX="2g"

# NiFi Web Properties
export NIFI_WEB_HTTP_HOST="localhost"
export NIFI_WEB_HTTP_PORT="8080"
export NIFI_WEB_HTTPS_HOST=""
export NIFI_WEB_HTTPS_PORT=""

# NiFi Security (for development - disable HTTPS)
export NIFI_SECURITY_KEYSTORE=""
export NIFI_SECURITY_KEYSTOREPASSWD=""
export NIFI_SECURITY_TRUSTSTORE=""
export NIFI_SECURITY_TRUSTSTOREPASSWD=""

# NiFi Database
export NIFI_DATABASE_DIRECTORY="${NIFI_HOME}/database_repository"
export NIFI_FLOWFILE_REPOSITORY_DIRECTORY="${NIFI_HOME}/flowfile_repository"
export NIFI_CONTENT_REPOSITORY_DIRECTORY="${NIFI_HOME}/content_repository"
export NIFI_PROVENANCE_REPOSITORY_DIRECTORY="${NIFI_HOME}/provenance_repository"

# NiFi API Configuration
export NIFI_API_URL="http://localhost:8080/nifi-api"

# Color output for scripts
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
    esac
}

# Function to check if NiFi home exists
check_nifi_home() {
    if [ ! -d "$NIFI_HOME" ]; then
        print_status "ERROR" "NiFi home directory not found: $NIFI_HOME"
        print_status "INFO" "Please ensure NiFi is installed at the specified path"
        return 1
    fi
    
    if [ ! -f "$NIFI_HOME/bin/nifi.sh" ]; then
        print_status "ERROR" "NiFi executable not found: $NIFI_HOME/bin/nifi.sh"
        return 1
    fi
    
    return 0
}

# Function to check Java installation
check_java() {
    if [ -z "$JAVA_HOME" ]; then
        print_status "ERROR" "JAVA_HOME is not set"
        return 1
    fi
    
    if [ ! -x "$JAVA_HOME/bin/java" ]; then
        print_status "ERROR" "Java executable not found: $JAVA_HOME/bin/java"
        return 1
    fi
    
    local java_version=$("$JAVA_HOME/bin/java" -version 2>&1 | head -n 1 | cut -d'"' -f2)
    print_status "INFO" "Using Java version: $java_version"
    return 0
}

# Function to create necessary directories
create_directories() {
    local dirs=(
        "$NIFI_PID_DIR"
        "$NIFI_LOG_DIR"
        "$NIFI_DATABASE_DIRECTORY"
        "$NIFI_FLOWFILE_REPOSITORY_DIRECTORY"
        "$NIFI_CONTENT_REPOSITORY_DIRECTORY"
        "$NIFI_PROVENANCE_REPOSITORY_DIRECTORY"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "INFO" "Created directory: $dir"
        fi
    done
}

# Export functions for use in other scripts
export -f print_status
export -f check_nifi_home
export -f check_java
export -f create_directories

print_status "INFO" "NiFi environment configuration loaded"
print_status "INFO" "NIFI_HOME: $NIFI_HOME"
print_status "INFO" "JAVA_HOME: $JAVA_HOME"
print_status "INFO" "NiFi API URL: $NIFI_API_URL"
