"""
Natural Language Intent Processing for NiFi Operations

This module processes natural language queries and extracts intent and parameters
for NiFi operations using various LLM providers.
"""

import json
import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import asyncio

from src.llm.providers.openai_provider import OpenAIProvider
from src.llm.providers.anthropic_provider import AnthropicProvider
from src.llm.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class NiFiIntent(str, Enum):
    """Enumeration of supported NiFi intents."""
    # Process Group Operations
    LIST_PROCESS_GROUPS = "list_process_groups"
    CREATE_PROCESS_GROUP = "create_process_group"
    DELETE_PROCESS_GROUP = "delete_process_group"
    START_PROCESS_GROUP = "start_process_group"
    STOP_PROCESS_GROUP = "stop_process_group"
    
    # Processor Operations
    LIST_PROCESSORS = "list_processors"
    CREATE_PROCESSOR = "create_processor"
    DELETE_PROCESSOR = "delete_processor"
    START_PROCESSOR = "start_processor"
    STOP_PROCESSOR = "stop_processor"
    CONFIGURE_PROCESSOR = "configure_processor"
    
    # Connection Operations
    LIST_CONNECTIONS = "list_connections"
    CREATE_CONNECTION = "create_connection"
    DELETE_CONNECTION = "delete_connection"
    
    # Template Operations
    LIST_TEMPLATES = "list_templates"
    CREATE_TEMPLATE = "create_template"
    INSTANTIATE_TEMPLATE = "instantiate_template"
    
    # Search Operations
    SEARCH_COMPONENTS = "search_components"
    
    # Status and Monitoring
    GET_STATUS = "get_status"
    GET_FLOW_STATUS = "get_flow_status"
    MONITOR_FLOW = "monitor_flow"
    
    # Documentation
    GET_DOCUMENTATION = "get_documentation"
    GET_PROCESSOR_INFO = "get_processor_info"
    
    # General
    HELP = "help"
    UNKNOWN = "unknown"


class IntentParameters(BaseModel):
    """Parameters extracted from natural language query."""
    process_group_id: Optional[str] = Field(default="root", description="Target process group ID")
    process_group_name: Optional[str] = Field(default=None, description="Process group name")
    processor_name: Optional[str] = Field(default=None, description="Processor name")
    processor_type: Optional[str] = Field(default=None, description="Processor type")
    processor_id: Optional[str] = Field(default=None, description="Processor ID")
    connection_name: Optional[str] = Field(default=None, description="Connection name")
    template_name: Optional[str] = Field(default=None, description="Template name")
    search_query: Optional[str] = Field(default=None, description="Search query")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Component properties")
    relationships: Optional[List[str]] = Field(default_factory=list, description="Processor relationships")
    source_id: Optional[str] = Field(default=None, description="Source component ID")
    destination_id: Optional[str] = Field(default=None, description="Destination component ID")
    position: Optional[Dict[str, float]] = Field(default=None, description="Component position")
    additional_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")


class ProcessedIntent(BaseModel):
    """Result of intent processing."""
    intent: NiFiIntent
    parameters: IntentParameters
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    raw_query: str = Field(description="Original query")
    explanation: Optional[str] = Field(default=None, description="Explanation of the intent")


class IntentProcessor:
    """
    Processes natural language queries to extract NiFi operation intents.
    """
    
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        """
        Initialize the intent processor.
        
        Args:
            llm_provider: LLM provider instance. If None, will try to create one.
        """
        self.llm_provider = llm_provider or self._create_default_provider()
        self.intent_patterns = self._build_intent_patterns()
        
    def _create_default_provider(self) -> BaseLLMProvider:
        """Create a default LLM provider."""
        try:
            return OpenAIProvider()
        except Exception:
            try:
                return AnthropicProvider()
            except Exception:
                logger.warning("No LLM provider available, using pattern matching only")
                return None
    
    def _build_intent_patterns(self) -> Dict[NiFiIntent, List[str]]:
        """Build regex patterns for intent matching."""
        return {
            # Process Group Operations
            NiFiIntent.LIST_PROCESS_GROUPS: [
                r"list.*process\s*groups?",
                r"show.*process\s*groups?",
                r"get.*process\s*groups?",
                r"what.*process\s*groups?",
            ],
            NiFiIntent.CREATE_PROCESS_GROUP: [
                r"create.*process\s*group",
                r"make.*process\s*group",
                r"add.*process\s*group",
                r"new.*process\s*group",
            ],
            NiFiIntent.DELETE_PROCESS_GROUP: [
                r"delete.*process\s*group",
                r"remove.*process\s*group",
                r"drop.*process\s*group",
            ],
            NiFiIntent.START_PROCESS_GROUP: [
                r"start.*process\s*group",
                r"run.*process\s*group",
                r"begin.*process\s*group",
            ],
            NiFiIntent.STOP_PROCESS_GROUP: [
                r"stop.*process\s*group",
                r"halt.*process\s*group",
                r"pause.*process\s*group",
            ],
            
            # Processor Operations
            NiFiIntent.LIST_PROCESSORS: [
                r"list.*processors?",
                r"show.*processors?",
                r"get.*processors?",
                r"what.*processors?",
            ],
            NiFiIntent.CREATE_PROCESSOR: [
                r"create.*processor",
                r"make.*processor",
                r"add.*processor",
                r"new.*processor",
            ],
            NiFiIntent.START_PROCESSOR: [
                r"start.*processor",
                r"run.*processor",
                r"begin.*processor",
            ],
            NiFiIntent.STOP_PROCESSOR: [
                r"stop.*processor",
                r"halt.*processor",
                r"pause.*processor",
            ],
            
            # Connection Operations
            NiFiIntent.LIST_CONNECTIONS: [
                r"list.*connections?",
                r"show.*connections?",
                r"get.*connections?",
            ],
            NiFiIntent.CREATE_CONNECTION: [
                r"create.*connection",
                r"connect.*",
                r"link.*",
            ],
            
            # Template Operations
            NiFiIntent.LIST_TEMPLATES: [
                r"list.*templates?",
                r"show.*templates?",
                r"get.*templates?",
            ],
            NiFiIntent.CREATE_TEMPLATE: [
                r"create.*template",
                r"make.*template",
                r"save.*template",
            ],
            NiFiIntent.INSTANTIATE_TEMPLATE: [
                r"instantiate.*template",
                r"use.*template",
                r"apply.*template",
            ],
            
            # Search Operations
            NiFiIntent.SEARCH_COMPONENTS: [
                r"search.*",
                r"find.*",
                r"look\s+for.*",
            ],
            
            # Status and Monitoring
            NiFiIntent.GET_STATUS: [
                r"status",
                r"health",
                r"how.*doing",
                r"what.*status",
            ],
            NiFiIntent.GET_FLOW_STATUS: [
                r"flow.*status",
                r"pipeline.*status",
                r"dataflow.*status",
            ],
            NiFiIntent.MONITOR_FLOW: [
                r"monitor.*flow",
                r"watch.*flow",
                r"track.*flow",
            ],
            
            # Documentation
            NiFiIntent.GET_DOCUMENTATION: [
                r"help.*",
                r"documentation.*",
                r"docs.*",
                r"how.*use",
                r"what.*is",
            ],
            NiFiIntent.GET_PROCESSOR_INFO: [
                r".*processor.*info",
                r".*processor.*documentation",
                r"what.*does.*processor",
            ],
            
            # General
            NiFiIntent.HELP: [
                r"help",
                r"usage",
                r"commands?",
                r"what.*can.*do",
            ],
        }
    
    async def process_query(self, query: str) -> ProcessedIntent:
        """
        Process a natural language query to extract intent and parameters.
        
        Args:
            query: Natural language query
            
        Returns:
            ProcessedIntent object with extracted information
        """
        query_lower = query.lower().strip()
        
        # Try LLM-based processing first
        if self.llm_provider:
            try:
                llm_result = await self._process_with_llm(query)
                if llm_result.confidence > 0.7:
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM processing failed: {e}, falling back to pattern matching")
        
        # Fallback to pattern matching
        return self._process_with_patterns(query)
    
    async def _process_with_llm(self, query: str) -> ProcessedIntent:
        """Process query using LLM provider."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(query)
        
        response = await self.llm_provider.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        return self._parse_llm_response(response, query)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for LLM."""
        intents_list = "\n".join([f"- {intent.value}: {intent.value.replace('_', ' ').title()}" for intent in NiFiIntent])
        
        return f"""You are an expert Apache NiFi assistant that processes natural language queries and extracts structured intent and parameters for NiFi operations.

Available NiFi Intents:
{intents_list}

Your task is to analyze user queries and return a JSON response with the following structure:
{{
    "intent": "one_of_the_available_intents",
    "parameters": {{
        "process_group_id": "root or specific group ID",
        "process_group_name": "name if mentioned",
        "processor_name": "processor name if mentioned",
        "processor_type": "full processor class name if identifiable",
        "processor_id": "processor ID if mentioned",
        "connection_name": "connection name if mentioned",
        "template_name": "template name if mentioned",
        "search_query": "search terms if applicable",
        "properties": {{}},
        "relationships": [],
        "source_id": "source component ID if mentioned",
        "destination_id": "destination component ID if mentioned",
        "position": {{"x": 0, "y": 0}},
        "additional_params": {{}}
    }},
    "confidence": 0.0-1.0,
    "explanation": "Brief explanation of the extracted intent"
}}

Common NiFi processor types:
- GetFile: org.apache.nifi.processors.standard.GetFile
- PutFile: org.apache.nifi.processors.standard.PutFile
- GetHTTP: org.apache.nifi.processors.standard.GetHTTP
- PutHTTP: org.apache.nifi.processors.standard.PutHTTP
- ConsumeKafka: org.apache.nifi.processors.kafka.pubsub.ConsumeKafka_2_6
- PublishKafka: org.apache.nifi.processors.kafka.pubsub.PublishKafka_2_6
- JoltTransformJSON: org.apache.nifi.processors.standard.JoltTransformJSON
- RouteOnAttribute: org.apache.nifi.processors.standard.RouteOnAttribute

Be precise and extract as much relevant information as possible from the query."""
    
    def _build_user_prompt(self, query: str) -> str:
        """Build user prompt with the query."""
        return f"Analyze this NiFi query and extract the intent and parameters: \"{query}\""
    
    def _parse_llm_response(self, response: str, original_query: str) -> ProcessedIntent:
        """Parse LLM response into ProcessedIntent."""
        try:
            data = json.loads(response)
            
            intent = NiFiIntent(data.get("intent", NiFiIntent.UNKNOWN))
            parameters = IntentParameters(**data.get("parameters", {}))
            confidence = float(data.get("confidence", 0.5))
            explanation = data.get("explanation", "")
            
            return ProcessedIntent(
                intent=intent,
                parameters=parameters,
                confidence=confidence,
                raw_query=original_query,
                explanation=explanation
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return ProcessedIntent(
                intent=NiFiIntent.UNKNOWN,
                parameters=IntentParameters(),
                confidence=0.0,
                raw_query=original_query,
                explanation="Failed to parse LLM response"
            )
    
    def _process_with_patterns(self, query: str) -> ProcessedIntent:
        """Process query using pattern matching."""
        query_lower = query.lower().strip()
        best_match = None
        best_confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    confidence = len(re.findall(pattern, query_lower)) * 0.3
                    if confidence > best_confidence:
                        best_match = intent
                        best_confidence = min(confidence, 0.8)  # Cap at 0.8 for pattern matching
        
        if best_match is None:
            best_match = NiFiIntent.UNKNOWN
            best_confidence = 0.0
        
        # Extract basic parameters using patterns
        parameters = self._extract_parameters_from_patterns(query_lower, best_match)
        
        return ProcessedIntent(
            intent=best_match,
            parameters=parameters,
            confidence=best_confidence,
            raw_query=query,
            explanation=f"Matched pattern for {best_match.value}"
        )
    
    def _extract_parameters_from_patterns(self, query: str, intent: NiFiIntent) -> IntentParameters:
        """Extract parameters using regex patterns."""
        params = IntentParameters()
        
        # Extract names in quotes
        name_matches = re.findall(r'["\']([^"\']+)["\']', query)
        if name_matches:
            if intent in [NiFiIntent.CREATE_PROCESS_GROUP, NiFiIntent.START_PROCESS_GROUP, NiFiIntent.STOP_PROCESS_GROUP]:
                params.process_group_name = name_matches[0]
            elif intent in [NiFiIntent.CREATE_PROCESSOR, NiFiIntent.START_PROCESSOR, NiFiIntent.STOP_PROCESSOR]:
                params.processor_name = name_matches[0]
            elif intent in [NiFiIntent.CREATE_TEMPLATE, NiFiIntent.INSTANTIATE_TEMPLATE]:
                params.template_name = name_matches[0]
        
        # Extract processor types
        processor_type_patterns = {
            r'getfile|get\s+file': 'org.apache.nifi.processors.standard.GetFile',
            r'putfile|put\s+file': 'org.apache.nifi.processors.standard.PutFile',
            r'gethttp|get\s+http': 'org.apache.nifi.processors.standard.GetHTTP',
            r'puthttp|put\s+http': 'org.apache.nifi.processors.standard.PutHTTP',
            r'kafka.*consume|consume.*kafka': 'org.apache.nifi.processors.kafka.pubsub.ConsumeKafka_2_6',
            r'kafka.*publish|publish.*kafka': 'org.apache.nifi.processors.kafka.pubsub.PublishKafka_2_6',
            r'jolt|transform.*json': 'org.apache.nifi.processors.standard.JoltTransformJSON',
            r'route.*attribute': 'org.apache.nifi.processors.standard.RouteOnAttribute',
        }
        
        for pattern, processor_type in processor_type_patterns.items():
            if re.search(pattern, query):
                params.processor_type = processor_type
                break
        
        # Extract search queries
        if intent == NiFiIntent.SEARCH_COMPONENTS:
            search_patterns = [
                r'search\s+for\s+(.+)',
                r'find\s+(.+)',
                r'look\s+for\s+(.+)',
            ]
            for pattern in search_patterns:
                match = re.search(pattern, query)
                if match:
                    params.search_query = match.group(1).strip()
                    break
        
        # Extract process group references
        pg_patterns = [
            r'in\s+(?:the\s+)?(.+?)\s+(?:process\s+)?group',
            r'(?:process\s+)?group\s+(.+)',
        ]
        for pattern in pg_patterns:
            match = re.search(pattern, query)
            if match:
                group_name = match.group(1).strip().strip('"\'')
                if group_name.lower() not in ['root', 'main', 'default']:
                    params.process_group_name = group_name
                break
        
        return params
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return [intent.value for intent in NiFiIntent]
    
    def get_intent_examples(self) -> Dict[str, List[str]]:
        """Get example queries for each intent."""
        return {
            NiFiIntent.LIST_PROCESS_GROUPS.value: [
                "List all process groups",
                "Show me the process groups",
                "What process groups are available?"
            ],
            NiFiIntent.CREATE_PROCESS_GROUP.value: [
                "Create a process group called 'Data Processing'",
                "Make a new process group named 'ETL Pipeline'",
                "Add a process group for data transformation"
            ],
            NiFiIntent.LIST_PROCESSORS.value: [
                "List processors in the main process group",
                "Show me all processors",
                "What processors are running?"
            ],
            NiFiIntent.CREATE_PROCESSOR.value: [
                "Create a GetFile processor",
                "Add a new Kafka consumer processor",
                "Make a processor to read files"
            ],
            NiFiIntent.START_PROCESSOR.value: [
                "Start the GetFile processor",
                "Run all processors in the ETL group",
                "Begin processing data"
            ],
            NiFiIntent.STOP_PROCESSOR.value: [
                "Stop the data processing flow",
                "Halt all processors",
                "Pause the ETL pipeline"
            ],
            NiFiIntent.SEARCH_COMPONENTS.value: [
                "Search for GetFile processors",
                "Find all Kafka-related components",
                "Look for processors with 'transform' in the name"
            ],
            NiFiIntent.GET_STATUS.value: [
                "What's the status of my flow?",
                "How is NiFi doing?",
                "Show me the system health"
            ],
            NiFiIntent.GET_DOCUMENTATION.value: [
                "What is the GetFile processor?",
                "Help me understand how to use RouteOnAttribute",
                "Show documentation for JoltTransformJSON"
            ]
        }


# Convenience function for creating an intent processor
def create_intent_processor(provider_type: str = "openai", **kwargs) -> IntentProcessor:
    """
    Create an intent processor with the specified LLM provider.
    
    Args:
        provider_type: Type of LLM provider ("openai", "anthropic", "local")
        **kwargs: Additional arguments for the provider
        
    Returns:
        Configured IntentProcessor instance
    """
    provider = None
    
    if provider_type.lower() == "openai":
        try:
            provider = OpenAIProvider(**kwargs)
        except Exception as e:
            logger.warning(f"Failed to create OpenAI provider: {e}")
    
    elif provider_type.lower() == "anthropic":
        try:
            provider = AnthropicProvider(**kwargs)
        except Exception as e:
            logger.warning(f"Failed to create Anthropic provider: {e}")
    
    return IntentProcessor(provider)
