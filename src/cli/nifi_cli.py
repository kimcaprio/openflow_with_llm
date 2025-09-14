"""
NiFi CLI Module

Command-line interface for managing Apache NiFi instance.
"""

import click
import sys
from pathlib import Path
import json
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.nifi_manager import NiFiManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--nifi-home', envvar='NIFI_HOME', help='NiFi installation directory')
@click.option('--config', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, nifi_home, config, verbose):
    """NiFi Management CLI for Openflow with LLM project."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    ctx.ensure_object(dict)
    ctx.obj['manager'] = NiFiManager(nifi_home=nifi_home, config_file=config)


@cli.command()
@click.option('--wait/--no-wait', default=True, help='Wait for NiFi to be ready')
@click.option('--timeout', default=120, help='Timeout in seconds')
@click.pass_context
def start(ctx, wait, timeout):
    """Start NiFi instance."""
    manager: NiFiManager = ctx.obj['manager']
    
    click.echo("🚀 Starting Apache NiFi...")
    
    if manager.is_running():
        click.echo("✅ NiFi is already running")
        return
    
    success = manager.start(wait_for_ready=wait, timeout=timeout)
    
    if success:
        status = manager.get_status()
        click.echo("✅ NiFi started successfully")
        click.echo(f"   PID: {status['pid']}")
        if status['web_ui_url']:
            click.echo(f"   Web UI: {status['web_ui_url']}")
        click.echo(f"   API: {status['api_url']}")
    else:
        click.echo("❌ Failed to start NiFi")
        sys.exit(1)


@cli.command()
@click.option('--timeout', default=60, help='Timeout in seconds')
@click.pass_context
def stop(ctx, timeout):
    """Stop NiFi instance."""
    manager: NiFiManager = ctx.obj['manager']
    
    click.echo("🛑 Stopping Apache NiFi...")
    
    if not manager.is_running():
        click.echo("ℹ️  NiFi is not running")
        return
    
    success = manager.stop(timeout=timeout)
    
    if success:
        click.echo("✅ NiFi stopped successfully")
    else:
        click.echo("❌ Failed to stop NiFi")
        sys.exit(1)


@cli.command()
@click.option('--timeout', default=120, help='Timeout in seconds')
@click.pass_context
def restart(ctx, timeout):
    """Restart NiFi instance."""
    manager: NiFiManager = ctx.obj['manager']
    
    click.echo("🔄 Restarting Apache NiFi...")
    
    success = manager.restart(timeout=timeout)
    
    if success:
        status = manager.get_status()
        click.echo("✅ NiFi restarted successfully")
        click.echo(f"   PID: {status['pid']}")
        if status['web_ui_url']:
            click.echo(f"   Web UI: {status['web_ui_url']}")
    else:
        click.echo("❌ Failed to restart NiFi")
        sys.exit(1)


@cli.command()
@click.option('--json', 'output_json', is_flag=True, help='Output status as JSON')
@click.pass_context
def status(ctx, output_json):
    """Show NiFi status."""
    manager: NiFiManager = ctx.obj['manager']
    
    status = manager.get_status()
    
    if output_json:
        click.echo(json.dumps(status, indent=2))
        return
    
    click.echo("📊 NiFi Status:")
    click.echo(f"   Running: {'✅ Yes' if status['running'] else '❌ No'}")
    
    if status['running']:
        click.echo(f"   PID: {status['pid']}")
        click.echo(f"   API Available: {'✅ Yes' if status['api_available'] else '❌ No'}")
        if status['web_ui_url']:
            click.echo(f"   Web UI: {status['web_ui_url']}")
        click.echo(f"   API URL: {status['api_url']}")
    
    click.echo(f"   NiFi Home: {status['nifi_home']}")


@cli.command()
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.pass_context
def logs(ctx, lines, follow):
    """Show NiFi logs."""
    manager: NiFiManager = ctx.obj['manager']
    
    if follow:
        click.echo("📋 Following NiFi logs (Ctrl+C to stop)...")
        # For follow mode, use the shell script
        import subprocess
        try:
            subprocess.run([
                str(Path(__file__).parent.parent.parent / 'scripts' / 'nifi_control.sh'),
                'follow'
            ])
        except KeyboardInterrupt:
            click.echo("\n👋 Stopped following logs")
    else:
        click.echo(f"📋 Last {lines} lines of NiFi logs:")
        log_lines = manager.get_logs(lines=lines)
        
        if not log_lines:
            click.echo("No logs available")
            return
        
        for line in log_lines:
            if line.strip():
                click.echo(line)


@cli.command()
@click.pass_context
def test_api(ctx):
    """Test NiFi API connection."""
    manager: NiFiManager = ctx.obj['manager']
    
    click.echo("🔍 Testing NiFi API connection...")
    
    if manager.test_api_connection():
        click.echo("✅ API connection successful")
        
        # Get system diagnostics
        diagnostics = manager.get_system_diagnostics()
        if diagnostics:
            click.echo("📊 System Diagnostics:")
            system_diag = diagnostics.get('systemDiagnostics', {})
            
            # Memory info
            heap_info = system_diag.get('aggregateSnapshot', {}).get('heapUtilization', {})
            if heap_info:
                click.echo(f"   Heap Used: {heap_info.get('utilization', 'N/A')}")
                click.echo(f"   Heap Max: {heap_info.get('max', 'N/A')}")
            
            # Processor info
            processor_info = system_diag.get('aggregateSnapshot', {})
            if processor_info:
                click.echo(f"   Active Threads: {processor_info.get('activeThreadCount', 'N/A')}")
                click.echo(f"   Total Threads: {processor_info.get('totalThreadCount', 'N/A')}")
    else:
        click.echo("❌ API connection failed")
        click.echo("   Make sure NiFi is running and accessible")
        sys.exit(1)


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to clean all NiFi data?')
@click.pass_context
def clean(ctx):
    """Clean NiFi data directories (DESTRUCTIVE)."""
    manager: NiFiManager = ctx.obj['manager']
    
    if manager.is_running():
        click.echo("❌ Cannot clean data while NiFi is running")
        click.echo("   Please stop NiFi first")
        sys.exit(1)
    
    click.echo("🧹 Cleaning NiFi data directories...")
    
    success = manager.cleanup_data(confirm=True)
    
    if success:
        click.echo("✅ NiFi data cleaned successfully")
    else:
        click.echo("❌ Failed to clean NiFi data")
        sys.exit(1)


@cli.command()
@click.pass_context
def info(ctx):
    """Show NiFi installation information."""
    manager: NiFiManager = ctx.obj['manager']
    
    click.echo("ℹ️  NiFi Installation Information:")
    click.echo(f"   NiFi Home: {manager.nifi_home}")
    click.echo(f"   NiFi Script: {manager.nifi_script}")
    click.echo(f"   PID File: {manager.pid_file}")
    click.echo(f"   Log Directory: {manager.log_dir}")
    click.echo(f"   API Base URL: {manager.api_base_url}")
    
    # Check if paths exist
    click.echo("\n📁 Path Validation:")
    click.echo(f"   NiFi Home exists: {'✅' if Path(manager.nifi_home).exists() else '❌'}")
    click.echo(f"   NiFi Script exists: {'✅' if manager.nifi_script.exists() else '❌'}")
    click.echo(f"   Log Directory exists: {'✅' if manager.log_dir.exists() else '❌'}")


if __name__ == '__main__':
    cli()
