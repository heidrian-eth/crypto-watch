#!/bin/bash

# Crypto Watch Dashboard Runner

echo "🚀 Starting Crypto Watch Dashboard..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    # Try Python 3.12 first, fall back to python3 if not available
    if command -v python3.12 &> /dev/null; then
        python3.12 -m venv venv
    else
        echo "⚠️  Python 3.12 not found, using default python3"
        python3 -m venv venv
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if ! python -c "import streamlit" &> /dev/null; then
    echo "📥 Installing requirements..."
    pip install -r requirements.txt
fi

# Check if Streamlit secrets file exists
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "⚠️  No .streamlit/secrets.toml file found"
    echo "ℹ️  Add your Binance API keys to .streamlit/secrets.toml for enhanced features"
fi

# Run the Streamlit app
echo "🌐 Launching dashboard..."
echo "📊 Dashboard will open in your browser at http://localhost:8501"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

streamlit run app_simple.py