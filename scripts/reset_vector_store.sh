#!/bin/bash
# Reset Chroma DB Vector Store
# This script removes the existing vector store directory to resolve schema mismatch issues.

VECTOR_STORE_DIR="./vector_store"

echo "Resetting Vector Store..."

if [ -d "$VECTOR_STORE_DIR" ]; then
    rm -rf "$VECTOR_STORE_DIR"
    echo "Removed existing $VECTOR_STORE_DIR."
fi

mkdir -p "$VECTOR_STORE_DIR"
echo "Created fresh $VECTOR_STORE_DIR."

echo "Vector Store reset complete. Ready for new ingestion."
