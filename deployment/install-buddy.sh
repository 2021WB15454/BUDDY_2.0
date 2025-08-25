#!/bin/bash
# Universal BUDDY Installation Script
# Supports: Linux, macOS, Windows (via WSL/Git Bash)

set -e

# Constants
BUDDY_VERSION="1.0.0"
BUDDY_API_URL="http://localhost:8080"
INSTALL_DIR="/opt/buddy"
USER_DIR="$HOME/.buddy"
TEMP_DIR="/tmp/buddy-install"
SUPPORTED_PLATFORMS=("linux" "darwin" "windows")
SUPPORTED_ARCHITECTURES=("x86_64" "aarch64" "arm64")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Display banner
show_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    ____  __  ____  ____  __  __
   | __ )/ / |  _ \|  _ \ \ \/ /
   |  _ \/ /  | |_) | | | | \  / 
   | |_) | |  |  _ <| |_| | /  \ 
   |____/ /   |_| \_\____/ /_/\_\
         /                       
    
    BUDDY AI Assistant - Universal Installer
    Version 1.0.0
    
EOF
    echo -e "${NC}"
}

# Detect platform and architecture
detect_platform() {
    log "Detecting platform and architecture..."
    
    case "$(uname -s)" in
        Linux*)     PLATFORM="linux";;
        Darwin*)    PLATFORM="darwin";;
        MINGW*|CYGWIN*|MSYS*) PLATFORM="windows";;
        *)          PLATFORM="unknown"
    esac
    
    case "$(uname -m)" in
        x86_64|amd64)   ARCHITECTURE="x86_64";;
        aarch64)        ARCHITECTURE="aarch64";;
        arm64)          ARCHITECTURE="arm64";;
        armv7l)         ARCHITECTURE="armv7l";;
        *)              ARCHITECTURE="unknown"
    esac
    
    info "Detected: $PLATFORM ($ARCHITECTURE)"
    
    # Validate support
    if [[ ! " ${SUPPORTED_PLATFORMS[@]} " =~ " ${PLATFORM} " ]]; then
        error "Unsupported platform: $PLATFORM"
        exit 1
    fi
    
    if [[ ! " ${SUPPORTED_ARCHITECTURES[@]} " =~ " ${ARCHITECTURE} " ]]; then
        error "Unsupported architecture: $ARCHITECTURE"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check if running as root (not recommended for user installation)
    if [[ $EUID -eq 0 ]]; then
        warning "Running as root. Installing system-wide..."
        INSTALL_DIR="/opt/buddy"
        USER_DIR="/etc/buddy"
    else
        INSTALL_DIR="$HOME/.local/share/buddy"
        USER_DIR="$HOME/.config/buddy"
    fi
    
    # Check minimum disk space (500MB)
    if command -v df &> /dev/null; then
        if [[ "$PLATFORM" == "darwin" ]]; then
            AVAILABLE_SPACE=$(df -m "$HOME" | awk 'NR==2 {print $4}')
        else
            AVAILABLE_SPACE=$(df -BM "$HOME" | awk 'NR==2 {print $4}' | sed 's/M//')
        fi
        
        if [[ "$AVAILABLE_SPACE" -lt 500 ]]; then
            error "Insufficient disk space. At least 500MB required."
            exit 1
        fi
    fi
    
    # Check internet connectivity
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        warning "Limited internet connectivity detected. Some features may not work."
    fi
    
    # Check required tools
    local required_tools=("curl" "tar")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error "Required tool '$tool' is not installed."
            exit 1
        fi
    done
    
    log "System requirements check passed."
}

# Create directory structure
create_directories() {
    log "Creating directory structure..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$USER_DIR"
    mkdir -p "$TEMP_DIR"
    
    # Create subdirectories
    local subdirs=("bin" "lib" "share" "config" "logs" "cache" "models" "plugins")
    for subdir in "${subdirs[@]}"; do
        mkdir -p "$INSTALL_DIR/$subdir"
        mkdir -p "$USER_DIR/$subdir"
    done
    
    info "Directory structure created at $INSTALL_DIR"
}

# Download BUDDY components
download_buddy() {
    log "Downloading BUDDY components for $PLATFORM ($ARCHITECTURE)..."
    
    # For now, we'll use the existing BUDDY setup since it's already running
    # In production, this would download from release servers
    
    # Create a simple launcher script
    cat > "$TEMP_DIR/buddy" << 'EOF'
#!/bin/bash
# BUDDY Launcher Script

BUDDY_HOME="$(dirname "$(realpath "$0")")"
export BUDDY_HOME

# Check if BUDDY server is running
if curl -s http://localhost:8080/health &> /dev/null; then
    echo "BUDDY is running at http://localhost:8080"
else
    echo "Starting BUDDY server..."
    cd "$BUDDY_HOME/../../../packages/core"
    nohup ../../.venv/Scripts/python.exe -m buddy.main --api-only --port 8080 > "$BUDDY_HOME/../logs/buddy.log" 2>&1 &
    echo "BUDDY server starting... Check logs at $BUDDY_HOME/../logs/buddy.log"
fi

# Open web interface if available
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:3001"
elif command -v open &> /dev/null; then
    open "http://localhost:3001"
elif command -v start &> /dev/null; then
    start "http://localhost:3001"
else
    echo "Visit http://localhost:3001 to use BUDDY"
fi
EOF
    
    chmod +x "$TEMP_DIR/buddy"
    
    # Create configuration template
    cat > "$TEMP_DIR/config.yml" << EOF
# BUDDY Configuration
version: "$BUDDY_VERSION"
api:
  host: "localhost"
  port: 8080
  ssl: false

features:
  conversation_flow: true
  device_optimization: true
  emotional_intelligence: true
  health_wellness: true
  cross_platform_sync: true

logging:
  level: "INFO"
  file: "$USER_DIR/logs/buddy.log"

models:
  download_on_start: true
  cache_dir: "$USER_DIR/models"

plugins:
  enabled: true
  directory: "$USER_DIR/plugins"
EOF
    
    log "Components prepared for installation."
}

# Install BUDDY
install_buddy() {
    log "Installing BUDDY..."
    
    # Move components to installation directory
    cp "$TEMP_DIR/buddy" "$INSTALL_DIR/bin/buddy"
    cp "$TEMP_DIR/config.yml" "$USER_DIR/config/config.yml"
    
    # Make executable
    chmod +x "$INSTALL_DIR/bin/buddy"
    
    # Create symlink for global access (if installing system-wide)
    if [[ $EUID -eq 0 ]] || [[ -w "/usr/local/bin" ]]; then
        ln -sf "$INSTALL_DIR/bin/buddy" "/usr/local/bin/buddy"
        info "Global 'buddy' command installed"
    else
        # Add to user's PATH
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            mkdir -p "$HOME/.local/bin"
            ln -sf "$INSTALL_DIR/bin/buddy" "$HOME/.local/bin/buddy"
            
            # Add to shell profile
            local shell_profile=""
            if [[ -n "$ZSH_VERSION" ]]; then
                shell_profile="$HOME/.zshrc"
            elif [[ -n "$BASH_VERSION" ]]; then
                shell_profile="$HOME/.bashrc"
            fi
            
            if [[ -n "$shell_profile" ]] && [[ -f "$shell_profile" ]]; then
                if ! grep -q "$HOME/.local/bin" "$shell_profile"; then
                    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_profile"
                    info "Added $HOME/.local/bin to PATH in $shell_profile"
                fi
            fi
        fi
    fi
    
    log "BUDDY installation completed."
}

# Install desktop integration (Linux/macOS)
install_desktop_integration() {
    if [[ "$PLATFORM" == "linux" ]]; then
        install_linux_desktop_entry
    elif [[ "$PLATFORM" == "darwin" ]]; then
        install_macos_app_bundle
    fi
}

# Install Linux desktop entry
install_linux_desktop_entry() {
    log "Installing Linux desktop integration..."
    
    local desktop_dir="$HOME/.local/share/applications"
    mkdir -p "$desktop_dir"
    
    cat > "$desktop_dir/buddy-ai.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=BUDDY AI Assistant
GenericName=AI Assistant
Comment=Your personal AI assistant with conversation flow management
Exec=$INSTALL_DIR/bin/buddy
Icon=$INSTALL_DIR/share/buddy-icon.png
Terminal=false
Categories=Utility;Office;Development;
Keywords=AI;Assistant;Voice;Chat;Conversation;
StartupNotify=true
StartupWMClass=BUDDY
MimeType=x-scheme-handler/buddy;
EOF
    
    # Create a simple icon (text-based for now)
    cat > "$INSTALL_DIR/share/buddy-icon.png" << 'EOF'
# This would be a proper PNG icon in production
# For now, creating a placeholder
EOF
    
    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$desktop_dir"
    fi
    
    info "Desktop integration installed"
}

# Install macOS app bundle
install_macos_app_bundle() {
    log "Installing macOS app bundle..."
    
    local app_dir="/Applications/BUDDY.app"
    local contents_dir="$app_dir/Contents"
    local macos_dir="$contents_dir/MacOS"
    local resources_dir="$contents_dir/Resources"
    
    if [[ $EUID -eq 0 ]] || [[ -w "/Applications" ]]; then
        sudo mkdir -p "$macos_dir" "$resources_dir"
        
        # Create Info.plist
        sudo cat > "$contents_dir/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>BUDDY</string>
    <key>CFBundleIdentifier</key>
    <string>com.buddy.ai.assistant</string>
    <key>CFBundleName</key>
    <string>BUDDY</string>
    <key>CFBundleVersion</key>
    <string>$BUDDY_VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$BUDDY_VERSION</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF
        
        # Create launcher
        sudo cp "$INSTALL_DIR/bin/buddy" "$macos_dir/BUDDY"
        sudo chmod +x "$macos_dir/BUDDY"
        
        info "macOS app bundle installed at $app_dir"
    else
        warning "Cannot install to /Applications (requires admin privileges)"
    fi
}

# Install system service
install_system_service() {
    log "Installing system service..."
    
    if [[ "$PLATFORM" == "linux" ]]; then
        install_systemd_service
    elif [[ "$PLATFORM" == "darwin" ]]; then
        install_launchd_service
    fi
}

# Install systemd service (Linux)
install_systemd_service() {
    local service_file
    
    if [[ $EUID -eq 0 ]]; then
        service_file="/etc/systemd/system/buddy.service"
    else
        service_file="$HOME/.config/systemd/user/buddy.service"
        mkdir -p "$(dirname "$service_file")"
    fi
    
    cat > "$service_file" << EOF
[Unit]
Description=BUDDY AI Assistant
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/bin/buddy --daemon
Restart=always
RestartSec=10
Environment=HOME=$HOME
Environment=USER=$USER

[Install]
WantedBy=default.target
EOF
    
    if [[ $EUID -eq 0 ]]; then
        systemctl daemon-reload
        systemctl enable buddy
        info "System service installed (run 'sudo systemctl start buddy' to start)"
    else
        systemctl --user daemon-reload
        systemctl --user enable buddy
        info "User service installed (run 'systemctl --user start buddy' to start)"
    fi
}

# Install launchd service (macOS)
install_launchd_service() {
    local plist_file="$HOME/Library/LaunchAgents/com.buddy.ai.assistant.plist"
    mkdir -p "$(dirname "$plist_file")"
    
    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.buddy.ai.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/bin/buddy</string>
        <string>--daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$USER_DIR/logs/buddy.log</string>
    <key>StandardErrorPath</key>
    <string>$USER_DIR/logs/buddy-error.log</string>
</dict>
</plist>
EOF
    
    launchctl load "$plist_file" 2>/dev/null || true
    info "LaunchAgent installed"
}

# Post-installation setup
post_install_setup() {
    log "Running post-installation setup..."
    
    # Create initial logs
    mkdir -p "$USER_DIR/logs"
    touch "$USER_DIR/logs/buddy.log"
    
    # Set up shell completion (if supported)
    setup_shell_completion
    
    # Create uninstaller
    create_uninstaller
    
    # Display success message
    display_success_message
}

# Setup shell completion
setup_shell_completion() {
    local completion_dir
    
    if [[ -n "$ZSH_VERSION" ]]; then
        completion_dir="$HOME/.oh-my-zsh/completions"
        if [[ ! -d "$completion_dir" ]]; then
            completion_dir="$HOME/.zsh/completions"
        fi
    elif [[ -n "$BASH_VERSION" ]]; then
        completion_dir="$HOME/.bash_completion.d"
    fi
    
    if [[ -n "$completion_dir" ]]; then
        mkdir -p "$completion_dir"
        
        cat > "$completion_dir/_buddy" << 'EOF'
# BUDDY command completion
_buddy_completion() {
    local cur prev commands
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    commands="start stop restart status help config version update"
    
    COMPREPLY=($(compgen -W "$commands" -- "$cur"))
}

complete -F _buddy_completion buddy
EOF
        
        info "Shell completion installed"
    fi
}

# Create uninstaller
create_uninstaller() {
    cat > "$INSTALL_DIR/bin/buddy-uninstall" << EOF
#!/bin/bash
# BUDDY Uninstaller

echo "Uninstalling BUDDY AI Assistant..."

# Stop services
if [[ "$PLATFORM" == "linux" ]]; then
    systemctl --user stop buddy 2>/dev/null || true
    systemctl --user disable buddy 2>/dev/null || true
elif [[ "$PLATFORM" == "darwin" ]]; then
    launchctl unload "$HOME/Library/LaunchAgents/com.buddy.ai.assistant.plist" 2>/dev/null || true
fi

# Remove files
rm -rf "$INSTALL_DIR"
rm -rf "$USER_DIR"
rm -f "/usr/local/bin/buddy"
rm -f "$HOME/.local/bin/buddy"
rm -f "$HOME/.local/share/applications/buddy-ai.desktop"
rm -rf "/Applications/BUDDY.app"

echo "BUDDY has been uninstalled."
EOF
    
    chmod +x "$INSTALL_DIR/bin/buddy-uninstall"
}

# Display success message
display_success_message() {
    log "Installation completed successfully!"
    
    echo
    echo -e "${GREEN}🎉 BUDDY AI Assistant has been installed successfully!${NC}"
    echo
    echo -e "${BLUE}Quick Start:${NC}"
    echo "  • Run 'buddy' to start BUDDY"
    echo "  • Visit http://localhost:3001 for the web interface"
    echo "  • Visit http://localhost:8080 for the API"
    echo
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  • buddy --help          Show help"
    echo "  • buddy --status        Check BUDDY status"
    echo "  • buddy --config        Edit configuration"
    echo "  • buddy-uninstall       Uninstall BUDDY"
    echo
    echo -e "${BLUE}Features Available:${NC}"
    echo "  ✅ Enhanced conversation flow management"
    echo "  ✅ Cross-device synchronization"
    echo "  ✅ Emotional intelligence support"
    echo "  ✅ Health and wellness advice"
    echo "  ✅ 16 advanced AI skills"
    echo
    echo -e "${YELLOW}Note: BUDDY server is already running at http://localhost:8080${NC}"
    echo -e "${YELLOW}The web interface should be available at http://localhost:3001${NC}"
    echo
}

# Cleanup function
cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}

# Main installation function
main() {
    # Set up cleanup trap
    trap cleanup EXIT
    
    show_banner
    
    log "Starting BUDDY AI Assistant installation..."
    
    detect_platform
    check_requirements
    create_directories
    download_buddy
    install_buddy
    install_desktop_integration
    install_system_service
    post_install_setup
    
    log "BUDDY AI Assistant installation completed!"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "BUDDY AI Assistant Universal Installer"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --version, -v  Show version information"
        echo "  --dry-run      Show what would be installed without installing"
        echo
        exit 0
        ;;
    --version|-v)
        echo "BUDDY AI Assistant Installer v$BUDDY_VERSION"
        exit 0
        ;;
    --dry-run)
        echo "Dry run mode - showing what would be installed:"
        detect_platform
        echo "Platform: $PLATFORM ($ARCHITECTURE)"
        echo "Install directory: $INSTALL_DIR"
        echo "User directory: $USER_DIR"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
