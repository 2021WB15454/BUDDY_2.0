"""
BUDDY Universal Port Manager
Platform-agnostic port management for any deployment environment
"""

import os
import socket
import logging
import platform
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class PortConfig:
    """Configuration for BUDDY port management"""
    host: str = "0.0.0.0"
    port: int = 0
    fallback_ports: list = None
    environment: str = "auto"
    
    def __post_init__(self):
        if self.fallback_ports is None:
            self.fallback_ports = [8000, 8080, 8082, 5000, 3000, 9000]

class UniversalPortManager:
    """
    Universal port management for BUDDY across all platforms
    
    Features:
    - Auto-detects platform (local dev, cloud, container)
    - Respects environment PORT variables
    - Finds free ports automatically
    - Supports reverse proxy configurations
    - Cloud provider agnostic (Heroku, Render, Railway, etc.)
    """
    
    def __init__(self, config: Optional[PortConfig] = None):
        self.config = config or PortConfig()
        self.environment = self._detect_environment()
        self.assigned_port: Optional[int] = None
        self.assigned_host: str = self.config.host
        
    def _detect_environment(self) -> str:
        """Detect the deployment environment"""
        # Cloud platform detection
        if os.getenv('RENDER'):
            return 'render'
        elif os.getenv('HEROKU'):
            return 'heroku' 
        elif os.getenv('RAILWAY_ENVIRONMENT'):
            return 'railway'
        elif os.getenv('FLY_APP_NAME'):
            return 'fly'
        elif os.getenv('VERCEL'):
            return 'vercel'
        elif os.getenv('NETLIFY'):
            return 'netlify'
        elif os.getenv('KUBERNETES_SERVICE_HOST'):
            return 'kubernetes'
        elif os.getenv('DOCKER_CONTAINER'):
            return 'docker'
        elif os.getenv('CI'):
            return 'ci'
        else:
            return 'local'
    
    def get_assigned_port(self) -> int:
        """
        Get the port BUDDY should use based on environment
        
        Priority:
        1. Environment variable PORT (cloud platforms)
        2. Environment variable BUDDY_PORT (custom)
        3. Auto-assign free port
        4. Fallback ports
        """
        # Check environment variables first (cloud platforms)
        env_port = os.getenv('PORT') or os.getenv('BUDDY_PORT')
        if env_port:
            try:
                port = int(env_port)
                if self._is_port_available(port):
                    logger.info(f"🌐 Using environment assigned port: {port}")
                    return port
                else:
                    logger.warning(f"⚠️  Environment port {port} not available, finding alternative")
            except ValueError:
                logger.warning(f"⚠️  Invalid port in environment: {env_port}")
        
        # Auto-assign free port (port 0 = OS assigns)
        if self.config.port == 0:
            port = self._find_free_port()
            if port:
                logger.info(f"🎯 Auto-assigned free port: {port}")
                return port
        
        # Try specified port
        if self.config.port > 0 and self._is_port_available(self.config.port):
            logger.info(f"🎯 Using configured port: {self.config.port}")
            return self.config.port
        
        # Try fallback ports
        for port in self.config.fallback_ports:
            if self._is_port_available(port):
                logger.info(f"🔄 Using fallback port: {port}")
                return port
        
        # Last resort - let OS decide
        port = self._find_free_port()
        logger.info(f"🆘 Using OS-assigned port: {port}")
        return port
    
    def _find_free_port(self) -> int:
        """Find a free port by binding to port 0"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((self.config.host, 0))
                _, port = sock.getsockname()
                return port
        except Exception as e:
            logger.error(f"❌ Error finding free port: {e}")
            return 8000  # Emergency fallback
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                result = sock.connect_ex((self.config.host, port))
                return result != 0
        except Exception:
            return False
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get complete server configuration"""
        port = self.get_assigned_port()
        self.assigned_port = port
        
        config = {
            'host': self.assigned_host,
            'port': port,
            'environment': self.environment,
            'urls': self._generate_urls(port),
            'platform_info': self._get_platform_info()
        }
        
        return config
    
    def _generate_urls(self, port: int) -> Dict[str, str]:
        """Generate all relevant URLs for BUDDY"""
        base_urls = {
            'local': f"http://localhost:{port}",
            'network': f"http://{self._get_local_ip()}:{port}",
        }
        
        # Add environment-specific URLs
        if self.environment == 'render':
            render_url = os.getenv('RENDER_EXTERNAL_URL')
            if render_url:
                base_urls['external'] = render_url
        elif self.environment == 'heroku':
            app_name = os.getenv('HEROKU_APP_NAME')
            if app_name:
                base_urls['external'] = f"https://{app_name}.herokuapp.com"
        elif self.environment == 'railway':
            railway_url = os.getenv('RAILWAY_STATIC_URL')
            if railway_url:
                base_urls['external'] = railway_url
        
        # Add API endpoints
        endpoints = {}
        for name, base_url in base_urls.items():
            endpoints[f"{name}_api"] = f"{base_url}/api"
            endpoints[f"{name}_health"] = f"{base_url}/health"
            endpoints[f"{name}_docs"] = f"{base_url}/docs"
            endpoints[f"{name}_chat"] = f"{base_url}/chat/universal"
        
        return {**base_urls, **endpoints}
    
    def _get_local_ip(self) -> str:
        """Get local IP address for network access"""
        try:
            # Connect to a remote address to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                local_ip = sock.getsockname()[0]
                return local_ip
        except Exception:
            return "127.0.0.1"
    
    def _get_platform_info(self) -> Dict[str, str]:
        """Get platform information"""
        return {
            'system': platform.system(),
            'architecture': platform.architecture()[0],
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'environment': self.environment
        }
    
    def print_startup_info(self) -> None:
        """Print comprehensive startup information"""
        config = self.get_server_config()
        
        print("🚀 BUDDY 2.0 Universal Port Manager")
        print("=" * 60)
        print(f"🌍 Environment: {self.environment.upper()}")
        print(f"🖥️  Platform: {config['platform_info']['system']} {config['platform_info']['architecture']}")
        print(f"🐍 Python: {config['platform_info']['python_version']}")
        print("=" * 60)
        print(f"📡 Server Host: {config['host']}")
        print(f"🎯 Assigned Port: {config['port']}")
        print("=" * 60)
        
        # Print URLs
        urls = config['urls']
        print("🔗 Access URLs:")
        for name, url in urls.items():
            if not name.endswith('_api') and not name.endswith('_health') and not name.endswith('_docs') and not name.endswith('_chat'):
                print(f"   {name.title()}: {url}")
        
        print("\n📚 API Endpoints:")
        print(f"   Health Check: {urls.get('local_health', 'N/A')}")
        print(f"   API Docs: {urls.get('local_docs', 'N/A')}")
        print(f"   Universal Chat: {urls.get('local_chat', 'N/A')}")
        
        if 'external' in urls:
            print(f"\n🌐 External URL: {urls['external']}")
        
        print("=" * 60)
        print("✅ BUDDY is universally accessible!")
        print("💡 Works with any cloud provider, container, or local setup")
        print("🔄 Auto-adapts to environment constraints")
        print("=" * 60)

    @contextmanager
    def managed_server(self):
        """Context manager for server lifecycle"""
        config = self.get_server_config()
        try:
            logger.info(f"🚀 Starting BUDDY server on {config['host']}:{config['port']}")
            yield config
        finally:
            logger.info(f"🛑 Shutting down BUDDY server")

# Global instance for easy access
universal_port_manager = UniversalPortManager()

# Convenience functions
def get_buddy_port() -> int:
    """Get the port BUDDY should use"""
    return universal_port_manager.get_assigned_port()

def get_buddy_host() -> str:
    """Get the host BUDDY should bind to"""
    return universal_port_manager.assigned_host

def get_server_config() -> Dict[str, Any]:
    """Get complete server configuration"""
    return universal_port_manager.get_server_config()

def print_startup_banner() -> None:
    """Print startup banner with all URLs"""
    universal_port_manager.print_startup_info()

def is_cloud_environment() -> bool:
    """Check if running in a cloud environment"""
    return universal_port_manager.environment not in ['local', 'docker']

def get_environment() -> str:
    """Get the detected environment"""
    return universal_port_manager.environment

# Platform-specific helpers
def configure_for_render():
    """Configure for Render.com deployment"""
    os.environ.setdefault('HOST', '0.0.0.0')
    if 'RENDER_EXTERNAL_URL' not in os.environ:
        logger.warning("RENDER_EXTERNAL_URL not set - external links may not work")

def configure_for_heroku():
    """Configure for Heroku deployment"""
    os.environ.setdefault('HOST', '0.0.0.0')
    if 'HEROKU_APP_NAME' not in os.environ:
        logger.warning("HEROKU_APP_NAME not set - external links may not work")

def configure_for_railway():
    """Configure for Railway deployment"""
    os.environ.setdefault('HOST', '0.0.0.0')
    if 'RAILWAY_STATIC_URL' not in os.environ:
        logger.warning("RAILWAY_STATIC_URL not set - external links may not work")

# Auto-configure based on environment
def auto_configure():
    """Auto-configure based on detected environment"""
    env = get_environment()
    if env == 'render':
        configure_for_render()
    elif env == 'heroku':
        configure_for_heroku()
    elif env == 'railway':
        configure_for_railway()

if __name__ == "__main__":
    # Demo the universal port manager
    manager = UniversalPortManager()
    manager.print_startup_info()
    
    print("\n🧪 Testing port availability...")
    for port in [8000, 8080, 8082, 3000, 5000]:
        available = manager._is_port_available(port)
        status = "✅ Available" if available else "❌ In Use"
        print(f"   Port {port}: {status}")
