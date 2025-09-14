#!/usr/bin/env python3
"""
Test Script for NiFi MCP Server

This script demonstrates how to interact with the NiFi MCP Server programmatically.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.mcp.nifi_mcp_server import MCPRequest, NiFiMCPServer
from src.nifi.api_client import NiFiConnectionConfig


async def test_mcp_server():
    """Test the MCP server functionality."""
    print("🚀 Testing NiFi MCP Server...")
    
    # Create NiFi configuration
    nifi_config = NiFiConnectionConfig(
        base_url="https://localhost:8443/nifi-api",
        verify_ssl=False,
        timeout=30
    )
    
    # Create MCP server
    server = NiFiMCPServer(nifi_config=nifi_config, llm_provider_type="openai")
    
    try:
        # Initialize server
        print("📡 Initializing MCP server...")
        await server.initialize()
        print("✅ Server initialized successfully")
        
        # Test queries
        test_queries = [
            "List all process groups",
            "Show me the processors in the root group",
            "What's the status of my NiFi flow?",
            "Search for GetFile processors",
            "Help me understand NiFi"
        ]
        
        for query in test_queries:
            print(f"\n💬 Query: {query}")
            
            request = MCPRequest(
                query=query,
                session_id="test_session"
            )
            
            response = await server.process_query(request)
            
            print(f"🎯 Intent: {response.intent}")
            print(f"📊 Confidence: {response.confidence:.2%}" if response.confidence else "📊 Confidence: N/A")
            print(f"✅ Success: {response.success}")
            print(f"💬 Response: {response.message}")
            
            if response.data:
                print(f"📋 Data keys: {list(response.data.keys())}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await server.shutdown()
        print("\n🔚 Server shutdown complete")


async def test_intent_processor():
    """Test the intent processor separately."""
    print("\n🧠 Testing Intent Processor...")
    
    from src.llm.intent_processor import create_intent_processor
    
    try:
        # Create intent processor
        processor = create_intent_processor("openai")
        
        test_queries = [
            "List all process groups",
            "Create a processor called GetFile",
            "Start the data processing flow",
            "Search for Kafka processors",
            "What is the status?"
        ]
        
        for query in test_queries:
            print(f"\n💭 Processing: {query}")
            
            result = await processor.process_query(query)
            
            print(f"🎯 Intent: {result.intent.value}")
            print(f"📊 Confidence: {result.confidence:.2%}")
            print(f"📝 Explanation: {result.explanation}")
            
            if result.parameters.processor_type:
                print(f"⚙️ Processor Type: {result.parameters.processor_type}")
            if result.parameters.process_group_name:
                print(f"📁 Process Group: {result.parameters.process_group_name}")
            if result.parameters.search_query:
                print(f"🔍 Search Query: {result.parameters.search_query}")
    
    except Exception as e:
        print(f"❌ Intent Processor Error: {e}")
        import traceback
        traceback.print_exc()


async def test_nifi_client():
    """Test the NiFi API client."""
    print("\n🔌 Testing NiFi API Client...")
    
    from src.nifi.api_client import create_nifi_client
    
    try:
        # Create NiFi client
        client = create_nifi_client(
            base_url="https://localhost:8443/nifi-api",
            verify_ssl=False
        )
        
        async with client:
            # Test health check
            print("🏥 Checking NiFi health...")
            healthy = await client.health_check()
            print(f"✅ NiFi Health: {'Healthy' if healthy else 'Unhealthy'}")
            
            if healthy:
                # Test basic operations
                print("\n📁 Getting process groups...")
                process_groups = await client.get_process_groups()
                print(f"Found {len(process_groups)} process group(s)")
                
                print("\n⚙️ Getting processors...")
                processors = await client.get_processors()
                print(f"Found {len(processors)} processor(s)")
                
                print("\n🔗 Getting connections...")
                connections = await client.get_connections()
                print(f"Found {len(connections)} connection(s)")
                
                print("\n📋 Getting templates...")
                templates = await client.get_templates()
                print(f"Found {len(templates)} template(s)")
    
    except Exception as e:
        print(f"❌ NiFi Client Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function."""
    print("🧪 NiFi MCP Server Test Suite")
    print("=" * 50)
    
    # Test individual components
    await test_intent_processor()
    await test_nifi_client()
    
    # Test full MCP server
    await test_mcp_server()
    
    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
