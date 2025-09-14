"""
NiFi REST API Client

This module provides a comprehensive client for interacting with Apache NiFi's REST API.
It supports all major NiFi operations including process groups, processors, connections, and templates.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NiFiConnectionConfig(BaseModel):
    """Configuration for NiFi connection."""
    base_url: str = Field(default="https://localhost:8443/nifi-api", description="NiFi API base URL")
    username: Optional[str] = Field(default=None, description="Username for authentication")
    password: Optional[str] = Field(default=None, description="Password for authentication")
    verify_ssl: bool = Field(default=False, description="Whether to verify SSL certificates")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")


class NiFiComponent(BaseModel):
    """Base model for NiFi components."""
    id: str
    name: str
    type: Optional[str] = None
    state: Optional[str] = None
    comments: Optional[str] = None


class ProcessGroup(NiFiComponent):
    """NiFi Process Group model."""
    flow_file_count: Optional[int] = None
    flow_file_size: Optional[int] = None
    running_count: Optional[int] = None
    stopped_count: Optional[int] = None
    invalid_count: Optional[int] = None
    disabled_count: Optional[int] = None


class Processor(NiFiComponent):
    """NiFi Processor model."""
    processor_type: Optional[str] = None
    run_status: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
    relationships: Optional[List[str]] = None


class Connection(NiFiComponent):
    """NiFi Connection model."""
    source_id: Optional[str] = None
    source_name: Optional[str] = None
    destination_id: Optional[str] = None
    destination_name: Optional[str] = None
    flow_file_count: Optional[int] = None
    flow_file_size: Optional[int] = None


class Template(NiFiComponent):
    """NiFi Template model."""
    description: Optional[str] = None
    timestamp: Optional[str] = None
    encoding_version: Optional[str] = None


class NiFiAPIError(Exception):
    """Custom exception for NiFi API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class NiFiAPIClient:
    """
    Comprehensive NiFi REST API Client.
    
    Provides methods for interacting with all major NiFi components and operations.
    """
    
    def __init__(self, config: NiFiConnectionConfig):
        """
        Initialize the NiFi API client.
        
        Args:
            config: NiFi connection configuration
        """
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            verify=config.verify_ssl,
            timeout=config.timeout
        )
        self._auth_token = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.authenticate()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    async def authenticate(self) -> bool:
        """
        Authenticate with NiFi if credentials are provided.
        
        Returns:
            True if authentication successful or not required, False otherwise
        """
        if not self.config.username or not self.config.password:
            logger.info("No credentials provided, assuming no authentication required")
            return True
            
        try:
            auth_data = {
                "username": self.config.username,
                "password": self.config.password
            }
            
            response = await self.client.post("/access/token", data=auth_data)
            if response.status_code == 201:
                self._auth_token = response.text
                self.client.headers.update({"Authorization": f"Bearer {self._auth_token}"})
                logger.info("Successfully authenticated with NiFi")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the NiFi API with error handling and retries.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON data for request body
            data: Form data for request body
            
        Returns:
            Response data as dictionary
            
        Raises:
            NiFiAPIError: If the request fails
        """
        url = endpoint if endpoint.startswith('http') else f"/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    data=data
                )
                
                if response.status_code >= 400:
                    error_msg = f"API request failed: {method} {url} - {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data}"
                    except:
                        error_msg += f" - {response.text}"
                    
                    raise NiFiAPIError(error_msg, response.status_code, response.json() if response.content else None)
                
                return response.json() if response.content else {}
                
            except httpx.RequestError as e:
                if attempt == self.config.max_retries - 1:
                    raise NiFiAPIError(f"Request failed after {self.config.max_retries} attempts: {e}")
                logger.warning(f"Request attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    # System and Health Operations
    async def get_system_diagnostics(self) -> Dict[str, Any]:
        """Get NiFi system diagnostics information."""
        return await self._make_request("GET", "/system-diagnostics")
    
    async def get_cluster_summary(self) -> Dict[str, Any]:
        """Get NiFi cluster summary information."""
        return await self._make_request("GET", "/controller/cluster")
    
    async def get_controller_status(self) -> Dict[str, Any]:
        """Get NiFi controller status."""
        return await self._make_request("GET", "/flow/status")
    
    # Process Group Operations
    async def get_process_groups(self, parent_group_id: str = "root") -> List[ProcessGroup]:
        """
        Get all process groups within a parent group.
        
        Args:
            parent_group_id: Parent process group ID (default: root)
            
        Returns:
            List of ProcessGroup objects
        """
        response = await self._make_request("GET", f"/flow/process-groups/{parent_group_id}")
        
        process_groups = []
        if "processGroupFlow" in response and "flow" in response["processGroupFlow"]:
            flow = response["processGroupFlow"]["flow"]
            if "processGroups" in flow:
                for pg_data in flow["processGroups"]:
                    pg_component = pg_data.get("component", {})
                    pg_status = pg_data.get("status", {})
                    
                    process_groups.append(ProcessGroup(
                        id=pg_component.get("id", ""),
                        name=pg_component.get("name", ""),
                        comments=pg_component.get("comments"),
                        flow_file_count=pg_status.get("aggregateSnapshot", {}).get("flowFilesQueued", 0),
                        flow_file_size=pg_status.get("aggregateSnapshot", {}).get("bytesQueued", 0),
                        running_count=pg_status.get("aggregateSnapshot", {}).get("runningCount", 0),
                        stopped_count=pg_status.get("aggregateSnapshot", {}).get("stoppedCount", 0),
                        invalid_count=pg_status.get("aggregateSnapshot", {}).get("invalidCount", 0),
                        disabled_count=pg_status.get("aggregateSnapshot", {}).get("disabledCount", 0)
                    ))
        
        return process_groups
    
    async def create_process_group(self, parent_group_id: str, name: str, position: Optional[Dict] = None) -> ProcessGroup:
        """
        Create a new process group.
        
        Args:
            parent_group_id: Parent process group ID
            name: Name for the new process group
            position: Position coordinates (x, y)
            
        Returns:
            Created ProcessGroup object
        """
        if position is None:
            position = {"x": 0, "y": 0}
            
        payload = {
            "revision": {"version": 0},
            "component": {
                "name": name,
                "position": position
            }
        }
        
        response = await self._make_request("POST", f"/process-groups/{parent_group_id}/process-groups", json_data=payload)
        
        component = response.get("component", {})
        return ProcessGroup(
            id=component.get("id", ""),
            name=component.get("name", ""),
            comments=component.get("comments")
        )
    
    async def delete_process_group(self, group_id: str, version: int = 0) -> bool:
        """
        Delete a process group.
        
        Args:
            group_id: Process group ID to delete
            version: Revision version
            
        Returns:
            True if successful
        """
        params = {"version": version}
        await self._make_request("DELETE", f"/process-groups/{group_id}", params=params)
        return True
    
    # Processor Operations
    async def get_processors(self, process_group_id: str = "root") -> List[Processor]:
        """
        Get all processors within a process group.
        
        Args:
            process_group_id: Process group ID (default: root)
            
        Returns:
            List of Processor objects
        """
        response = await self._make_request("GET", f"/flow/process-groups/{process_group_id}")
        
        processors = []
        if "processGroupFlow" in response and "flow" in response["processGroupFlow"]:
            flow = response["processGroupFlow"]["flow"]
            if "processors" in flow:
                for proc_data in flow["processors"]:
                    proc_component = proc_data.get("component", {})
                    proc_status = proc_data.get("status", {})
                    
                    processors.append(Processor(
                        id=proc_component.get("id", ""),
                        name=proc_component.get("name", ""),
                        type=proc_component.get("type"),
                        processor_type=proc_component.get("type"),
                        state=proc_component.get("state"),
                        run_status=proc_status.get("runStatus"),
                        comments=proc_component.get("comments"),
                        validation_errors=proc_component.get("validationErrors", []),
                        properties=proc_component.get("config", {}).get("properties", {}),
                        relationships=list(proc_component.get("relationships", {}).keys())
                    ))
        
        return processors
    
    async def create_processor(
        self, 
        process_group_id: str, 
        processor_type: str, 
        name: str,
        position: Optional[Dict] = None,
        properties: Optional[Dict] = None
    ) -> Processor:
        """
        Create a new processor.
        
        Args:
            process_group_id: Parent process group ID
            processor_type: Type of processor (e.g., 'org.apache.nifi.processors.standard.GetFile')
            name: Name for the processor
            position: Position coordinates (x, y)
            properties: Processor properties
            
        Returns:
            Created Processor object
        """
        if position is None:
            position = {"x": 0, "y": 0}
        if properties is None:
            properties = {}
            
        payload = {
            "revision": {"version": 0},
            "component": {
                "type": processor_type,
                "name": name,
                "position": position,
                "config": {
                    "properties": properties
                }
            }
        }
        
        response = await self._make_request("POST", f"/process-groups/{process_group_id}/processors", json_data=payload)
        
        component = response.get("component", {})
        return Processor(
            id=component.get("id", ""),
            name=component.get("name", ""),
            type=component.get("type"),
            processor_type=component.get("type"),
            state=component.get("state"),
            comments=component.get("comments"),
            properties=component.get("config", {}).get("properties", {})
        )
    
    async def start_processor(self, processor_id: str, version: int = 0) -> bool:
        """Start a processor."""
        return await self._update_processor_state(processor_id, "RUNNING", version)
    
    async def stop_processor(self, processor_id: str, version: int = 0) -> bool:
        """Stop a processor."""
        return await self._update_processor_state(processor_id, "STOPPED", version)
    
    async def _update_processor_state(self, processor_id: str, state: str, version: int) -> bool:
        """Update processor run state."""
        payload = {
            "revision": {"version": version},
            "component": {
                "id": processor_id,
                "state": state
            }
        }
        
        await self._make_request("PUT", f"/processors/{processor_id}", json_data=payload)
        return True
    
    # Connection Operations
    async def get_connections(self, process_group_id: str = "root") -> List[Connection]:
        """
        Get all connections within a process group.
        
        Args:
            process_group_id: Process group ID (default: root)
            
        Returns:
            List of Connection objects
        """
        response = await self._make_request("GET", f"/flow/process-groups/{process_group_id}")
        
        connections = []
        if "processGroupFlow" in response and "flow" in response["processGroupFlow"]:
            flow = response["processGroupFlow"]["flow"]
            if "connections" in flow:
                for conn_data in flow["connections"]:
                    conn_component = conn_data.get("component", {})
                    conn_status = conn_data.get("status", {})
                    
                    connections.append(Connection(
                        id=conn_component.get("id", ""),
                        name=conn_component.get("name", ""),
                        source_id=conn_component.get("source", {}).get("id"),
                        source_name=conn_component.get("source", {}).get("name"),
                        destination_id=conn_component.get("destination", {}).get("id"),
                        destination_name=conn_component.get("destination", {}).get("name"),
                        flow_file_count=conn_status.get("aggregateSnapshot", {}).get("flowFilesQueued", 0),
                        flow_file_size=conn_status.get("aggregateSnapshot", {}).get("bytesQueued", 0)
                    ))
        
        return connections
    
    async def create_connection(
        self,
        process_group_id: str,
        source_id: str,
        destination_id: str,
        relationships: List[str],
        name: Optional[str] = None
    ) -> Connection:
        """
        Create a connection between two components.
        
        Args:
            process_group_id: Parent process group ID
            source_id: Source component ID
            destination_id: Destination component ID
            relationships: List of relationships to connect
            name: Optional connection name
            
        Returns:
            Created Connection object
        """
        payload = {
            "revision": {"version": 0},
            "component": {
                "name": name or f"Connection_{source_id}_to_{destination_id}",
                "source": {"id": source_id, "groupId": process_group_id},
                "destination": {"id": destination_id, "groupId": process_group_id},
                "selectedRelationships": relationships
            }
        }
        
        response = await self._make_request("POST", f"/process-groups/{process_group_id}/connections", json_data=payload)
        
        component = response.get("component", {})
        return Connection(
            id=component.get("id", ""),
            name=component.get("name", ""),
            source_id=component.get("source", {}).get("id"),
            destination_id=component.get("destination", {}).get("id")
        )
    
    # Template Operations
    async def get_templates(self) -> List[Template]:
        """
        Get all available templates.
        
        Returns:
            List of Template objects
        """
        response = await self._make_request("GET", "/flow/templates")
        
        templates = []
        if "templates" in response:
            for template_data in response["templates"]:
                template_info = template_data.get("template", {})
                
                templates.append(Template(
                    id=template_info.get("id", ""),
                    name=template_info.get("name", ""),
                    description=template_info.get("description"),
                    timestamp=template_info.get("timestamp"),
                    encoding_version=template_info.get("encodingVersion")
                ))
        
        return templates
    
    async def create_template(self, process_group_id: str, name: str, description: str = "") -> Template:
        """
        Create a template from a process group.
        
        Args:
            process_group_id: Process group ID to create template from
            name: Template name
            description: Template description
            
        Returns:
            Created Template object
        """
        payload = {
            "name": name,
            "description": description,
            "snippetId": process_group_id
        }
        
        response = await self._make_request("POST", "/process-groups/root/templates", json_data=payload)
        
        template_info = response.get("template", {})
        return Template(
            id=template_info.get("id", ""),
            name=template_info.get("name", ""),
            description=template_info.get("description"),
            timestamp=template_info.get("timestamp")
        )
    
    async def instantiate_template(self, process_group_id: str, template_id: str, origin_x: int = 0, origin_y: int = 0) -> Dict[str, Any]:
        """
        Instantiate a template in a process group.
        
        Args:
            process_group_id: Target process group ID
            template_id: Template ID to instantiate
            origin_x: X coordinate for template placement
            origin_y: Y coordinate for template placement
            
        Returns:
            Instantiation result
        """
        payload = {
            "templateId": template_id,
            "originX": origin_x,
            "originY": origin_y
        }
        
        return await self._make_request("POST", f"/process-groups/{process_group_id}/template-instance", json_data=payload)
    
    # Search Operations
    async def search_components(self, query: str) -> Dict[str, List[Dict]]:
        """
        Search for components across the NiFi instance.
        
        Args:
            query: Search query string
            
        Returns:
            Dictionary containing search results by component type
        """
        params = {"q": query}
        response = await self._make_request("GET", "/flow/search-results", params=params)
        
        return {
            "processors": response.get("processorResults", []),
            "process_groups": response.get("processGroupResults", []),
            "connections": response.get("connectionResults", []),
            "input_ports": response.get("inputPortResults", []),
            "output_ports": response.get("outputPortResults", []),
            "remote_process_groups": response.get("remoteProcessGroupResults", []),
            "funnels": response.get("funnelResults", [])
        }
    
    # Flow Control Operations
    async def start_process_group(self, process_group_id: str, version: int = 0) -> bool:
        """Start all processors in a process group."""
        return await self._update_process_group_state(process_group_id, "RUNNING", version)
    
    async def stop_process_group(self, process_group_id: str, version: int = 0) -> bool:
        """Stop all processors in a process group."""
        return await self._update_process_group_state(process_group_id, "STOPPED", version)
    
    async def _update_process_group_state(self, process_group_id: str, state: str, version: int) -> bool:
        """Update process group state."""
        payload = {
            "id": process_group_id,
            "state": state
        }
        
        await self._make_request("PUT", f"/flow/process-groups/{process_group_id}", json_data=payload)
        return True
    
    # Utility Methods
    async def get_processor_types(self) -> List[Dict[str, Any]]:
        """Get all available processor types."""
        response = await self._make_request("GET", "/flow/processor-types")
        return response.get("processorTypes", [])
    
    async def get_processor_documentation(self, processor_type: str) -> Dict[str, Any]:
        """
        Get documentation for a specific processor type.
        
        Args:
            processor_type: Full processor class name
            
        Returns:
            Processor documentation
        """
        # Extract bundle and type from full class name
        parts = processor_type.split('.')
        bundle_group = '.'.join(parts[:-2]) if len(parts) > 2 else 'org.apache.nifi'
        artifact = 'nifi-standard-processors'  # This might need to be dynamic
        version = '1.20.0'  # This should be retrieved dynamically
        type_name = parts[-1]
        
        endpoint = f"/extension-repository/{bundle_group}/{artifact}/{version}/extensions/{type_name}/docs"
        
        try:
            return await self._make_request("GET", endpoint)
        except NiFiAPIError:
            # Fallback to basic processor type info
            processor_types = await self.get_processor_types()
            for pt in processor_types:
                if pt.get("type") == processor_type:
                    return pt
            return {}
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the NiFi instance.
        
        Returns:
            True if NiFi is healthy, False otherwise
        """
        try:
            await self.get_system_diagnostics()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Convenience function for creating a configured client
def create_nifi_client(
    base_url: str = "https://localhost:8443/nifi-api",
    username: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs
) -> NiFiAPIClient:
    """
    Create a configured NiFi API client.
    
    Args:
        base_url: NiFi API base URL
        username: Optional username for authentication
        password: Optional password for authentication
        **kwargs: Additional configuration options
        
    Returns:
        Configured NiFiAPIClient instance
    """
    config = NiFiConnectionConfig(
        base_url=base_url,
        username=username,
        password=password,
        **kwargs
    )
    return NiFiAPIClient(config)
