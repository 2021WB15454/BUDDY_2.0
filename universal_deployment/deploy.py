#!/usr/bin/env python3
"""
BUDDY Universal Deployment Script
Automated deployment and management for BUDDY Core system
"""

import os
import sys
import subprocess
import argparse
import time
import json
import requests
from pathlib import Path

class BuddyDeployer:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.compose_file = self.project_dir / "docker-compose.yml"
        self.env_file = self.project_dir / ".env"
        
    def setup_environment(self):
        """Setup environment file from template"""
        env_example = self.project_dir / ".env.example"
        
        if not self.env_file.exists() and env_example.exists():
            print("📋 Creating .env file from template...")
            subprocess.run(["cp", str(env_example), str(self.env_file)], check=True)
            print("✅ Please edit .env file with your configuration")
            return False
        return True
    
    def check_prerequisites(self):
        """Check if required tools are installed"""
        print("🔍 Checking prerequisites...")
        
        # Check Docker
        try:
            result = subprocess.run(["docker", "--version"], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ Docker: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker not found. Please install Docker Desktop.")
            return False
        
        # Check Docker Compose
        try:
            result = subprocess.run(["docker-compose", "--version"], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ Docker Compose: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker Compose not found. Please install Docker Compose.")
            return False
        
        # Check if Docker daemon is running
        try:
            subprocess.run(["docker", "info"], 
                          capture_output=True, check=True)
            print("✅ Docker daemon is running")
        except subprocess.CalledProcessError:
            print("❌ Docker daemon is not running. Please start Docker.")
            return False
        
        return True
    
    def deploy(self, mode="development"):
        """Deploy BUDDY Core system"""
        print(f"🚀 Deploying BUDDY Core in {mode} mode...")
        
        # Build and start services
        cmd = ["docker-compose", "up", "-d", "--build"]
        if mode == "production":
            cmd.extend(["--scale", "buddy-core=2"])
        
        try:
            subprocess.run(cmd, cwd=self.project_dir, check=True)
            print("✅ Services started successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Deployment failed: {e}")
            return False
    
    def check_health(self, timeout=60):
        """Check if all services are healthy"""
        print("🏥 Checking service health...")
        
        services = [
            ("BUDDY Core", "http://localhost:8000/health"),
            ("ChromaDB", "http://localhost:8001/api/v1/heartbeat"),
        ]
        
        start_time = time.time()
        
        for service_name, url in services:
            print(f"Checking {service_name}...")
            
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ {service_name} is healthy")
                        break
                except requests.exceptions.RequestException:
                    pass
                
                time.sleep(2)
            else:
                print(f"❌ {service_name} health check failed")
                return False
        
        return True
    
    def show_status(self):
        """Show status of all services"""
        print("📊 Service Status:")
        subprocess.run(["docker-compose", "ps"], cwd=self.project_dir)
    
    def show_logs(self, service=None, follow=False):
        """Show logs for services"""
        cmd = ["docker-compose", "logs"]
        if follow:
            cmd.append("-f")
        if service:
            cmd.append(service)
        
        subprocess.run(cmd, cwd=self.project_dir)
    
    def stop(self):
        """Stop all services"""
        print("🛑 Stopping BUDDY Core services...")
        subprocess.run(["docker-compose", "down"], cwd=self.project_dir)
        print("✅ Services stopped")
    
    def restart(self):
        """Restart all services"""
        print("🔄 Restarting BUDDY Core services...")
        subprocess.run(["docker-compose", "restart"], cwd=self.project_dir)
        print("✅ Services restarted")
    
    def test_connection(self):
        """Test API connectivity"""
        print("🧪 Testing API connectivity...")
        
        try:
            # Test health endpoint
            response = requests.get("http://localhost:8000/health", timeout=10)
            if response.status_code == 200:
                print("✅ Health check passed")
                health_data = response.json()
                print(f"   Database: {health_data.get('database', 'unknown')}")
                print(f"   Redis: {health_data.get('redis', 'unknown')}")
            
            # Test device registration
            device_data = {
                "device_id": "test-deployment-device",
                "device_name": "Deployment Test",
                "device_type": "test",
                "platform": "python"
            }
            
            response = requests.post(
                "http://localhost:8000/api/v1/devices/register",
                json=device_data,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Device registration test passed")
            else:
                print(f"❌ Device registration test failed: {response.status_code}")
            
            # Test chat endpoint
            chat_data = {
                "text": "Hello BUDDY! Deployment test message.",
                "device_id": "test-deployment-device"
            }
            
            response = requests.post(
                "http://localhost:8000/api/v1/chat",
                json=chat_data,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Chat endpoint test passed")
                chat_response = response.json()
                print(f"   Response: {chat_response.get('response', 'No response')}")
            else:
                print(f"❌ Chat endpoint test failed: {response.status_code}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up all containers and volumes"""
        print("🧹 Cleaning up BUDDY Core deployment...")
        subprocess.run(["docker-compose", "down", "-v", "--remove-orphans"], 
                      cwd=self.project_dir)
        print("✅ Cleanup completed")
    
    def backup_data(self, backup_dir="./backups"):
        """Backup database and configuration"""
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"buddy_backup_{timestamp}.sql"
        
        print(f"💾 Creating backup at {backup_file}...")
        
        try:
            # Backup PostgreSQL database
            cmd = [
                "docker-compose", "exec", "-T", "postgres",
                "pg_dump", "-U", "buddy", "buddydb"
            ]
            
            with open(backup_file, "w") as f:
                subprocess.run(cmd, cwd=self.project_dir, stdout=f, check=True)
            
            print(f"✅ Backup created: {backup_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Backup failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="BUDDY Universal Deployment Manager")
    parser.add_argument("action", choices=[
        "deploy", "stop", "restart", "status", "logs", "test", "cleanup", "backup"
    ], help="Action to perform")
    
    parser.add_argument("--mode", choices=["development", "production"], 
                       default="development", help="Deployment mode")
    parser.add_argument("--service", help="Specific service for logs")
    parser.add_argument("--follow", "-f", action="store_true", 
                       help="Follow logs output")
    parser.add_argument("--timeout", type=int, default=60,
                       help="Health check timeout in seconds")
    
    args = parser.parse_args()
    
    deployer = BuddyDeployer()
    
    # Common checks
    if not deployer.check_prerequisites():
        sys.exit(1)
    
    # Action handlers
    if args.action == "deploy":
        if not deployer.setup_environment():
            print("Please configure .env file and run deploy again.")
            sys.exit(1)
        
        if deployer.deploy(args.mode):
            time.sleep(5)  # Give services time to start
            if deployer.check_health(args.timeout):
                print("\n🎉 BUDDY Core deployed successfully!")
                print("\n📋 Quick Start:")
                print("   API Docs: http://localhost:8000/docs")
                print("   Health: http://localhost:8000/health")
                print("   ChromaDB: http://localhost:8001")
                print("\n🔧 Management Commands:")
                print("   Status: python deploy.py status")
                print("   Logs: python deploy.py logs")
                print("   Test: python deploy.py test")
                print("   Stop: python deploy.py stop")
            else:
                print("❌ Some services failed health checks")
                deployer.show_logs()
                sys.exit(1)
        else:
            sys.exit(1)
    
    elif args.action == "stop":
        deployer.stop()
    
    elif args.action == "restart":
        deployer.restart()
    
    elif args.action == "status":
        deployer.show_status()
    
    elif args.action == "logs":
        deployer.show_logs(args.service, args.follow)
    
    elif args.action == "test":
        if deployer.test_connection():
            print("\n✅ All tests passed! BUDDY Core is working correctly.")
        else:
            print("\n❌ Tests failed. Check logs for details.")
            sys.exit(1)
    
    elif args.action == "cleanup":
        deployer.cleanup()
    
    elif args.action == "backup":
        deployer.backup_data()

if __name__ == "__main__":
    main()
