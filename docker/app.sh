#!/bin/bash

echo "Starting application..."
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4