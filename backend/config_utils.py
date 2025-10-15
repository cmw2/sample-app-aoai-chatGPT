"""
Multi-datasource configuration utilities and template processing.
"""
import json
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def process_template(template: Any) -> Any:
    """
    Process template object by replacing ${VARIABLE_NAME} with environment variables.
    
    Args:
        template: The template object (dict, list, string, etc.) to process
        
    Returns:
        The processed object with environment variables replaced
    """
    if isinstance(template, str):
        # Handle string template replacement
        import re
        def replace_env_var(match):
            env_var = match.group(1)
            value = os.environ.get(env_var)
            if value is None:
                logger.warning(f"Environment variable {env_var} not found, keeping placeholder")
                return match.group(0)  # Keep the placeholder if env var missing
            return value
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, template)
    
    elif isinstance(template, dict):
        # Process dictionary recursively
        return {key: process_template(value) for key, value in template.items()}
    
    elif isinstance(template, list):
        # Process list recursively
        return [process_template(item) for item in template]
    
    else:
        # Return as-is for other types (int, bool, None, etc.)
        return template


def load_datasources_config(config_file_path: str) -> List[Dict[str, Any]]:
    """
    Load data sources configuration from JSON file with environment variable processing.
    
    Args:
        config_file_path: Path to the dataSources.json file
        
    Returns:
        List of processed data source configurations
        
    Raises:
        Exception: If configuration cannot be loaded or is invalid
    """
    try:
        logger.info(f"Loading data sources from config file: {config_file_path}")
        with open(config_file_path, 'r') as f:
            config = json.load(f)
        return process_template(config)
            
    except FileNotFoundError:
        raise Exception(f"Data sources config file not found: {config_file_path}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in data sources config: {e}")
    except Exception as e:
        logger.error(f"Failed to load data sources config: {e}")
        raise


def load_metadata_config(config_file_path: str) -> List[Dict[str, Any]]:
    """
    Load data source metadata configuration from JSON file.
    
    Args:
        config_file_path: Path to the dataSourceMetadata.json file
        
    Returns:
        List of data source metadata configurations
        
    Raises:
        Exception: If configuration cannot be loaded or is invalid
    """
    try:
        logger.info(f"Loading metadata from config file: {config_file_path}")
        with open(config_file_path, 'r') as f:
            return json.load(f)
                
    except FileNotFoundError:
        raise Exception(f"Metadata config file not found: {config_file_path}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in metadata config: {e}")
    except Exception as e:
        logger.error(f"Failed to load metadata config: {e}")
        raise


def validate_datasources_config(datasources: List[Dict[str, Any]], metadata: List[Dict[str, Any]]) -> bool:
    """
    Validate that datasources and metadata configurations are consistent.
    
    Args:
        datasources: List of data source configurations
        metadata: List of metadata configurations
        
    Returns:
        True if valid, raises Exception if invalid
        
    Raises:
        Exception: If validation fails
    """
    if len(datasources) != len(metadata):
        raise Exception(
            f"Mismatch between datasources ({len(datasources)}) and metadata ({len(metadata)}) counts"
        )
    
    if len(datasources) == 0:
        raise Exception("At least one data source must be configured")
    
    # Validate each data source has required fields
    for i, ds in enumerate(datasources):
        if not ds.get('type'):
            raise Exception(f"Data source {i} missing 'type' field")
        if not ds.get('parameters'):
            raise Exception(f"Data source {i} missing 'parameters' field")
            
        params = ds['parameters']
        required_fields = ['endpoint', 'index_name']
        for field in required_fields:
            if not params.get(field):
                raise Exception(f"Data source {i} missing required parameter '{field}'")
    
    # Validate metadata
    for i, meta in enumerate(metadata):
        required_fields = ['id', 'name', 'description', 'keywords']
        for field in required_fields:
            if not meta.get(field):
                raise Exception(f"Metadata {i} missing required field '{field}'")
        
        if not isinstance(meta['keywords'], list):
            raise Exception(f"Metadata {i} 'keywords' must be a list")
    
    logger.info(f"Validated {len(datasources)} data sources and metadata configurations")
    return True


# Test function to verify template processing
def test_template_processing():
    """Test function to verify environment variable replacement works correctly."""
    
    # Set some test environment variables
    os.environ['TEST_ENDPOINT'] = 'https://test.search.windows.net'
    os.environ['TEST_INDEX'] = 'test-index'
    os.environ['TEST_KEY'] = 'test-key-123'
    
    # Test template object
    test_template = {
        "type": "azure_search",
        "parameters": {
            "endpoint": "${TEST_ENDPOINT}",
            "index_name": "${TEST_INDEX}",
            "key": "${TEST_KEY}",
            "static_value": "should-remain-unchanged",
            "missing_var": "${MISSING_VAR}",
            "nested": {
                "inner_endpoint": "${TEST_ENDPOINT}",
                "list_with_templates": ["${TEST_INDEX}", "static", "${TEST_KEY}"]
            }
        }
    }
    
    # Process template
    processed = process_template(test_template)
    
    # Verify results
    print("=== Template Processing Test ===")
    print("Original template:")
    print(json.dumps(test_template, indent=2))
    print("\nProcessed template:")
    print(json.dumps(processed, indent=2))
    
    # Assertions
    assert processed['parameters']['endpoint'] == 'https://test.search.windows.net'
    assert processed['parameters']['index_name'] == 'test-index'
    assert processed['parameters']['key'] == 'test-key-123'
    assert processed['parameters']['static_value'] == 'should-remain-unchanged'
    assert processed['parameters']['missing_var'] == '${MISSING_VAR}'  # Should remain as placeholder
    assert processed['parameters']['nested']['inner_endpoint'] == 'https://test.search.windows.net'
    assert processed['parameters']['nested']['list_with_templates'][0] == 'test-index'
    assert processed['parameters']['nested']['list_with_templates'][1] == 'static'
    assert processed['parameters']['nested']['list_with_templates'][2] == 'test-key-123'
    
    print("\n✅ All template processing tests passed!")
    
    # Clean up test environment variables
    del os.environ['TEST_ENDPOINT']
    del os.environ['TEST_INDEX'] 
    del os.environ['TEST_KEY']


if __name__ == "__main__":
    # Run test when file is executed directly
    test_template_processing()