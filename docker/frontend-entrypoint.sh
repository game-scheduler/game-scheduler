#!/bin/sh
# Generate config.js from environment variables at container startup
# This runs before nginx starts via docker-entrypoint.d mechanism

set -e

# Use envsubst to replace ${API_URL} in template
envsubst '${API_URL}' < /etc/nginx/templates/config.template.js > /usr/share/nginx/html/config.js

echo "Generated config.js with API_URL=${API_URL}"
