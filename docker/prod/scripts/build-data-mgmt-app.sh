#!/bin/bash
set -euo pipefail

: "${GOOGLE_MAPS_API_KEY:=}"
: "${GOOGLE_MAPS_MAP_ID:=}"
: "${PROXY_BASE_URL:=}"

echo "Cloning repo $GITHUB_REPO at tag $GITHUB_TAG..."
git clone --depth 1 --branch "$GITHUB_TAG" "$GITHUB_REPO" source
cd source

echo "Installing dependencies..."
npm ci

echo "Creating .env file for build..."
cat <<EOF > .env
VITE_APP_VERSION=$GITHUB_TAG
VITE_APP_GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY
VITE_APP_GOOGLE_MAPS_MAP_ID=$GOOGLE_MAPS_MAP_ID
VITE_APP_PROXY_BASE_URL=$PROXY_BASE_URL
VITE_APP_BUILD_BASE_PATH=/web/
EOF

echo "Building frontend..."
npm run build

echo "Copying build output to frontend volume..."
rm -rf /app/dist/*
cp -r dist/* /app/dist/

echo "HydroServer Data Management app build complete. Shutting down container."