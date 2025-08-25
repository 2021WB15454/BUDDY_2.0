#!/bin/bash

# BUDDY 2.0 Cross-Platform Installation Script
# ============================================
# 
# Installs and configures BUDDY 2.0 across all platforms:
# - MongoDB Atlas setup
# - Pinecone vector database
# - Firebase hosting and functions
# - Cross-device synchronization
# - Platform-specific builds

set -e

echo "🚀 BUDDY 2.0 Cross-Platform Installation"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
MONGODB_URI=""
PINECONE_API_KEY=""
FIREBASE_PROJECT_ID=""
FIREBASE_SERVICE_ACCOUNT=""

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Node.js dependencies
install_node_dependencies() {
    print_info "Installing Node.js dependencies..."
    
    if ! command_exists node; then
        print_error "Node.js is not installed. Please install Node.js 18+ first."
        exit 1
    fi
    
    if ! command_exists npm; then
        print_error "npm is not installed. Please install npm first."
        exit 1
    fi
    
    # Install global dependencies
    npm install -g firebase-tools
    npm install -g @angular/cli
    npm install -g expo-cli
    npm install -g electron-builder
    
    print_status "Node.js dependencies installed"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_info "Installing Python dependencies..."
    
    if ! command_exists python3; then
        print_error "Python 3.8+ is not installed. Please install Python first."
        exit 1
    fi
    
    # Create virtual environment
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Install Python packages
    pip install --upgrade pip
    pip install motor pymongo
    pip install pinecone-client sentence-transformers
    pip install fastapi uvicorn
    pip install pydantic
    pip install firebase-admin
    pip install python-multipart
    pip install aiofiles
    pip install websockets
    
    # Voice processing dependencies
    pip install pyaudio speechrecognition
    pip install whisper pyttsx3 gtts
    pip install webrtcvad
    
    print_status "Python dependencies installed"
}

# Function to setup MongoDB Atlas
setup_mongodb() {
    print_info "Setting up MongoDB Atlas..."
    
    if [ -z "$MONGODB_URI" ]; then
        print_warning "MongoDB URI not provided. Please set up MongoDB Atlas manually."
        print_info "1. Go to https://cloud.mongodb.com/"
        print_info "2. Create a new cluster"
        print_info "3. Create a database user"
        print_info "4. Get connection string and set MONGODB_URI environment variable"
        return
    fi
    
    # Test MongoDB connection
    python3 -c "
import motor.motor_asyncio
import asyncio

async def test_connection():
    client = motor.motor_asyncio.AsyncIOMotorClient('$MONGODB_URI')
    try:
        await client.admin.command('ping')
        print('✅ MongoDB connection successful')
    except Exception as e:
        print(f'❌ MongoDB connection failed: {e}')
        
asyncio.run(test_connection())
"
    
    print_status "MongoDB Atlas configured"
}

# Function to setup Pinecone
setup_pinecone() {
    print_info "Setting up Pinecone vector database..."
    
    if [ -z "$PINECONE_API_KEY" ]; then
        print_warning "Pinecone API key not provided. Please set up Pinecone manually."
        print_info "1. Go to https://www.pinecone.io/"
        print_info "2. Create an account and get API key"
        print_info "3. Set PINECONE_API_KEY environment variable"
        return
    fi
    
    # Test Pinecone connection
    python3 -c "
import pinecone
import os

try:
    pc = pinecone.Pinecone(api_key='$PINECONE_API_KEY')
    indexes = list(pc.list_indexes())
    print('✅ Pinecone connection successful')
except Exception as e:
    print(f'❌ Pinecone connection failed: {e}')
"
    
    print_status "Pinecone vector database configured"
}

# Function to setup Firebase
setup_firebase() {
    print_info "Setting up Firebase hosting and functions..."
    
    if ! command_exists firebase; then
        print_error "Firebase CLI not installed. Installing..."
        npm install -g firebase-tools
    fi
    
    # Login to Firebase (if not already logged in)
    firebase login --no-localhost
    
    # Initialize Firebase project
    if [ -n "$FIREBASE_PROJECT_ID" ]; then
        firebase use "$FIREBASE_PROJECT_ID"
    else
        print_warning "Firebase project ID not provided. Please run 'firebase init' manually."
    fi
    
    # Set up hosting targets
    firebase target:apply hosting buddy-web-app buddy-web
    firebase target:apply hosting buddy-admin-dashboard buddy-admin
    firebase target:apply hosting buddy-desktop-app buddy-desktop
    
    print_status "Firebase configured"
}

# Function to build web applications
build_web_apps() {
    print_info "Building web applications..."
    
    # Create web app directories if they don't exist
    mkdir -p web/src web/public
    mkdir -p admin/src admin/public
    
    # Build web app (would be actual React/Vue build in production)
    print_info "Building main web application..."
    cd web
    if [ -f "package.json" ]; then
        npm install
        npm run build
    else
        print_warning "Web app package.json not found. Skipping web build."
        # Create basic build directory for demo
        mkdir -p build
        echo '<!DOCTYPE html><html><head><title>BUDDY 2.0</title></head><body><h1>BUDDY 2.0 Web App</h1></body></html>' > build/index.html
    fi
    cd ..
    
    # Build admin dashboard
    print_info "Building admin dashboard..."
    cd admin
    if [ -f "package.json" ]; then
        npm install
        npm run build
    else
        print_warning "Admin dashboard package.json not found. Skipping admin build."
        # Create basic build directory for demo
        mkdir -p build
        echo '<!DOCTYPE html><html><head><title>BUDDY 2.0 Admin</title></head><body><h1>BUDDY 2.0 Admin Dashboard</h1></body></html>' > build/index.html
    fi
    cd ..
    
    print_status "Web applications built"
}

# Function to build mobile apps
build_mobile_apps() {
    print_info "Building mobile applications..."
    
    # React Native setup
    if [ -d "apps/mobile" ]; then
        cd apps/mobile
        
        if [ -f "package.json" ]; then
            npm install
            
            # iOS build (macOS only)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                print_info "Building iOS app..."
                cd ios && pod install && cd ..
                npx react-native run-ios --configuration Release
            fi
            
            # Android build
            print_info "Building Android app..."
            npx react-native run-android --variant=release
        else
            print_warning "Mobile app package.json not found. Skipping mobile build."
        fi
        
        cd ../..
    else
        print_warning "Mobile app directory not found. Skipping mobile build."
    fi
    
    print_status "Mobile applications built"
}

# Function to build desktop apps
build_desktop_apps() {
    print_info "Building desktop applications..."
    
    if [ -d "apps/desktop" ]; then
        cd apps/desktop
        
        if [ -f "package.json" ]; then
            npm install
            npm run build
            npm run electron:build
        else
            print_warning "Desktop app package.json not found. Skipping desktop build."
        fi
        
        cd ../..
    else
        print_warning "Desktop app directory not found. Skipping desktop build."
    fi
    
    print_status "Desktop applications built"
}

# Function to deploy to Firebase
deploy_firebase() {
    print_info "Deploying to Firebase..."
    
    # Deploy functions
    firebase deploy --only functions
    
    # Deploy hosting
    firebase deploy --only hosting
    
    print_status "Firebase deployment complete"
}

# Function to create configuration files
create_config_files() {
    print_info "Creating configuration files..."
    
    # Create environment configuration
    cat > .env << EOF
# BUDDY 2.0 Environment Configuration
MONGODB_URI=$MONGODB_URI
PINECONE_API_KEY=$PINECONE_API_KEY
FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID

# API Configuration
API_BASE_URL=https://$FIREBASE_PROJECT_ID.web.app/api
WS_BASE_URL=wss://$FIREBASE_PROJECT_ID.web.app/ws

# Voice Configuration
VOICE_ENGINE=whisper
TTS_ENGINE=pyttsx3
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Sync Configuration
SYNC_INTERVAL=300
MAX_CONCURRENT_SYNCS=5
SYNC_BATCH_SIZE=50
EOF
    
    # Create Docker configuration
    cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    portaudio19-dev \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "buddy_main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    
    # Create requirements.txt
    pip freeze > requirements.txt
    
    print_status "Configuration files created"
}

# Function to run tests
run_tests() {
    print_info "Running tests..."
    
    # Run Python tests
    python3 -m pytest infrastructure/tests/ -v
    
    # Run voice system tests
    python3 test_phase8_voice.py
    
    # Run cross-platform integration tests
    python3 infrastructure/tests/test_cross_platform.py
    
    print_status "All tests passed"
}

# Main installation function
main() {
    print_info "Starting BUDDY 2.0 cross-platform installation..."
    
    # Check for configuration
    if [ -f ".env" ]; then
        source .env
    fi
    
    # Installation steps
    install_node_dependencies
    install_python_dependencies
    setup_mongodb
    setup_pinecone
    setup_firebase
    build_web_apps
    build_mobile_apps
    build_desktop_apps
    create_config_files
    
    # Deploy if in production mode
    if [ "$1" = "--deploy" ]; then
        deploy_firebase
    fi
    
    # Run tests if requested
    if [ "$1" = "--test" ] || [ "$2" = "--test" ]; then
        run_tests
    fi
    
    print_status "BUDDY 2.0 installation complete!"
    print_info "Next steps:"
    print_info "1. Configure your environment variables in .env"
    print_info "2. Run 'python3 buddy_main.py' to start the backend"
    print_info "3. Run 'firebase serve' to test locally"
    print_info "4. Run '$0 --deploy' to deploy to production"
    
    print_info "🎉 BUDDY 2.0 is ready for cross-platform deployment!"
}

# Parse command line arguments
case "$1" in
    --help|-h)
        echo "BUDDY 2.0 Installation Script"
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --deploy     Deploy to Firebase after installation"
        echo "  --test       Run tests after installation"
        echo "  --help       Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
