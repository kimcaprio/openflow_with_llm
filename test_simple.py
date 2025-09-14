#!/usr/bin/env python3
"""
Simple Test Script for NiFi MCP Server

This script tests the MCP server functionality without requiring a running NiFi instance.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.llm.intent_processor import create_intent_processor, NiFiIntent


async def test_intent_processor():
    """Test the intent processor with various queries."""
    print("🧠 Testing Intent Processor...")
    print("=" * 50)
    
    try:
        # Create intent processor (will use pattern matching if no LLM available)
        processor = create_intent_processor("openai")
        
        test_queries = [
            "List all process groups",
            "Show me the processors in the root group", 
            "Create a GetFile processor",
            "Start the data processing flow",
            "Search for Kafka processors",
            "What's the status of my NiFi instance?",
            "Help me understand NiFi processors",
            "Create a process group called 'ETL Pipeline'",
            "Stop all processors",
            "Show me all connections"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n💭 Test {i}: {query}")
            
            try:
                result = await processor.process_query(query)
                
                print(f"   🎯 Intent: {result.intent.value}")
                print(f"   📊 Confidence: {result.confidence:.2%}")
                print(f"   📝 Explanation: {result.explanation}")
                
                # Show extracted parameters
                params = result.parameters
                if params.processor_type:
                    print(f"   ⚙️ Processor Type: {params.processor_type}")
                if params.process_group_name:
                    print(f"   📁 Process Group: {params.process_group_name}")
                if params.search_query:
                    print(f"   🔍 Search Query: {params.search_query}")
                if params.processor_name:
                    print(f"   🏷️ Processor Name: {params.processor_name}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Intent Processor Setup Error: {e}")
        print("   This is likely due to missing LLM API keys, which is expected for testing.")
        print("   The system will fall back to pattern matching.")


async def test_pattern_matching():
    """Test pattern matching functionality."""
    print("\n🔍 Testing Pattern Matching...")
    print("=" * 50)
    
    from src.llm.intent_processor import IntentProcessor
    
    # Create processor without LLM
    processor = IntentProcessor(llm_provider=None)
    
    test_queries = [
        "list all process groups",
        "create processor getfile", 
        "start the flow",
        "search for kafka",
        "what is the status",
        "help me",
        "show connections",
        "make a new process group called test"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Pattern Test {i}: {query}")
        
        result = await processor.process_query(query)
        
        print(f"   🎯 Intent: {result.intent.value}")
        print(f"   📊 Confidence: {result.confidence:.2%}")
        print(f"   📝 Method: Pattern Matching")


def test_supported_intents():
    """Show all supported intents and examples."""
    print("\n📋 Supported Intents and Examples")
    print("=" * 50)
    
    from src.llm.intent_processor import IntentProcessor
    
    processor = IntentProcessor(llm_provider=None)
    
    intents = processor.get_supported_intents()
    examples = processor.get_intent_examples()
    
    print(f"Total supported intents: {len(intents)}")
    
    for intent in intents[:10]:  # Show first 10
        print(f"\n🎯 {intent}")
        if intent in examples:
            for example in examples[intent][:2]:  # Show first 2 examples
                print(f"   💬 \"{example}\"")


async def main():
    """Main test function."""
    print("🧪 NiFi MCP Server - Simple Test Suite")
    print("=" * 60)
    
    # Test intent processing
    await test_intent_processor()
    
    # Test pattern matching
    await test_pattern_matching()
    
    # Show supported intents
    test_supported_intents()
    
    print("\n🎉 Simple tests completed!")
    print("\n📝 Next Steps:")
    print("   1. Set up LLM API keys (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
    print("   2. Start NiFi instance: ./scripts/nifi_control.sh start")
    print("   3. Run full MCP server: uv run python src/main.py server")
    print("   4. Start chat UI: uv run python src/main.py ui")


if __name__ == "__main__":
    asyncio.run(main())
