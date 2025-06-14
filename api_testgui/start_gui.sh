#!/bin/bash
# Quick start script for Dansk Historie Online - Semantisk Søgning API Test GUI
# Checks dependencies and launches the Streamlit app

echo "🚀 Starting Dansk Historie Online - Semantisk Søgning API Test GUI..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import streamlit, requests" &> /dev/null; then
    echo "📦 Installing missing dependencies..."
    pip3 install -r requirements.txt
fi

# Check if Docker containers are running
echo "🐳 Checking if API server is accessible..."
if ! curl -s http://localhost:8080 > /dev/null; then
    echo "⚠️  Warning: API server not accessible at localhost:8080"
    echo "   Make sure Docker containers are running:"
    echo "   cd ../soegemaskine && docker-compose up -d"
fi

# Launch the GUI
echo "🌐 Launching GUI at http://localhost:8501"
echo "   Press Ctrl+C to stop"
streamlit run app.py
