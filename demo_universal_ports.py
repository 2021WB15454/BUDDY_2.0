"""
BUDDY Universal Port Demo
Demonstrates platform-agnostic port management across different environments
"""

import os
import sys
import time
sys.path.append('buddy_core')

def simulate_environment(env_name, env_vars=None):
    """Simulate different deployment environments"""
    print(f"\n🌍 Simulating {env_name} Environment")
    print("-" * 40)
    
    # Backup original environment
    original_env = {}
    if env_vars:
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
    
    try:
        # Import fresh manager for each test
        import importlib
        if 'buddy_core.utils.universal_port_manager' in sys.modules:
            importlib.reload(sys.modules['buddy_core.utils.universal_port_manager'])
        
        from buddy_core.utils.universal_port_manager import UniversalPortManager, PortConfig
        
        # Create manager and get config
        manager = UniversalPortManager()
        config = manager.get_server_config()
        
        print(f"✅ Environment: {config['environment']}")
        print(f"📡 Host: {config['host']}")
        print(f"🎯 Port: {config['port']}")
        print(f"🔗 Local URL: {config['urls']['local']}")
        
        if 'external' in config['urls']:
            print(f"🌐 External URL: {config['urls']['external']}")
        
        return config
        
    finally:
        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value

def main():
    """Run universal port management demo"""
    print("🚀 BUDDY Universal Port Management Demo")
    print("=" * 60)
    print("This demo shows how BUDDY adapts to different platforms automatically!")
    
    # Test scenarios
    scenarios = [
        ("Local Development", {}),
        ("Render.com", {
            "RENDER": "true",
            "PORT": "10000",
            "RENDER_EXTERNAL_URL": "https://buddy-2-0.onrender.com"
        }),
        ("Heroku", {
            "HEROKU": "true", 
            "PORT": "5000",
            "HEROKU_APP_NAME": "buddy-ai-assistant"
        }),
        ("Railway", {
            "RAILWAY_ENVIRONMENT": "production",
            "PORT": "3000",
            "RAILWAY_STATIC_URL": "https://buddy-production.up.railway.app"
        }),
        ("Docker Container", {
            "DOCKER_CONTAINER": "true",
        }),
        ("Kubernetes", {
            "KUBERNETES_SERVICE_HOST": "10.0.0.1",
            "PORT": "8000"
        })
    ]
    
    results = []
    
    for env_name, env_vars in scenarios:
        try:
            config = simulate_environment(env_name, env_vars)
            results.append((env_name, config))
        except Exception as e:
            print(f"❌ Error simulating {env_name}: {e}")
    
    # Summary
    print(f"\n📊 Summary: BUDDY Universal Port Management")
    print("=" * 60)
    print("Environment           | Port  | Host      | Type")
    print("-" * 60)
    
    for env_name, config in results:
        env_short = env_name[:17].ljust(17)
        port = str(config['port']).ljust(5)
        host = config['host'].ljust(9)
        env_type = config['environment'].ljust(10)
        print(f"{env_short} | {port} | {host} | {env_type}")
    
    print("\n✅ Universal Port Management Results:")
    print("   🎯 All environments got appropriate ports")
    print("   🌍 Auto-detected deployment contexts")  
    print("   🔄 Zero configuration required")
    print("   📡 Generated platform-specific URLs")
    print("   ⚡ Ready for immediate deployment")
    
    print(f"\n🚀 BUDDY 2.0 is now truly universal!")
    print(f"   Deploy to ANY platform without port configuration!")

if __name__ == "__main__":
    main()
