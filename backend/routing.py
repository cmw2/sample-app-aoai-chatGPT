"""
Multi-datasource routing logic using LLM for data source selection.
"""
import json
import logging
import httpx
from typing import List, Dict, Any, Optional

from backend.settings import _DataSourceMetadata

logger = logging.getLogger(__name__)


class SelectedDataSourceWrapper:
    """
    Wrapper class to make a selected datasource payload behave like a datasource settings object.
    This allows the existing prepare_model_args function to work without modification.
    """
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self._type = payload.get('type', 'azure_search')
    
    def construct_payload_configuration(self, *args, **kwargs) -> Dict[str, Any]:
        """Return the pre-constructed payload."""
        return self.payload


async def select_data_source(
    user_query: str,
    metadata: List[_DataSourceMetadata],
    azure_openai_client,
    routing_deployment: str
) -> int:
    """
    Use Azure OpenAI to select the most appropriate data source for the user query.
    
    Args:
        user_query: The user's question/query
        metadata: List of data source metadata for routing decisions
        azure_openai_client: Initialized Azure OpenAI client
        routing_deployment: The deployment name to use for routing decisions
        
    Returns:
        Index of the selected data source (0-based)
        
    Raises:
        Exception: If routing fails, but provides fallback to index 0
    """
    try:
        if not metadata or len(metadata) == 0:
            logger.warning("No metadata provided for routing, falling back to index 0")
            return 0
        
        if len(metadata) == 1:
            logger.debug("Only one data source available, using index 0")
            return 0
        
        # Construct routing prompt
        routing_prompt = f"""You are a routing assistant. Based on the user's query, select the most appropriate data source by returning ONLY the index number (0, 1, 2, etc.).

Available data sources:
{_format_metadata_for_prompt(metadata)}

User query: "{user_query}"

Respond with ONLY the index number of the most appropriate data source:"""

        logger.debug(f"Using routing model: {routing_deployment} for data source selection")
        
        # Make request to Azure OpenAI
        messages = [{"role": "user", "content": routing_prompt}]
        
        response = await azure_openai_client.chat.completions.create(
            model=routing_deployment,
            messages=messages,
            max_tokens=10,
            temperature=0.0  # Use deterministic routing
        )
        
        if not response.choices or len(response.choices) == 0:
            logger.error("No choices in routing response")
            return 0
        
        # Parse response
        selected_text = response.choices[0].message.content.strip()
        
        try:
            selected_index = int(selected_text)
        except ValueError:
            logger.warning(f"Invalid routing response: '{selected_text}', using default index 0")
            return 0
        
        # Validate selected index
        if 0 <= selected_index < len(metadata):
            logger.info(f"Routing LLM selected data source {selected_index}: {metadata[selected_index].name}")
            return selected_index
        else:
            logger.warning(f"Invalid routing response: {selected_index}, using default index 0")
            return 0
            
    except Exception as e:
        logger.error(f"Error in data source routing: {e}")
        return 0  # Fallback to first data source


def _format_metadata_for_prompt(metadata: List[_DataSourceMetadata]) -> str:
    """
    Format metadata list for inclusion in the routing prompt.
    
    Args:
        metadata: List of data source metadata
        
    Returns:
        Formatted string for prompt inclusion
    """
    formatted_lines = []
    for i, meta in enumerate(metadata):
        keywords_str = f" Keywords: {', '.join(meta.keywords)}" if meta.keywords else ""
        formatted_lines.append(f"{i}: {meta.name} - {meta.description}{keywords_str}")
    
    return "\n".join(formatted_lines)


def create_datasource_payload_from_config(
    datasource_config: Dict[str, Any],
    app_settings
) -> Dict[str, Any]:
    """
    Create a datasource payload configuration from a datasource config dictionary.
    
    This function converts the JSON configuration format into the format expected
    by the Azure OpenAI data sources API.
    
    Args:
        datasource_config: Raw datasource configuration from JSON
        app_settings: Application settings instance
        
    Returns:
        Formatted datasource payload for Azure OpenAI API
    """
    if not datasource_config or not datasource_config.get('parameters'):
        raise ValueError("Invalid datasource configuration")
    
    params = datasource_config['parameters'].copy()
    
    # Add embedding dependency if available
    if hasattr(app_settings, 'azure_openai'):
        embedding_dependency = app_settings.azure_openai.extract_embedding_dependency()
        if embedding_dependency:
            params['embedding_dependency'] = embedding_dependency
    
    # Add search common settings if available
    if hasattr(app_settings, 'search'):
        search_params = app_settings.search.model_dump(exclude_none=True, by_alias=True)
        params.update(search_params)
    
    return {
        "type": datasource_config.get('type', 'azure_search'),
        "parameters": params
    }


async def get_routed_datasource_payload(
    user_query: str,
    multi_datasource_settings,
    app_settings,
    azure_openai_client,
    request=None
) -> Dict[str, Any]:
    """
    Get the appropriate datasource payload based on routing decision.
    
    Args:
        user_query: The user's query for routing decision
        multi_datasource_settings: Multi-datasource settings instance
        app_settings: Application settings instance  
        azure_openai_client: Initialized Azure OpenAI client
        request: Optional request object for additional context
        
    Returns:
        Datasource payload configuration for the selected data source
    """
    try:
        # Select appropriate data source
        selected_index = await select_data_source(
            user_query=user_query,
            metadata=multi_datasource_settings.metadata,
            azure_openai_client=azure_openai_client,
            routing_deployment=multi_datasource_settings.routing_deployment
        )
        
        # Get selected datasource configuration
        datasource_config = multi_datasource_settings.get_datasource_by_index(selected_index)
        
        if not datasource_config:
            raise Exception("No valid datasource configuration found")
        
        # Create payload from configuration
        payload = create_datasource_payload_from_config(datasource_config, app_settings)
        
        logger.info(f"Using data source {selected_index} ({multi_datasource_settings.metadata[selected_index].name}) for query")
        
        return payload
        
    except Exception as e:
        logger.error(f"Failed to get routed datasource payload: {e}")
        
        # Fallback to first datasource
        if multi_datasource_settings.datasources:
            fallback_config = multi_datasource_settings.datasources[0]
            logger.info("Falling back to first available datasource")
            return create_datasource_payload_from_config(fallback_config, app_settings)
        else:
            raise Exception("No datasources available for fallback")


# Utility function for testing routing logic
async def test_routing_logic():
    """Test function for routing logic (for development/debugging)."""
    
    # Mock metadata for testing
    test_metadata = [
        _DataSourceMetadata(
            id="docs",
            name="Documentation",
            description="User guides and documentation",
            keywords=["guide", "help", "documentation", "manual"]
        ),
        _DataSourceMetadata(
            id="api",
            name="API Reference",
            description="Technical API specifications",
            keywords=["API", "technical", "reference", "developer"]
        )
    ]
    
    test_queries = [
        "How do I install the software?",  # Should route to docs
        "What are the API endpoints?",     # Should route to API
        "Show me the user manual",        # Should route to docs
        "What parameters does the create user API accept?"  # Should route to API
    ]
    
    print("=== Routing Logic Test ===")
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("Formatted metadata for prompt:")
        print(_format_metadata_for_prompt(test_metadata))
        
        # Note: In real usage, this would make an actual API call
        # For testing purposes, we're just showing the prompt format
        print(f"Would route based on similarity to metadata keywords")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_routing_logic())