"""
NiFi Manager Utility Module

This module provides Python utilities for managing Apache NiFi instance,
including starting, stopping, and monitoring NiFi processes.
"""

import os
import subprocess
import time
import requests
import psutil
from typing import Optional, Dict, Any, List
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class NiFiManager:
    """
    Manages Apache NiFi instance operations.
    """
    
    def __init__(self, nifi_home: Optional[str] = None, config_file: Optional[str] = None):
        """
        Initialize NiFi Manager.
        
        Args:
            nifi_home: Path to NiFi installation directory
            config_file: Path to NiFi configuration YAML file
        """
        self.nifi_home = nifi_home or os.getenv('NIFI_HOME', '/Users/kikim/Downloads/nifi-2.4.0')
        self.config_file = config_file or 'config/nifi_config.yaml'
        self.config = self._load_config()
        
        # Set paths
        self.nifi_script = Path(self.nifi_home) / 'bin' / 'nifi.sh'
        self.pid_dir = Path(self.nifi_home) / 'run'
        self.pid_file = self.pid_dir / 'nifi.pid'
        self.log_dir = Path(self.nifi_home) / 'logs'
        
        # API configuration
        self.api_base_url = self.config.get('nifi', {}).get('api', {}).get('base_url', 
                                                            'http://localhost:8080/nifi-api')
        self.api_timeout = self.config.get('nifi', {}).get('api', {}).get('timeout', 30)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load NiFi configuration from YAML file."""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"Config file not found: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def _run_command(self, command: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run a shell command and return the result.
        
        Args:
            command: Command to run as list of strings
            cwd: Working directory for the command
            
        Returns:
            CompletedProcess object with result
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.nifi_home,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(command)}")
            raise
        except Exception as e:
            logger.error(f"Error running command {' '.join(command)}: {e}")
            raise
    
    def _get_nifi_pid(self) -> Optional[int]:
        """
        Get NiFi process ID.
        
        Returns:
            Process ID if NiFi is running, None otherwise
        """
        # Try to read from PID file first
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                    if psutil.pid_exists(pid):
                        return pid
            except (ValueError, IOError):
                pass
        
        # Try to find by process name
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'java' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'nifi' in cmdline.lower() and 'bootstrap' in cmdline.lower():
                        return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return None
    
    def is_running(self) -> bool:
        """
        Check if NiFi is currently running.
        
        Returns:
            True if NiFi is running, False otherwise
        """
        pid = self._get_nifi_pid()
        return pid is not None
    
    def start(self, wait_for_ready: bool = True, timeout: int = 120) -> bool:
        """
        Start NiFi instance.
        
        Args:
            wait_for_ready: Whether to wait for NiFi to be fully ready
            timeout: Maximum time to wait for startup (seconds)
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running():
            logger.info("NiFi is already running")
            return True
        
        if not self.nifi_script.exists():
            logger.error(f"NiFi script not found: {self.nifi_script}")
            return False
        
        # Create necessary directories
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Starting NiFi...")
        result = self._run_command([str(self.nifi_script), 'start'])
        
        if result.returncode != 0:
            logger.error(f"Failed to start NiFi: {result.stderr}")
            return False
        
        logger.info("NiFi start command executed successfully")
        
        if wait_for_ready:
            return self.wait_for_ready(timeout)
        
        return True
    
    def stop(self, timeout: int = 60) -> bool:
        """
        Stop NiFi instance.
        
        Args:
            timeout: Maximum time to wait for shutdown (seconds)
            
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running():
            logger.info("NiFi is not running")
            return True
        
        logger.info("Stopping NiFi...")
        result = self._run_command([str(self.nifi_script), 'stop'])
        
        if result.returncode != 0:
            logger.error(f"Failed to stop NiFi: {result.stderr}")
            return False
        
        # Wait for process to stop
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running():
                logger.info("NiFi stopped successfully")
                return True
            time.sleep(2)
        
        logger.warning(f"NiFi did not stop within {timeout} seconds")
        return False
    
    def restart(self, timeout: int = 120) -> bool:
        """
        Restart NiFi instance.
        
        Args:
            timeout: Maximum time to wait for restart (seconds)
            
        Returns:
            True if restarted successfully, False otherwise
        """
        logger.info("Restarting NiFi...")
        
        if not self.stop():
            return False
        
        time.sleep(5)  # Brief pause between stop and start
        
        return self.start(timeout=timeout)
    
    def wait_for_ready(self, timeout: int = 120) -> bool:
        """
        Wait for NiFi to be fully ready and responding to API calls.
        
        Args:
            timeout: Maximum time to wait (seconds)
            
        Returns:
            True if NiFi is ready, False if timeout
        """
        logger.info(f"Waiting for NiFi to be ready (timeout: {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.api_base_url}/system-diagnostics",
                    timeout=5
                )
                if response.status_code == 200:
                    logger.info("NiFi is ready and responding to API calls")
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(5)
        
        logger.warning(f"NiFi did not become ready within {timeout} seconds")
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive NiFi status information.
        
        Returns:
            Dictionary containing status information
        """
        status = {
            'running': self.is_running(),
            'pid': self._get_nifi_pid(),
            'api_available': False,
            'web_ui_url': None,
            'api_url': self.api_base_url,
            'nifi_home': str(self.nifi_home),
            'version': None
        }
        
        if status['running']:
            # Check API availability
            try:
                response = requests.get(
                    f"{self.api_base_url}/system-diagnostics",
                    timeout=5
                )
                status['api_available'] = response.status_code == 200
            except requests.RequestException:
                pass
            
            # Set web UI URL
            web_config = self.config.get('nifi', {}).get('web', {}).get('http', {})
            host = web_config.get('host', 'localhost')
            port = web_config.get('port', 8080)
            status['web_ui_url'] = f"http://{host}:{port}/nifi"
        
        return status
    
    def get_logs(self, lines: int = 50) -> List[str]:
        """
        Get recent NiFi log entries.
        
        Args:
            lines: Number of lines to retrieve
            
        Returns:
            List of log lines
        """
        log_file = self.log_dir / 'nifi-app.log'
        
        if not log_file.exists():
            logger.warning(f"Log file not found: {log_file}")
            return []
        
        try:
            result = self._run_command(['tail', '-n', str(lines), str(log_file)])
            if result.returncode == 0:
                return result.stdout.split('\n')
            else:
                logger.error(f"Error reading logs: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return []
    
    def test_api_connection(self) -> bool:
        """
        Test connection to NiFi API.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/system-diagnostics",
                timeout=self.api_timeout
            )
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    def get_system_diagnostics(self) -> Optional[Dict[str, Any]]:
        """
        Get NiFi system diagnostics information.
        
        Returns:
            System diagnostics data or None if unavailable
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/system-diagnostics",
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get system diagnostics: {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.error(f"Error getting system diagnostics: {e}")
            return None
    
    def cleanup_data(self, confirm: bool = False) -> bool:
        """
        Clean up NiFi data directories (DESTRUCTIVE operation).
        
        Args:
            confirm: Must be True to actually perform cleanup
            
        Returns:
            True if cleanup successful, False otherwise
        """
        if not confirm:
            logger.warning("Cleanup not performed - confirmation required")
            return False
        
        if self.is_running():
            logger.error("Cannot cleanup data while NiFi is running")
            return False
        
        # Directories to clean
        data_dirs = [
            Path(self.nifi_home) / 'database_repository',
            Path(self.nifi_home) / 'flowfile_repository',
            Path(self.nifi_home) / 'content_repository',
            Path(self.nifi_home) / 'provenance_repository'
        ]
        
        try:
            for data_dir in data_dirs:
                if data_dir.exists():
                    import shutil
                    shutil.rmtree(data_dir)
                    data_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Cleaned directory: {data_dir}")
            
            logger.info("NiFi data cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False


# Convenience functions for quick access
def get_nifi_manager() -> NiFiManager:
    """Get a configured NiFi manager instance."""
    return NiFiManager()


def is_nifi_running() -> bool:
    """Quick check if NiFi is running."""
    return get_nifi_manager().is_running()


def start_nifi(wait_for_ready: bool = True) -> bool:
    """Quick start NiFi."""
    return get_nifi_manager().start(wait_for_ready=wait_for_ready)


def stop_nifi() -> bool:
    """Quick stop NiFi."""
    return get_nifi_manager().stop()


def restart_nifi() -> bool:
    """Quick restart NiFi."""
    return get_nifi_manager().restart()


def get_nifi_status() -> Dict[str, Any]:
    """Quick get NiFi status."""
    return get_nifi_manager().get_status()
