#!/bin/bash
set -e

# Start the Ollama server in the background
ollama serve &
OLLAMA_PID=$!

# Wait for the Ollama API to become available
echo "Waiting for Ollama to initiate..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
done

echo "Ollama is running. Ensuring required models are pulled..."
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text:latest
echo "Models are ready."

# Optionally, can add commands to start MCP servers here if they run continuously on a port,
# or simply leave the container running to accept npx executions.

# Suspend script execution to keep the container alive alongside the background process
wait $OLLAMA_PID
