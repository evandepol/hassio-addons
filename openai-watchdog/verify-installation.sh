#!/bin/bash

# OpenAI Watchdog Installation Verification Script
# This script verifies that all dependencies are properly installed and configured

set -e

echo "🔍 OpenAI Watchdog Installation Verification"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check Python installation
echo
print_info "Checking Python installation..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    print_status 0 "Python available: $PYTHON_VERSION"
else
    print_status 1 "Python3 not found"
    exit 1
fi

# Check pip installation
echo
print_info "Checking pip installation..."
if command -v pip3 >/dev/null 2>&1; then
    PIP_VERSION=$(pip3 --version 2>&1)
    print_status 0 "pip3 available: $PIP_VERSION"
else
    print_status 1 "pip3 not found"
    exit 1
fi

# Check if running in Docker/Home Assistant environment
echo
print_info "Checking environment..."
if [ -n "$SUPERVISOR_TOKEN" ] || [ -f "/.dockerenv" ]; then
    print_status 0 "Running in Home Assistant/Docker environment"
    CONTAINER_ENV=true
else
    print_warning "Running in local development environment"
    print_info "Note: Package installation may require virtual environment or --break-system-packages"
    CONTAINER_ENV=false
fi

# Check OpenAI package
echo
print_info "Checking OpenAI package installation..."
if python3 -c "import openai; print(f'OpenAI version: {openai.__version__}')" 2>/dev/null; then
    OPENAI_VERSION=$(python3 -c "import openai; print(openai.__version__)" 2>/dev/null)
    print_status 0 "OpenAI package installed: $OPENAI_VERSION"
else
    print_status 1 "OpenAI package not found"
    if [ "$CONTAINER_ENV" = true ]; then
        echo "Installing OpenAI package..."
        pip3 install openai
        if [ $? -eq 0 ]; then
            print_status 0 "OpenAI package installed successfully"
        else
            print_status 1 "Failed to install OpenAI package"
            exit 1
        fi
    else
        print_warning "In development environment - package will be installed during Docker build"
        print_info "To test locally, use: python3 -m venv venv && source venv/bin/activate && pip install openai"
    fi
fi

# Check other required packages
echo
print_info "Checking other required packages..."

PACKAGES=("yaml:pyyaml" "schedule:schedule" "dateutil:python-dateutil")

for package_info in "${PACKAGES[@]}"; do
    import_name=$(echo $package_info | cut -d: -f1)
    package_name=$(echo $package_info | cut -d: -f2)
    
    if python3 -c "import $import_name" 2>/dev/null; then
        print_status 0 "$package_name installed"
    else
        print_status 1 "$package_name not found"
        if [ "$CONTAINER_ENV" = true ]; then
            echo "Installing $package_name..."
            pip3 install $package_name
            if [ $? -eq 0 ]; then
                print_status 0 "$package_name installed successfully"
            else
                print_status 1 "Failed to install $package_name"
            fi
        else
            print_warning "Package will be installed during Docker build"
        fi
    fi
done

# Check file structure
echo
print_info "Checking file structure..."

REQUIRED_FILES=(
    "config.yaml"
    "build.yaml" 
    "Dockerfile"
    "run.sh"
    "README.md"
    "INSTALLATION.md"
    "watchdog/main.py"
    "watchdog/openai_analyzer.py"
    "watchdog/cost_tracker.py"
    "watchdog/ha_client.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_status 0 "$file exists"
    else
        print_status 1 "$file missing"
    fi
done

# Test Python imports
echo
print_info "Testing Python imports..."

python3 -c "
import sys
import os
sys.path.append('watchdog')

try:
    from openai_analyzer import OpenAIAnalyzer
    print('✅ OpenAIAnalyzer import successful')
except ImportError as e:
    print(f'❌ OpenAIAnalyzer import failed: {e}')
    
try:
    from cost_tracker import CostTracker
    print('✅ CostTracker import successful')
except ImportError as e:
    print(f'❌ CostTracker import failed: {e}')
    
try:
    from ha_client import HAClient
    print('✅ HAClient import successful')
except ImportError as e:
    print(f'❌ HAClient import failed: {e}')
"

# Check configuration schema
echo
print_info "Validating configuration schema..."

if [ -f "config.yaml" ]; then
    # Check for required fields
    if grep -q "openai_api_key" config.yaml; then
        print_status 0 "openai_api_key field present in config"
    else
        print_status 1 "openai_api_key field missing from config"
    fi
    
    if grep -q "openai_model" config.yaml; then
        print_status 0 "openai_model field present in config"
    else
        print_status 1 "openai_model field missing from config"
    fi
else
    print_status 1 "config.yaml not found"
fi

# Test OpenAI analyzer initialization (without API key)
echo
print_info "Testing OpenAI analyzer initialization..."

python3 -c "
import sys
import os
sys.path.append('watchdog')

try:
    from openai_analyzer import OpenAIAnalyzer
    
    # Test without API key (should work with mock mode)
    analyzer = OpenAIAnalyzer()
    print('✅ OpenAIAnalyzer initialized successfully (mock mode)')
    
    # Test model selection
    for model in ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo']:
        analyzer = OpenAIAnalyzer(model=model)
        print(f'✅ Model {model} initialization successful')
        
except Exception as e:
    print(f'❌ OpenAIAnalyzer initialization failed: {e}')
"

# Final summary
echo
echo "=============================================="
print_info "Installation verification complete!"
echo
print_warning "Next steps:"
echo "1. Set your OpenAI API key in the add-on configuration"
echo "2. Configure monitoring preferences"
echo "3. Start the add-on and check the logs"
echo
print_info "For detailed setup instructions, see INSTALLATION.md"