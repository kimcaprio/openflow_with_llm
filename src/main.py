"""
Main Entry Point for Openflow with LLM

This module provides the main entry point for running the NiFi MCP Server
and associated components.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional
import click
import uvicorn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.mcp.nifi_mcp_server import create_app, NiFiMCPServer
from src.utils.config import get_merged_config
from src.utils.nifi_manager import NiFiManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """Openflow with LLM - NiFi Natural Language Interface."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--workers', default=1, help='Number of worker processes')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
@click.pass_context
def server(ctx, host, port, workers, reload):
    """Start the NiFi MCP Server."""
    logger.info("Starting NiFi MCP Server...")
    
    # Load configuration
    config = get_merged_config()
    
    # Override with command line arguments
    host = host or config.get('server', {}).get('host', '0.0.0.0')
    port = port or config.get('server', {}).get('port', 8000)
    workers = workers or config.get('server', {}).get('workers', 1)
    
    # Create FastAPI app
    app = create_app()
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
        log_level="info" if not ctx.obj.get('verbose') else "debug"
    )


@cli.command()
@click.option('--server-host', default='localhost', help='MCP server host')
@click.option('--server-port', default=8000, help='MCP server port')
@click.option('--ui-port', default=9501, help='Streamlit UI port')
@click.pass_context
def ui(ctx, server_host, server_port, ui_port):
    """Start the Streamlit chat interface."""
    logger.info("Starting Streamlit chat interface...")
    
    # Set environment variables for the UI
    os.environ['MCP_SERVER_URL'] = f"http://{server_host}:{server_port}"
    
    # Import and run Streamlit app
    try:
        import streamlit.web.cli as stcli
        from ui.chat_interface import main as ui_main
        
        # Run Streamlit
        sys.argv = [
            "streamlit",
            "run",
            str(Path(__file__).parent / "ui" / "chat_interface.py"),
            "--server.port", str(ui_port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        stcli.main()
        
    except ImportError:
        logger.error("Streamlit not installed. Install with: uv add --group ui streamlit")
        sys.exit(1)


@cli.command()
@click.option('--server-host', default='0.0.0.0', help='MCP server host')
@click.option('--server-port', default=8000, help='MCP server port')
@click.option('--ui-port', default=9501, help='Streamlit UI port')
@click.option('--workers', default=1, help='Number of server workers')
@click.pass_context
def run(ctx, server_host, server_port, ui_port, workers):
    """Run both the MCP server and UI (development mode)."""
    import subprocess
    import time
    import signal
    import threading
    
    logger.info("Starting both MCP server and UI...")
    
    processes = []
    
    def signal_handler(signum, frame):
        logger.info("Shutting down...")
        for proc in processes:
            proc.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start MCP server
        server_cmd = [
            sys.executable, "-m", "src.main", "server",
            "--host", server_host,
            "--port", str(server_port),
            "--workers", str(workers)
        ]
        
        if ctx.obj.get('verbose'):
            server_cmd.append('--verbose')
        
        server_proc = subprocess.Popen(server_cmd)
        processes.append(server_proc)
        logger.info(f"Started MCP server on {server_host}:{server_port}")
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Start UI
        ui_cmd = [
            sys.executable, "-m", "src.main", "ui",
            "--server-host", server_host,
            "--server-port", str(server_port),
            "--ui-port", str(ui_port)
        ]
        
        ui_proc = subprocess.Popen(ui_cmd)
        processes.append(ui_proc)
        logger.info(f"Started UI on port {ui_port}")
        
        # Wait for processes
        for proc in processes:
            proc.wait()
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        for proc in processes:
            proc.terminate()


@cli.command()
@click.argument('query')
@click.option('--server-url', default='http://localhost:8000', help='MCP server URL')
@click.pass_context
def query(ctx, query, server_url):
    """Send a query to the MCP server."""
    import httpx
    
    async def send_query():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{server_url}/query",
                    json={"query": query, "session_id": "cli"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    print(f"\n🎯 Intent: {result.get('intent', 'unknown')}")
                    print(f"📊 Confidence: {result.get('confidence', 0):.2%}")
                    print(f"✅ Success: {result.get('success', False)}")
                    print(f"\n💬 Response: {result.get('message', 'No message')}")
                    
                    if result.get('data'):
                        print(f"\n📋 Data:")
                        import json
                        print(json.dumps(result['data'], indent=2))
                        
                else:
                    print(f"❌ Server error: {response.status_code}")
                    print(response.text)
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    asyncio.run(send_query())


@cli.group()
@click.pass_context
def nifi(ctx):
    """NiFi management commands."""
    pass


@nifi.command()
@click.pass_context
def start(ctx):
    """Start NiFi instance."""
    async def start_nifi():
        manager = NiFiManager()
        if await manager.start():
            print("✅ NiFi started successfully")
        else:
            print("❌ Failed to start NiFi")
    
    asyncio.run(start_nifi())


@nifi.command()
@click.pass_context
def stop(ctx):
    """Stop NiFi instance."""
    async def stop_nifi():
        manager = NiFiManager()
        if await manager.stop():
            print("✅ NiFi stopped successfully")
        else:
            print("❌ Failed to stop NiFi")
    
    asyncio.run(stop_nifi())


@nifi.command()
@click.pass_context
def status(ctx):
    """Check NiFi status."""
    async def check_status():
        manager = NiFiManager()
        status = await manager.get_status()
        
        print(f"🏥 NiFi Status:")
        print(f"   Running: {'✅' if status['running'] else '❌'} {status['running']}")
        print(f"   PID: {status.get('pid', 'N/A')}")
        print(f"   API Available: {'✅' if status.get('api_available') else '❌'} {status.get('api_available', False)}")
        print(f"   Web UI: {status.get('web_ui_url', 'N/A')}")
        print(f"   NiFi Home: {status['nifi_home']}")
    
    asyncio.run(check_status())


@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration."""
    config = get_merged_config()
    
    print("📋 Current Configuration:")
    import json
    print(json.dumps(config, indent=2, default=str))


@cli.command()
@click.pass_context
def health(ctx):
    """Check overall system health."""
    async def check_health():
        print("🏥 System Health Check:")
        
        # Check NiFi
        manager = NiFiManager()
        nifi_status = await manager.get_status()
        print(f"   NiFi: {'✅' if nifi_status['running'] else '❌'} {'Running' if nifi_status['running'] else 'Stopped'}")
        
        # Check MCP Server
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=5.0)
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"   MCP Server: ✅ {health_data.get('status', 'unknown')}")
                else:
                    print(f"   MCP Server: ❌ HTTP {response.status_code}")
        except Exception as e:
            print(f"   MCP Server: ❌ Not responding ({e})")
        
        # Check LLM providers
        try:
            from llm.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider()
            if await provider.is_available():
                print("   OpenAI: ✅ Available")
            else:
                print("   OpenAI: ❌ Not available")
        except Exception:
            print("   OpenAI: ❌ Not configured")
        
        try:
            from llm.providers.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider()
            if await provider.is_available():
                print("   Anthropic: ✅ Available")
            else:
                print("   Anthropic: ❌ Not available")
        except Exception:
            print("   Anthropic: ❌ Not configured")
    
    asyncio.run(check_health())


if __name__ == '__main__':
    cli()
