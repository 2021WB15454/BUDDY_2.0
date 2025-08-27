"""
BUDDY Environment Configuration Helper
Platform-specific configurations for cloud providers and deployment environments
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class EnvironmentConfig:
    """Environment-specific configuration"""
    name: str
    host: str = "0.0.0.0"
    port: Optional[int] = None
    external_url: Optional[str] = None
    features: Dict[str, bool] = None
    env_vars: Dict[str, str] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {}
        if self.env_vars is None:
            self.env_vars = {}

class BuddyEnvironmentConfigurator:
    """Configure BUDDY for different deployment environments"""
    
    ENVIRONMENT_CONFIGS = {
        "render": EnvironmentConfig(
            name="Render",
            host="0.0.0.0",
            external_url=lambda: os.getenv("RENDER_EXTERNAL_URL"),
            features={
                "auto_ssl": True,
                "static_files": True,
                "build_cache": True,
                "health_checks": True
            },
            env_vars={
                "PORT": "PORT",
                "HOST": "0.0.0.0",
                "BUDDY_ENV": "production"
            }
        ),
        
        "heroku": EnvironmentConfig(
            name="Heroku",
            host="0.0.0.0", 
            external_url=lambda: f"https://{os.getenv('HEROKU_APP_NAME', 'buddy')}.herokuapp.com",
            features={
                "auto_ssl": True,
                "dyno_sleep": True,
                "add_ons": True,
                "health_checks": True
            },
            env_vars={
                "PORT": "PORT",
                "HOST": "0.0.0.0",
                "BUDDY_ENV": "production"
            }
        ),
        
        "railway": EnvironmentConfig(
            name="Railway",
            host="0.0.0.0",
            external_url=lambda: os.getenv("RAILWAY_STATIC_URL"),
            features={
                "auto_ssl": True,
                "volumes": True,
                "edge_locations": True,
                "health_checks": True
            },
            env_vars={
                "PORT": "PORT",
                "HOST": "0.0.0.0", 
                "BUDDY_ENV": "production"
            }
        ),
        
        "fly": EnvironmentConfig(
            name="Fly.io",
            host="0.0.0.0",
            external_url=lambda: f"https://{os.getenv('FLY_APP_NAME', 'buddy')}.fly.dev",
            features={
                "auto_ssl": True,
                "edge_locations": True,
                "volumes": True,
                "health_checks": True
            },
            env_vars={
                "PORT": "PORT",
                "HOST": "0.0.0.0",
                "BUDDY_ENV": "production"
            }
        ),
        
        "vercel": EnvironmentConfig(
            name="Vercel",
            host="0.0.0.0",
            external_url=lambda: os.getenv("VERCEL_URL"),
            features={
                "serverless": True,
                "auto_ssl": True,
                "edge_functions": True,
                "static_files": True
            },
            env_vars={
                "PORT": "PORT",
                "HOST": "0.0.0.0",
                "BUDDY_ENV": "production"
            }
        ),
        
        "netlify": EnvironmentConfig(
            name="Netlify",
            host="0.0.0.0",
            external_url=lambda: os.getenv("DEPLOY_PRIME_URL"),
            features={
                "serverless": True,
                "auto_ssl": True,
                "edge_functions": True,
                "static_files": True
            },
            env_vars={
                "PORT": "PORT", 
                "HOST": "0.0.0.0",
                "BUDDY_ENV": "production"
            }
        ),
        
        "docker": EnvironmentConfig(
            name="Docker",
            host="0.0.0.0",
            port=8000,
            features={
                "containers": True,
                "volumes": True,
                "networking": True,
                "health_checks": True
            },
            env_vars={
                "HOST": "0.0.0.0",
                "BUDDY_ENV": "container"
            }
        ),
        
        "kubernetes": EnvironmentConfig(
            name="Kubernetes",
            host="0.0.0.0",
            port=8000,
            features={
                "auto_scaling": True,
                "load_balancing": True,
                "service_discovery": True,
                "health_checks": True,
                "config_maps": True
            },
            env_vars={
                "HOST": "0.0.0.0",
                "BUDDY_ENV": "k8s"
            }
        ),
        
        "local": EnvironmentConfig(
            name="Local Development",
            host="127.0.0.1",
            port=8082,
            external_url=lambda: "http://localhost:8082",
            features={
                "hot_reload": True,
                "debug_mode": True,
                "file_watching": True
            },
            env_vars={
                "BUDDY_ENV": "development"
            }
        )
    }
    
    @classmethod
    def get_config(cls, environment: str) -> Optional[EnvironmentConfig]:
        """Get configuration for specific environment"""
        config = cls.ENVIRONMENT_CONFIGS.get(environment)
        if config and callable(config.external_url):
            config.external_url = config.external_url()
        return config
    
    @classmethod
    def configure_environment(cls, environment: str) -> Dict[str, Any]:
        """Configure environment variables and settings"""
        config = cls.get_config(environment)
        if not config:
            return {}
        
        # Set environment variables
        for key, value in config.env_vars.items():
            if key not in os.environ:
                os.environ[key] = value
        
        return asdict(config)
    
    @classmethod
    def get_deployment_guide(cls, environment: str) -> str:
        """Get deployment guide for specific environment"""
        guides = {
            "render": """
🚀 Deploying BUDDY to Render.com

1. Create a new Web Service
2. Connect your GitHub repository  
3. Set build command: pip install -r requirements.txt
4. Set start command: python cloud_backend.py
5. Add environment variables:
   - BUDDY_ENV=production
   - Add your API keys (OpenAI, etc.)
6. Deploy!

✅ BUDDY will automatically use Render's assigned PORT
🌐 Access via your .onrender.com URL
            """,
            
            "heroku": """
🚀 Deploying BUDDY to Heroku

1. Create a new Heroku app
2. Connect to GitHub or use Heroku CLI
3. Add Procfile: web: python cloud_backend.py
4. Set environment variables:
   - BUDDY_ENV=production  
   - Add your API keys (OpenAI, etc.)
5. Deploy!

✅ BUDDY will automatically use Heroku's $PORT
🌐 Access via your .herokuapp.com URL
            """,
            
            "railway": """
🚀 Deploying BUDDY to Railway

1. Create a new Railway project
2. Connect your GitHub repository
3. Railway auto-detects Python and dependencies
4. Set environment variables:
   - BUDDY_ENV=production
   - Add your API keys (OpenAI, etc.)
5. Deploy!

✅ BUDDY will automatically use Railway's assigned PORT  
🌐 Access via your Railway-assigned URL
            """,
            
            "docker": """
🚀 Running BUDDY with Docker

1. Create Dockerfile:
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 8000
   CMD ["python", "cloud_backend.py"]

2. Build and run:
   docker build -t buddy .
   docker run -p 8000:8000 -e BUDDY_ENV=container buddy

✅ BUDDY will bind to 0.0.0.0:8000
🌐 Access via http://localhost:8000
            """,
            
            "local": """
🚀 Running BUDDY Locally

1. Install dependencies:
   pip install -r requirements.txt

2. Run BUDDY:
   python simple_buddy.py          # Simple backend
   python cloud_backend.py         # Cloud backend  
   python universal_launcher.py    # Universal launcher

✅ BUDDY will auto-find available port
🌐 Check console output for URLs
            """
        }
        
        return guides.get(environment, f"No deployment guide available for {environment}")
    
    @classmethod
    def print_environment_info(cls, environment: str):
        """Print comprehensive environment information"""
        config = cls.get_config(environment)
        if not config:
            print(f"❌ Unknown environment: {environment}")
            return
        
        print(f"🌍 Environment: {config.name}")
        print("=" * 50)
        print(f"📡 Host: {config.host}")
        print(f"🎯 Port: {config.port or 'Auto-assigned'}")
        print(f"🌐 External URL: {config.external_url or 'Auto-generated'}")
        
        print(f"\n✨ Features:")
        for feature, enabled in config.features.items():
            status = "✅" if enabled else "❌"
            print(f"   {status} {feature.replace('_', ' ').title()}")
        
        print(f"\n🔧 Environment Variables:")
        for key, value in config.env_vars.items():
            print(f"   {key}={value}")
        
        print(f"\n{cls.get_deployment_guide(environment)}")

def auto_configure_buddy():
    """Auto-configure BUDDY based on detected environment"""
    from buddy_core.utils.universal_port_manager import get_environment
    
    env = get_environment()
    config = BuddyEnvironmentConfigurator.configure_environment(env)
    
    print(f"🔧 Auto-configured for {env} environment")
    return config

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        env = sys.argv[1]
        BuddyEnvironmentConfigurator.print_environment_info(env)
    else:
        print("🌍 BUDDY Environment Configurator")
        print("=" * 40)
        print("Available environments:")
        for env_name in BuddyEnvironmentConfigurator.ENVIRONMENT_CONFIGS.keys():
            print(f"   • {env_name}")
        print(f"\nUsage: python environment_config.py <environment>")
        print(f"Example: python environment_config.py render")
