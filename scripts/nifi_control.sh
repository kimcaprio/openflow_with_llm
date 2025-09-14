#!/bin/bash

# NiFi Control Script
# This script provides easy control over Apache NiFi instance

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source the NiFi environment configuration
source "$PROJECT_ROOT/config/nifi_env.sh"

# PID file location
NIFI_PID_FILE="$NIFI_PID_DIR/nifi.pid"

# Function to get NiFi process ID
get_nifi_pid() {
    if [ -f "$NIFI_PID_FILE" ]; then
        cat "$NIFI_PID_FILE"
    else
        # Try to find NiFi process by name
        pgrep -f "nifi.*Bootstrap"
    fi
}

# Function to check if NiFi is running
is_nifi_running() {
    local pid=$(get_nifi_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to wait for NiFi to start
wait_for_nifi_start() {
    local max_wait=${1:-120}  # Default 2 minutes
    local wait_time=0
    
    print_status "INFO" "Waiting for NiFi to start (max ${max_wait}s)..."
    
    while [ $wait_time -lt $max_wait ]; do
        if curl -s -f "$NIFI_API_URL/system-diagnostics" > /dev/null 2>&1; then
            print_status "SUCCESS" "NiFi is ready and responding to API calls"
            return 0
        fi
        
        sleep 5
        wait_time=$((wait_time + 5))
        echo -n "."
    done
    
    echo ""
    print_status "WARNING" "NiFi may not be fully ready yet (timeout after ${max_wait}s)"
    return 1
}

# Function to wait for NiFi to stop
wait_for_nifi_stop() {
    local max_wait=${1:-60}  # Default 1 minute
    local wait_time=0
    
    print_status "INFO" "Waiting for NiFi to stop (max ${max_wait}s)..."
    
    while [ $wait_time -lt $max_wait ]; do
        if ! is_nifi_running; then
            print_status "SUCCESS" "NiFi has stopped"
            return 0
        fi
        
        sleep 2
        wait_time=$((wait_time + 2))
        echo -n "."
    done
    
    echo ""
    print_status "WARNING" "NiFi may still be running (timeout after ${max_wait}s)"
    return 1
}

# Function to start NiFi
start_nifi() {
    print_status "INFO" "Starting Apache NiFi..."
    
    # Check prerequisites
    if ! check_nifi_home || ! check_java; then
        return 1
    fi
    
    # Check if already running
    if is_nifi_running; then
        local pid=$(get_nifi_pid)
        print_status "WARNING" "NiFi is already running (PID: $pid)"
        return 0
    fi
    
    # Create necessary directories
    create_directories
    
    # Start NiFi
    cd "$NIFI_HOME"
    print_status "INFO" "Executing: $NIFI_HOME/bin/nifi.sh start"
    
    if "$NIFI_HOME/bin/nifi.sh" start; then
        print_status "SUCCESS" "NiFi start command executed"
        wait_for_nifi_start
        
        if is_nifi_running; then
            local pid=$(get_nifi_pid)
            print_status "SUCCESS" "NiFi is running (PID: $pid)"
            print_status "INFO" "NiFi Web UI: http://$NIFI_WEB_HTTP_HOST:$NIFI_WEB_HTTP_PORT/nifi"
            print_status "INFO" "NiFi API: $NIFI_API_URL"
        fi
    else
        print_status "ERROR" "Failed to start NiFi"
        return 1
    fi
}

# Function to stop NiFi
stop_nifi() {
    print_status "INFO" "Stopping Apache NiFi..."
    
    if ! is_nifi_running; then
        print_status "INFO" "NiFi is not running"
        return 0
    fi
    
    local pid=$(get_nifi_pid)
    print_status "INFO" "Stopping NiFi (PID: $pid)"
    
    cd "$NIFI_HOME"
    if "$NIFI_HOME/bin/nifi.sh" stop; then
        print_status "INFO" "NiFi stop command executed"
        wait_for_nifi_stop
    else
        print_status "ERROR" "Failed to execute NiFi stop command"
        return 1
    fi
}

# Function to restart NiFi
restart_nifi() {
    print_status "INFO" "Restarting Apache NiFi..."
    stop_nifi
    sleep 5
    start_nifi
}

# Function to get NiFi status
status_nifi() {
    print_status "INFO" "Checking NiFi status..."
    
    if is_nifi_running; then
        local pid=$(get_nifi_pid)
        print_status "SUCCESS" "NiFi is running (PID: $pid)"
        
        # Check API availability
        if curl -s -f "$NIFI_API_URL/system-diagnostics" > /dev/null 2>&1; then
            print_status "SUCCESS" "NiFi API is responding"
        else
            print_status "WARNING" "NiFi process is running but API is not responding"
        fi
        
        print_status "INFO" "NiFi Web UI: http://$NIFI_WEB_HTTP_HOST:$NIFI_WEB_HTTP_PORT/nifi"
        print_status "INFO" "NiFi API: $NIFI_API_URL"
    else
        print_status "INFO" "NiFi is not running"
    fi
}

# Function to show NiFi logs
logs_nifi() {
    local log_file="$NIFI_LOG_DIR/nifi-app.log"
    local lines=${1:-50}
    
    if [ -f "$log_file" ]; then
        print_status "INFO" "Showing last $lines lines of NiFi log:"
        echo "----------------------------------------"
        tail -n "$lines" "$log_file"
    else
        print_status "WARNING" "Log file not found: $log_file"
    fi
}

# Function to follow NiFi logs
follow_logs() {
    local log_file="$NIFI_LOG_DIR/nifi-app.log"
    
    if [ -f "$log_file" ]; then
        print_status "INFO" "Following NiFi logs (Ctrl+C to stop):"
        echo "----------------------------------------"
        tail -f "$log_file"
    else
        print_status "WARNING" "Log file not found: $log_file"
    fi
}

# Function to clean NiFi data
clean_nifi() {
    print_status "WARNING" "This will remove all NiFi data (flows, content, etc.)"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if is_nifi_running; then
            print_status "ERROR" "Please stop NiFi before cleaning data"
            return 1
        fi
        
        print_status "INFO" "Cleaning NiFi data directories..."
        
        local dirs_to_clean=(
            "$NIFI_DATABASE_DIRECTORY"
            "$NIFI_FLOWFILE_REPOSITORY_DIRECTORY"
            "$NIFI_CONTENT_REPOSITORY_DIRECTORY"
            "$NIFI_PROVENANCE_REPOSITORY_DIRECTORY"
        )
        
        for dir in "${dirs_to_clean[@]}"; do
            if [ -d "$dir" ]; then
                rm -rf "$dir"/*
                print_status "INFO" "Cleaned: $dir"
            fi
        done
        
        print_status "SUCCESS" "NiFi data cleaned"
    else
        print_status "INFO" "Clean operation cancelled"
    fi
}

# Function to show help
show_help() {
    echo "NiFi Control Script"
    echo "Usage: $0 {start|stop|restart|status|logs|follow|clean|help}"
    echo ""
    echo "Commands:"
    echo "  start    - Start NiFi"
    echo "  stop     - Stop NiFi"
    echo "  restart  - Restart NiFi"
    echo "  status   - Show NiFi status"
    echo "  logs     - Show recent NiFi logs (default: 50 lines)"
    echo "  follow   - Follow NiFi logs in real-time"
    echo "  clean    - Clean NiFi data directories (DESTRUCTIVE)"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs 100"
    echo "  $0 status"
}

# Main script logic
case "${1:-help}" in
    start)
        start_nifi
        ;;
    stop)
        stop_nifi
        ;;
    restart)
        restart_nifi
        ;;
    status)
        status_nifi
        ;;
    logs)
        logs_nifi "${2:-50}"
        ;;
    follow)
        follow_logs
        ;;
    clean)
        clean_nifi
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_status "ERROR" "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
