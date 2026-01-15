#!/bin/bash
# =============================================================================
# EC2 Setup Script for TMDB Pipeline
# =============================================================================
# Run this script on a fresh EC2 instance (Amazon Linux 2023 or Ubuntu)
#
# Usage:
#   chmod +x tmdb_pipeline/scripts/ec2-setup.sh
#   ./tmdb_pipeline/scripts/ec2-setup.sh
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "TMDB Pipeline - EC2 Setup"
echo "=========================================="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS="unknown"
fi

echo "Detected OS: $OS"

# Install dependencies based on OS
if [ "$OS" == "amzn" ] || [ "$OS" == "rhel" ] || [ "$OS" == "centos" ]; then
    echo "Installing dependencies (Amazon Linux/RHEL)..."
    sudo yum update -y
    sudo yum install -y python3 python3-pip screen git
elif [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    echo "Installing dependencies (Ubuntu/Debian)..."
    sudo apt update
    sudo apt install -y python3 python3-pip screen git
else
    echo "Unknown OS. Please install python3, pip3, screen, and git manually."
    exit 1
fi

# Install Python packages
echo "Installing Python packages..."
if [ -f requirements.txt ]; then
    pip3 install --user -r requirements.txt
else
    echo "Warning: requirements.txt not found, installing packages manually..."
    pip3 install --user requests urllib3 sqlalchemy pymysql python-dotenv tqdm
fi

# Add local bin to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    export PATH="$HOME/.local/bin:$PATH"
fi

# Check if root .env exists
if [ ! -f ../../.env ]; then
    echo ""
    echo "=========================================="
    echo "IMPORTANT: Create your .env file"
    echo "=========================================="
    echo "Copy .env.example to .env at monorepo root and fill in your values:"
    echo ""
    echo "  cp ../../.env.example ../../.env"
    echo "  nano ../../.env"
    echo ""
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Create your .env file at monorepo root (if not done):"
echo "   cp ../../.env.example ../../.env"
echo "   nano ../../.env"
echo ""
echo "2. Test the connection:"
echo "   python3 -m tmdb_pipeline test"
echo ""
echo "3. Setup database tables:"
echo "   python3 -m tmdb_pipeline setup"
echo ""
echo "4. Run initial ingestion in screen (survives disconnect):"
echo "   screen -S tmdb"
echo "   python3 -m tmdb_pipeline initial"
echo "   # Press Ctrl+A, then D to detach"
echo "   # Use 'screen -r tmdb' to reattach"
echo ""
