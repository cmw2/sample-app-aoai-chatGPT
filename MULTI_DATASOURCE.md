# Multi-DataSource Configuration Guide

This guide explains how to configure and use the multi-datasource routing feature that allows the chatbot to intelligently select between multiple Azure AI Search indexes based on user queries.

## Overview

The multi-datasource feature uses Azure OpenAI to analyze user queries and route them to the most appropriate data source. This enables a single chatbot to answer questions from multiple knowledge bases intelligently.

## Configuration

### 1. Enable Multi-DataSource Mode

Set the following environment variable:
```bash
MULTI_DATASOURCE_ENABLED=True
```

### 2. Create Configuration Files

Copy the sample configuration files and customize them for your data sources:

```bash
# Copy sample files to create your configuration
cp backend/config/dataSources.json.sample backend/config/dataSources.json
cp backend/config/dataSourceMetadata.json.sample backend/config/dataSourceMetadata.json
```

Then edit these files to configure your specific Azure AI Search indexes and routing metadata.

### 3. Configure Routing Model (Optional)

You can specify a dedicated model for routing decisions:
```bash
AZURE_OPENAI_ROUTING_DEPLOYMENT_NAME=gpt-4o-mini
```

If not specified, it will use your main Azure OpenAI deployment for routing.

## How Routing Works

1. **User Query Analysis**: When a user message is received, the system extracts the user's question
2. **LLM Routing Decision**: The routing LLM analyzes the query against the metadata of available data sources
3. **Data Source Selection**: Based on keywords and descriptions, the most appropriate data source is selected
4. **Query Processing**: The user's query is processed using the selected data source
5. **Response Generation**: Azure OpenAI generates a response using the selected index
