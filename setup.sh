#!/bin/bash

# Setup script for Hyperlocal News Summarizer

echo "🚀 Setting up Hyperlocal News Summarizer..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Download spaCy model
echo "📚 Downloading spaCy English model..."
python -m spacy download en_core_web_sm

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p audio_output
mkdir -p templates
mkdir -p static

echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run: python app.py"
echo "  3. Open browser: http://localhost:5000"

