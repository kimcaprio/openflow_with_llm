"""
NiFi MCP Server

This module implements a Model Context Protocol (MCP) server for Apache NiFi operations.
It processes natural language queries and executes corresponding NiFi API operations.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from ..nifi.api_client import NiFiAPIClient, NiFiConnectionConfig, NiFiAPIError
from ..llm.intent_processor import IntentProcessor, NiFiIntent, ProcessedIntent, create_intent_processor
from ..utils.config import get_config

logger = logging.getLogger(__name__)


class MCPRequest(BaseModel):
    """MCP request model."""
    query: str = Field(description="Natural language query")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    session_id: Optional[str] = Field(default=None, description="Session identifier")


class MCPResponse(BaseModel):
    """MCP response model."""
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable response message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    intent: Optional[str] = Field(default=None, description="Detected intent")
    confidence: Optional[float] = Field(default=None, description="Confidence score")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    session_id: Optional[str] = Field(default=None, description="Session identifier")


class NiFiMCPServer:
    """
    NiFi MCP Server implementation.
    
    Processes natural language queries and executes NiFi operations.
    """
    
    def __init__(
        self,
        nifi_config: Optional[NiFiConnectionConfig] = None,
        llm_provider_type: str = "openai",
        **llm_kwargs
    ):
        """
        Initialize the NiFi MCP Server.
        
        Args:
            nifi_config: NiFi connection configuration
            llm_provider_type: Type of LLM provider to use
            **llm_kwargs: Additional arguments for LLM provider
        """
        # Load configuration
        config = get_config()
        
        # Initialize NiFi client
        if nifi_config is None:
            nifi_config = NiFiConnectionConfig(
                base_url=config.get("nifi", {}).get("api", {}).get("base_url", "http://localhost:8080/nifi-api"),
                username=config.get("nifi", {}).get("auth", {}).get("username"),
                password=config.get("nifi", {}).get("auth", {}).get("password"),
                verify_ssl=config.get("nifi", {}).get("api", {}).get("verify_ssl", False),
                timeout=config.get("nifi", {}).get("api", {}).get("timeout", 30)
            )
        
        self.nifi_config = nifi_config
        self.nifi_client = None
        
        # Initialize intent processor
        self.intent_processor = create_intent_processor(llm_provider_type, **llm_kwargs)
        
        # Session storage
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"NiFi MCP Server initialized with {llm_provider_type} provider")
    
    async def initialize(self):
        """Initialize the server components."""
        try:
            self.nifi_client = NiFiAPIClient(self.nifi_config)
            await self.nifi_client.__aenter__()
            
            # Test NiFi connection
            if await self.nifi_client.health_check():
                logger.info("Successfully connected to NiFi")
            else:
                logger.warning("NiFi health check failed")
                
        except Exception as e:
            logger.error(f"Failed to initialize NiFi client: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the server components."""
        if self.nifi_client:
            await self.nifi_client.__aexit__(None, None, None)
    
    async def process_query(self, request: MCPRequest) -> MCPResponse:
        """
        Process a natural language query.
        
        Args:
            request: MCP request containing the query
            
        Returns:
            MCP response with results
        """
        try:
            # Process intent
            processed_intent = await self.intent_processor.process_query(request.query)
            
            # Execute NiFi operation
            result = await self._execute_nifi_operation(processed_intent, request.context)
            
            # Build response
            response = MCPResponse(
                success=True,
                message=result.get("message", "Operation completed successfully"),
                data=result.get("data"),
                intent=processed_intent.intent.value,
                confidence=processed_intent.confidence,
                session_id=request.session_id
            )
            
            # Update session context
            if request.session_id:
                self._update_session(request.session_id, processed_intent, result)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query '{request.query}': {e}")
            return MCPResponse(
                success=False,
                message=f"Error processing query: {str(e)}",
                session_id=request.session_id
            )
    
    async def _execute_nifi_operation(
        self, 
        intent: ProcessedIntent, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the appropriate NiFi operation based on the detected intent.
        
        Args:
            intent: Processed intent with parameters
            context: Additional context from the request
            
        Returns:
            Operation result
        """
        if not self.nifi_client:
            raise RuntimeError("NiFi client not initialized")
        
        params = intent.parameters
        
        try:
            if intent.intent == NiFiIntent.LIST_PROCESS_GROUPS:
                return await self._list_process_groups(params)
            
            elif intent.intent == NiFiIntent.CREATE_PROCESS_GROUP:
                return await self._create_process_group(params)
            
            elif intent.intent == NiFiIntent.DELETE_PROCESS_GROUP:
                return await self._delete_process_group(params)
            
            elif intent.intent == NiFiIntent.START_PROCESS_GROUP:
                return await self._start_process_group(params)
            
            elif intent.intent == NiFiIntent.STOP_PROCESS_GROUP:
                return await self._stop_process_group(params)
            
            elif intent.intent == NiFiIntent.LIST_PROCESSORS:
                return await self._list_processors(params)
            
            elif intent.intent == NiFiIntent.CREATE_PROCESSOR:
                return await self._create_processor(params)
            
            elif intent.intent == NiFiIntent.START_PROCESSOR:
                return await self._start_processor(params)
            
            elif intent.intent == NiFiIntent.STOP_PROCESSOR:
                return await self._stop_processor(params)
            
            elif intent.intent == NiFiIntent.LIST_CONNECTIONS:
                return await self._list_connections(params)
            
            elif intent.intent == NiFiIntent.CREATE_CONNECTION:
                return await self._create_connection(params)
            
            elif intent.intent == NiFiIntent.LIST_TEMPLATES:
                return await self._list_templates(params)
            
            elif intent.intent == NiFiIntent.CREATE_TEMPLATE:
                return await self._create_template(params)
            
            elif intent.intent == NiFiIntent.INSTANTIATE_TEMPLATE:
                return await self._instantiate_template(params)
            
            elif intent.intent == NiFiIntent.SEARCH_COMPONENTS:
                return await self._search_components(params)
            
            elif intent.intent == NiFiIntent.GET_STATUS:
                return await self._get_status(params)
            
            elif intent.intent == NiFiIntent.GET_FLOW_STATUS:
                return await self._get_flow_status(params)
            
            elif intent.intent == NiFiIntent.GET_DOCUMENTATION:
                return await self._get_documentation(params)
            
            elif intent.intent == NiFiIntent.GET_PROCESSOR_INFO:
                return await self._get_processor_info(params)
            
            elif intent.intent == NiFiIntent.HELP:
                return await self._get_help(params)
            
            else:
                return {
                    "message": f"Intent '{intent.intent.value}' is not yet implemented",
                    "data": {"intent": intent.intent.value, "parameters": params.dict()}
                }
                
        except NiFiAPIError as e:
            raise RuntimeError(f"NiFi API error: {e.message}")
        except Exception as e:
            raise RuntimeError(f"Operation failed: {str(e)}")
    
    # Process Group Operations
    async def _list_process_groups(self, params) -> Dict[str, Any]:
        """List process groups."""
        process_groups = await self.nifi_client.get_process_groups(params.process_group_id)
        
        if not process_groups:
            message = f"No process groups found in '{params.process_group_id}'"
        else:
            message = f"Found {len(process_groups)} process group(s)"
        
        return {
            "message": message,
            "data": {
                "process_groups": [pg.dict() for pg in process_groups],
                "count": len(process_groups)
            }
        }
    
    async def _create_process_group(self, params) -> Dict[str, Any]:
        """Create a process group."""
        if not params.process_group_name:
            raise ValueError("Process group name is required")
        
        pg = await self.nifi_client.create_process_group(
            parent_group_id=params.process_group_id,
            name=params.process_group_name,
            position=params.position
        )
        
        return {
            "message": f"Created process group '{params.process_group_name}'",
            "data": {"process_group": pg.dict()}
        }
    
    async def _delete_process_group(self, params) -> Dict[str, Any]:
        """Delete a process group."""
        # This would need additional logic to find the group by name
        # For now, return a placeholder
        return {
            "message": "Delete process group operation not fully implemented",
            "data": {"parameters": params.dict()}
        }
    
    async def _start_process_group(self, params) -> Dict[str, Any]:
        """Start a process group."""
        await self.nifi_client.start_process_group(params.process_group_id)
        
        return {
            "message": f"Started process group '{params.process_group_id}'",
            "data": {"process_group_id": params.process_group_id}
        }
    
    async def _stop_process_group(self, params) -> Dict[str, Any]:
        """Stop a process group."""
        await self.nifi_client.stop_process_group(params.process_group_id)
        
        return {
            "message": f"Stopped process group '{params.process_group_id}'",
            "data": {"process_group_id": params.process_group_id}
        }
    
    # Processor Operations
    async def _list_processors(self, params) -> Dict[str, Any]:
        """List processors."""
        processors = await self.nifi_client.get_processors(params.process_group_id)
        
        if not processors:
            message = f"No processors found in '{params.process_group_id}'"
        else:
            message = f"Found {len(processors)} processor(s)"
        
        return {
            "message": message,
            "data": {
                "processors": [proc.dict() for proc in processors],
                "count": len(processors)
            }
        }
    
    async def _create_processor(self, params) -> Dict[str, Any]:
        """Create a processor."""
        if not params.processor_type:
            raise ValueError("Processor type is required")
        
        name = params.processor_name or f"New {params.processor_type.split('.')[-1]}"
        
        processor = await self.nifi_client.create_processor(
            process_group_id=params.process_group_id,
            processor_type=params.processor_type,
            name=name,
            position=params.position,
            properties=params.properties
        )
        
        return {
            "message": f"Created processor '{name}' of type '{params.processor_type}'",
            "data": {"processor": processor.dict()}
        }
    
    async def _start_processor(self, params) -> Dict[str, Any]:
        """Start a processor."""
        # This would need additional logic to find processor by name
        return {
            "message": "Start processor operation not fully implemented",
            "data": {"parameters": params.dict()}
        }
    
    async def _stop_processor(self, params) -> Dict[str, Any]:
        """Stop a processor."""
        # This would need additional logic to find processor by name
        return {
            "message": "Stop processor operation not fully implemented",
            "data": {"parameters": params.dict()}
        }
    
    # Connection Operations
    async def _list_connections(self, params) -> Dict[str, Any]:
        """List connections."""
        connections = await self.nifi_client.get_connections(params.process_group_id)
        
        if not connections:
            message = f"No connections found in '{params.process_group_id}'"
        else:
            message = f"Found {len(connections)} connection(s)"
        
        return {
            "message": message,
            "data": {
                "connections": [conn.dict() for conn in connections],
                "count": len(connections)
            }
        }
    
    async def _create_connection(self, params) -> Dict[str, Any]:
        """Create a connection."""
        if not params.source_id or not params.destination_id:
            raise ValueError("Source and destination IDs are required")
        
        connection = await self.nifi_client.create_connection(
            process_group_id=params.process_group_id,
            source_id=params.source_id,
            destination_id=params.destination_id,
            relationships=params.relationships or ["success"],
            name=params.connection_name
        )
        
        return {
            "message": f"Created connection from '{params.source_id}' to '{params.destination_id}'",
            "data": {"connection": connection.dict()}
        }
    
    # Template Operations
    async def _list_templates(self, params) -> Dict[str, Any]:
        """List templates."""
        templates = await self.nifi_client.get_templates()
        
        if not templates:
            message = "No templates found"
        else:
            message = f"Found {len(templates)} template(s)"
        
        return {
            "message": message,
            "data": {
                "templates": [template.dict() for template in templates],
                "count": len(templates)
            }
        }
    
    async def _create_template(self, params) -> Dict[str, Any]:
        """Create a template."""
        if not params.template_name:
            raise ValueError("Template name is required")
        
        template = await self.nifi_client.create_template(
            process_group_id=params.process_group_id,
            name=params.template_name,
            description=params.additional_params.get("description", "")
        )
        
        return {
            "message": f"Created template '{params.template_name}'",
            "data": {"template": template.dict()}
        }
    
    async def _instantiate_template(self, params) -> Dict[str, Any]:
        """Instantiate a template."""
        # This would need additional logic to find template by name
        return {
            "message": "Instantiate template operation not fully implemented",
            "data": {"parameters": params.dict()}
        }
    
    # Search Operations
    async def _search_components(self, params) -> Dict[str, Any]:
        """Search components."""
        if not params.search_query:
            raise ValueError("Search query is required")
        
        results = await self.nifi_client.search_components(params.search_query)
        
        total_results = sum(len(components) for components in results.values())
        
        return {
            "message": f"Found {total_results} component(s) matching '{params.search_query}'",
            "data": {
                "search_results": results,
                "total_count": total_results
            }
        }
    
    # Status Operations
    async def _get_status(self, params) -> Dict[str, Any]:
        """Get system status."""
        diagnostics = await self.nifi_client.get_system_diagnostics()
        controller_status = await self.nifi_client.get_controller_status()
        
        return {
            "message": "Retrieved NiFi system status",
            "data": {
                "system_diagnostics": diagnostics,
                "controller_status": controller_status
            }
        }
    
    async def _get_flow_status(self, params) -> Dict[str, Any]:
        """Get flow status."""
        status = await self.nifi_client.get_controller_status()
        
        return {
            "message": "Retrieved flow status",
            "data": {"flow_status": status}
        }
    
    # Documentation Operations
    async def _get_documentation(self, params) -> Dict[str, Any]:
        """Get documentation."""
        if params.processor_type:
            docs = await self.nifi_client.get_processor_documentation(params.processor_type)
            return {
                "message": f"Retrieved documentation for {params.processor_type}",
                "data": {"documentation": docs}
            }
        else:
            # Return general help
            return await self._get_help(params)
    
    async def _get_processor_info(self, params) -> Dict[str, Any]:
        """Get processor information."""
        if params.processor_type:
            docs = await self.nifi_client.get_processor_documentation(params.processor_type)
            return {
                "message": f"Retrieved information for {params.processor_type}",
                "data": {"processor_info": docs}
            }
        else:
            # List available processor types
            processor_types = await self.nifi_client.get_processor_types()
            return {
                "message": f"Found {len(processor_types)} processor types",
                "data": {"processor_types": processor_types}
            }
    
    async def _get_help(self, params) -> Dict[str, Any]:
        """Get help information."""
        examples = self.intent_processor.get_intent_examples()
        
        return {
            "message": "Here are some example queries you can use:",
            "data": {
                "examples": examples,
                "supported_intents": self.intent_processor.get_supported_intents()
            }
        }
    
    def _update_session(self, session_id: str, intent: ProcessedIntent, result: Dict[str, Any]):
        """Update session context."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": datetime.now(),
                "queries": [],
                "context": {}
            }
        
        self.sessions[session_id]["queries"].append({
            "timestamp": datetime.now(),
            "query": intent.raw_query,
            "intent": intent.intent.value,
            "confidence": intent.confidence,
            "result": result
        })
        
        # Keep only last 10 queries per session
        if len(self.sessions[session_id]["queries"]) > 10:
            self.sessions[session_id]["queries"] = self.sessions[session_id]["queries"][-10:]


# FastAPI application
def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="NiFi MCP Server",
        description="Natural language interface for Apache NiFi operations",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize server
    mcp_server = None
    
    @app.on_event("startup")
    async def startup_event():
        nonlocal mcp_server
        mcp_server = NiFiMCPServer()
        await mcp_server.initialize()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        if mcp_server:
            await mcp_server.shutdown()
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "NiFi MCP Server is running"}
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        if mcp_server and mcp_server.nifi_client:
            nifi_healthy = await mcp_server.nifi_client.health_check()
            return {
                "status": "healthy" if nifi_healthy else "degraded",
                "nifi_connection": nifi_healthy,
                "timestamp": datetime.now()
            }
        return {"status": "starting", "timestamp": datetime.now()}
    
    @app.post("/query", response_model=MCPResponse)
    async def process_query(request: MCPRequest):
        """Process a natural language query."""
        if not mcp_server:
            raise HTTPException(status_code=503, detail="Server not initialized")
        
        return await mcp_server.process_query(request)
    
    @app.get("/intents")
    async def get_supported_intents():
        """Get supported intents and examples."""
        if not mcp_server:
            raise HTTPException(status_code=503, detail="Server not initialized")
        
        return {
            "intents": mcp_server.intent_processor.get_supported_intents(),
            "examples": mcp_server.intent_processor.get_intent_examples()
        }
    
    return app


# Main function for running the server
def main(host: str = "0.0.0.0", port: int = 8000, **kwargs):
    """Run the NiFi MCP Server."""
    app = create_app()
    uvicorn.run(app, host=host, port=port, **kwargs)


if __name__ == "__main__":
    main()
