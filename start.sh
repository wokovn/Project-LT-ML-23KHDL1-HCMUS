#!/bin/bash

# Exit on error
set -e

echo "Starting services..."

# Start Node backend in the background
echo "Starting Node Backend..."
cd /app/backend
npm start &

# Start Nginx in the foreground
echo "Starting Nginx Reverse Proxy on port 7860..."
nginx -c /app/nginx.conf -g "daemon off;"
