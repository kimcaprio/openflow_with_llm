"""
Streamlit Chat Interface for NiFi MCP Server

This module provides a web-based chat interface for interacting with Apache NiFi
through natural language queries.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import streamlit as st
import httpx
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NiFiChatInterface:
    """Streamlit-based chat interface for NiFi MCP Server."""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        """
        Initialize the chat interface.
        
        Args:
            mcp_server_url: URL of the NiFi MCP Server
        """
        self.mcp_server_url = mcp_server_url
        self.session_id = self._get_session_id()
        
    def _get_session_id(self) -> str:
        """Get or create session ID."""
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        return st.session_state.session_id
    
    async def send_query(self, query: str) -> Dict[str, Any]:
        """
        Send query to MCP server.
        
        Args:
            query: Natural language query
            
        Returns:
            Response from MCP server
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_server_url}/query",
                    json={
                        "query": query,
                        "session_id": self.session_id,
                        "context": {}
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "message": f"Server error: {response.status_code}",
                        "data": None
                    }
                    
        except Exception as e:
            logger.error(f"Error sending query: {e}")
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "data": None
            }
    
    async def get_server_health(self) -> Dict[str, Any]:
        """Check server health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.mcp_server_url}/health",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def get_supported_intents(self) -> Dict[str, Any]:
        """Get supported intents and examples."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.mcp_server_url}/intents",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"intents": [], "examples": {}}
                    
        except Exception as e:
            logger.error(f"Error getting intents: {e}")
            return {"intents": [], "examples": {}}
    
    def render_sidebar(self):
        """Render the sidebar with server status and examples."""
        st.sidebar.title("🔧 NiFi MCP Server")
        
        # Server health check
        if st.sidebar.button("Check Server Health"):
            with st.sidebar:
                with st.spinner("Checking server health..."):
                    health = asyncio.run(self.get_server_health())
                    
                    if health.get("status") == "healthy":
                        st.success("✅ Server is healthy")
                        st.json(health)
                    elif health.get("status") == "degraded":
                        st.warning("⚠️ Server is degraded")
                        st.json(health)
                    else:
                        st.error("❌ Server is not responding")
                        st.json(health)
        
        st.sidebar.markdown("---")
        
        # Example queries
        st.sidebar.subheader("📝 Example Queries")
        
        examples = [
            "List all process groups",
            "Show me the processors in the root group",
            "Create a process group called 'Data Processing'",
            "Search for GetFile processors",
            "What's the status of my NiFi flow?",
            "Start all processors in the main group",
            "Create a GetFile processor",
            "Show me all connections",
            "List available templates",
            "Help me understand NiFi processors"
        ]
        
        for example in examples:
            if st.sidebar.button(f"💬 {example}", key=f"example_{hash(example)}"):
                st.session_state.current_query = example
                st.rerun()
        
        st.sidebar.markdown("---")
        
        # Session info
        st.sidebar.subheader("🔍 Session Info")
        st.sidebar.text(f"Session ID: {self.session_id[:8]}...")
        
        if st.sidebar.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    
    def render_chat_interface(self):
        """Render the main chat interface."""
        st.title("💬 NiFi Natural Language Interface")
        st.markdown("Ask me anything about your Apache NiFi instance!")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    self._render_assistant_message(message)
                else:
                    st.markdown(message["content"])
        
        # Chat input
        query = st.chat_input("Ask about your NiFi instance...")
        
        # Handle example query from sidebar
        if hasattr(st.session_state, 'current_query'):
            query = st.session_state.current_query
            delattr(st.session_state, 'current_query')
        
        if query:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": query})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(query)
            
            # Get response from MCP server
            with st.chat_message("assistant"):
                with st.spinner("Processing your request..."):
                    response = asyncio.run(self.send_query(query))
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.get("message", "No response"),
                        "data": response.get("data"),
                        "success": response.get("success", False),
                        "intent": response.get("intent"),
                        "confidence": response.get("confidence"),
                        "timestamp": response.get("timestamp")
                    })
                    
                    # Render the response
                    self._render_assistant_message(st.session_state.messages[-1])
    
    def _render_assistant_message(self, message: Dict[str, Any]):
        """Render an assistant message with data visualization."""
        # Main response message
        if message.get("success"):
            st.success(message["content"])
        else:
            st.error(message["content"])
        
        # Show intent and confidence if available
        if message.get("intent") and message.get("confidence"):
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"🎯 Intent: `{message['intent']}`")
            with col2:
                confidence = message['confidence']
                confidence_color = "green" if confidence > 0.8 else "orange" if confidence > 0.5 else "red"
                st.caption(f"📊 Confidence: :{confidence_color}[{confidence:.2%}]")
        
        # Render data if available
        data = message.get("data")
        if data:
            self._render_data(data)
    
    def _render_data(self, data: Dict[str, Any]):
        """Render data in appropriate format."""
        if not data:
            return
        
        # Handle different data types
        if "process_groups" in data:
            self._render_process_groups(data["process_groups"])
        
        elif "processors" in data:
            self._render_processors(data["processors"])
        
        elif "connections" in data:
            self._render_connections(data["connections"])
        
        elif "templates" in data:
            self._render_templates(data["templates"])
        
        elif "search_results" in data:
            self._render_search_results(data["search_results"])
        
        elif "system_diagnostics" in data:
            self._render_system_diagnostics(data["system_diagnostics"])
        
        elif "examples" in data:
            self._render_examples(data["examples"])
        
        else:
            # Generic JSON display
            with st.expander("📋 Raw Data", expanded=False):
                st.json(data)
    
    def _render_process_groups(self, process_groups: List[Dict]):
        """Render process groups data."""
        if not process_groups:
            st.info("No process groups found.")
            return
        
        st.subheader("📁 Process Groups")
        
        # Create DataFrame for better display
        df_data = []
        for pg in process_groups:
            df_data.append({
                "Name": pg.get("name", "N/A"),
                "ID": pg.get("id", "N/A")[:8] + "...",
                "Running": pg.get("running_count", 0),
                "Stopped": pg.get("stopped_count", 0),
                "FlowFiles": pg.get("flow_file_count", 0),
                "Comments": pg.get("comments", "")[:50] + "..." if pg.get("comments", "") else ""
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
    
    def _render_processors(self, processors: List[Dict]):
        """Render processors data."""
        if not processors:
            st.info("No processors found.")
            return
        
        st.subheader("⚙️ Processors")
        
        # Create DataFrame
        df_data = []
        for proc in processors:
            df_data.append({
                "Name": proc.get("name", "N/A"),
                "Type": proc.get("processor_type", "N/A").split(".")[-1] if proc.get("processor_type") else "N/A",
                "Status": proc.get("run_status", "N/A"),
                "State": proc.get("state", "N/A"),
                "ID": proc.get("id", "N/A")[:8] + "..."
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
    
    def _render_connections(self, connections: List[Dict]):
        """Render connections data."""
        if not connections:
            st.info("No connections found.")
            return
        
        st.subheader("🔗 Connections")
        
        # Create DataFrame
        df_data = []
        for conn in connections:
            df_data.append({
                "Name": conn.get("name", "N/A"),
                "Source": conn.get("source_name", "N/A"),
                "Destination": conn.get("destination_name", "N/A"),
                "FlowFiles": conn.get("flow_file_count", 0),
                "Size": conn.get("flow_file_size", 0)
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
    
    def _render_templates(self, templates: List[Dict]):
        """Render templates data."""
        if not templates:
            st.info("No templates found.")
            return
        
        st.subheader("📋 Templates")
        
        for template in templates:
            with st.expander(f"📄 {template.get('name', 'Unnamed Template')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.text(f"ID: {template.get('id', 'N/A')}")
                    st.text(f"Timestamp: {template.get('timestamp', 'N/A')}")
                with col2:
                    st.text(f"Encoding: {template.get('encoding_version', 'N/A')}")
                
                if template.get('description'):
                    st.markdown(f"**Description:** {template['description']}")
    
    def _render_search_results(self, search_results: Dict[str, List]):
        """Render search results."""
        st.subheader("🔍 Search Results")
        
        total_results = sum(len(results) for results in search_results.values())
        if total_results == 0:
            st.info("No search results found.")
            return
        
        for component_type, results in search_results.items():
            if results:
                st.write(f"**{component_type.replace('_', ' ').title()}** ({len(results)} found)")
                
                for result in results[:5]:  # Show first 5 results
                    with st.expander(f"🔍 {result.get('name', 'Unnamed')}"):
                        st.json(result)
                
                if len(results) > 5:
                    st.caption(f"... and {len(results) - 5} more")
    
    def _render_system_diagnostics(self, diagnostics: Dict):
        """Render system diagnostics."""
        st.subheader("🏥 System Diagnostics")
        
        if "systemDiagnostics" in diagnostics:
            sys_diag = diagnostics["systemDiagnostics"]
            
            # Memory information
            if "aggregateSnapshot" in sys_diag:
                snapshot = sys_diag["aggregateSnapshot"]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Threads", snapshot.get("totalThreadCount", "N/A"))
                
                with col2:
                    st.metric("Active Threads", snapshot.get("activeThreadCount", "N/A"))
                
                with col3:
                    heap_util = snapshot.get("heapUtilization", {})
                    if heap_util:
                        st.metric("Heap Usage", heap_util.get("utilization", "N/A"))
        
        # Raw diagnostics data
        with st.expander("📊 Raw Diagnostics Data", expanded=False):
            st.json(diagnostics)
    
    def _render_examples(self, examples: Dict[str, List[str]]):
        """Render intent examples."""
        st.subheader("💡 Example Queries by Intent")
        
        for intent, example_list in examples.items():
            with st.expander(f"🎯 {intent.replace('_', ' ').title()}"):
                for example in example_list:
                    if st.button(f"Try: {example}", key=f"try_{hash(example)}"):
                        st.session_state.current_query = example
                        st.rerun()
    
    def run(self):
        """Run the Streamlit application."""
        st.set_page_config(
            page_title="NiFi Chat Interface",
            page_icon="💬",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS
        st.markdown("""
        <style>
        .stApp > header {
            background-color: transparent;
        }
        
        .stApp {
            margin-top: -80px;
        }
        
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
        }
        
        .user-message {
            background-color: #e3f2fd;
            align-self: flex-end;
        }
        
        .assistant-message {
            background-color: #f5f5f5;
            align-self: flex-start;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Render sidebar
        self.render_sidebar()
        
        # Render main chat interface
        self.render_chat_interface()


def main():
    """Main function to run the Streamlit app."""
    # Get MCP server URL from environment or use default
    import os
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    
    # Create and run the chat interface
    chat_interface = NiFiChatInterface(mcp_server_url)
    chat_interface.run()


if __name__ == "__main__":
    main()
