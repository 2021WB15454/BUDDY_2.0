"""
BUDDY Environment Configuration Loader

Loads and validates environment variables for BUDDY configuration.
Supports .env files and provides defaults for development.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class BuddyEnvironment:
    """
    Environment configuration manager for BUDDY.
    
    Loads configuration from environment variables and .env files,
    provides validation and defaults for different deployment environments.
    """
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize environment configuration.
        
        Args:
            env_file: Optional path to .env file to load
        """
        self.loaded_files = []
        
        # Try to load dotenv if available
        self._load_dotenv(env_file)
        
        # Get current environment
        self.environment = self.get('BUDDY_ENV', 'development')
        self.debug = self.get_bool('BUDDY_DEBUG', self.environment == 'development')
        
        logger.info(f"BUDDY Environment: {self.environment} (debug: {self.debug})")
    
    def _load_dotenv(self, env_file: Optional[Path] = None):
        """Load environment variables from .env file."""
        try:
            from dotenv import load_dotenv
            
            # Priority order for .env files
            env_files = []
            
            if env_file and env_file.exists():
                env_files.append(env_file)
            
            # Look for environment-specific files
            project_root = Path(__file__).parent.parent.parent.parent
            env_files.extend([
                project_root / f'.env.{os.getenv("BUDDY_ENV", "development")}',
                project_root / '.env.local',
                project_root / '.env',
                Path('.env'),
                Path('config/.env')
            ])
            
            for env_path in env_files:
                if env_path.exists():
                    load_dotenv(env_path, override=False)  # Don't override existing vars
                    self.loaded_files.append(str(env_path))
                    logger.info(f"Loaded environment from: {env_path}")
            
            if not self.loaded_files:
                logger.info("No .env files found, using system environment only")
                
        except ImportError:
            logger.warning("python-dotenv not available, using system environment only")
    
    def get(self, key: str, default: Any = None) -> str:
        """Get environment variable as string."""
        return os.getenv(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get environment variable as boolean."""
        value = os.getenv(key, '').lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get environment variable as integer."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get environment variable as float."""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default
    
    def get_list(self, key: str, default: list = None, separator: str = ',') -> list:
        """Get environment variable as list (comma-separated by default)."""
        if default is None:
            default = []
        
        value = os.getenv(key, '')
        if not value:
            return default
        
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    def require(self, key: str) -> str:
        """Get required environment variable (raises error if not found)."""
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration from environment."""
        config = {
            'use_atlas': self.get_bool('MONGODB_USE_ATLAS', self.environment in ['atlas', 'production']),
            'connection_string': self.get('MONGODB_CONNECTION_STRING'),
            'host': self.get('MONGODB_HOST', 'localhost'),
            'port': self.get_int('MONGODB_PORT', 27017),
            'database': self.get('MONGODB_DATABASE', 'buddy_ai'),
            'username': self.get('MONGODB_USERNAME'),
            'password': self.get('MONGODB_PASSWORD'),
            'auth_source': self.get('MONGODB_AUTH_SOURCE', 'admin'),
            'connection_pool_size': self.get_int('MONGODB_CONNECTION_POOL_SIZE', 10),
            'timeout_ms': self.get_int('MONGODB_TIMEOUT_MS', 10000),
        }
        
        # Environment-specific defaults
        if self.environment == 'development':
            config.setdefault('database', 'buddy_ai_dev')
        elif self.environment == 'production':
            config.setdefault('database', 'buddy_production')
        
        return config
    
    def get_pinecone_config(self) -> Dict[str, Any]:
        """Get Pinecone configuration from environment."""
        return {
            'api_key': self.get('PINECONE_API_KEY'),
            'environment': self.get('PINECONE_ENVIRONMENT', 'us-west1-gcp'),
            'index_name': self.get('PINECONE_INDEX_NAME', f'buddy-memory-{self.environment}'),
            'dimension': self.get_int('PINECONE_DIMENSION', 384),
            'metric': self.get('PINECONE_METRIC', 'cosine'),
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API server configuration from environment."""
        return {
            'host': self.get('API_HOST', '0.0.0.0'),
            'port': self.get_int('API_PORT', 8081),
            'cors_enabled': self.get_bool('API_CORS_ENABLED', self.environment == 'development'),
            'rate_limit_enabled': self.get_bool('API_RATE_LIMIT_ENABLED', True),
            'rate_limit_requests_per_minute': self.get_int('API_RATE_LIMIT_REQUESTS_PER_MINUTE', 100),
            'authentication_enabled': self.get_bool('API_AUTHENTICATION_ENABLED', self.environment == 'production'),
            'jwt_secret': self.get('BUDDY_JWT_SECRET', 'dev-secret-key' if self.environment == 'development' else None),
        }
    
    def get_external_apis_config(self) -> Dict[str, Any]:
        """Get external API configuration from environment."""
        return {
            'weather_api_key': self.get('WEATHER_API_KEY'),
            'openai_api_key': self.get('OPENAI_API_KEY'),
            'google_api_key': self.get('GOOGLE_API_KEY'),
        }
    
    def validate_required_config(self) -> Dict[str, Any]:
        """
        Validate that all required configuration is present.
        
        Returns:
            Dict with validation results
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check database configuration
        db_config = self.get_database_config()
        if db_config['use_atlas'] and not db_config['connection_string']:
            validation['errors'].append("MongoDB Atlas enabled but MONGODB_CONNECTION_STRING not set")
        
        # Check Pinecone configuration
        pinecone_config = self.get_pinecone_config()
        if not pinecone_config['api_key']:
            validation['warnings'].append("PINECONE_API_KEY not set - memory features will be disabled")
        
        # Check production security
        if self.environment == 'production':
            api_config = self.get_api_config()
            if api_config['jwt_secret'] in [None, 'dev-secret-key']:
                validation['errors'].append("Production environment requires secure BUDDY_JWT_SECRET")
            
            if not api_config['authentication_enabled']:
                validation['warnings'].append("Authentication disabled in production environment")
        
        # Check external APIs
        external_config = self.get_external_apis_config()
        if not external_config['weather_api_key']:
            validation['warnings'].append("WEATHER_API_KEY not set - weather features will be disabled")
        
        validation['valid'] = len(validation['errors']) == 0
        return validation
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get complete configuration dictionary."""
        return {
            'environment': self.environment,
            'debug': self.debug,
            'device_id': self.get('BUDDY_DEVICE_ID'),
            'cloud_enabled': self.get_bool('BUDDY_CLOUD_ENABLED', True),
            'vector_db_provider': self.get('BUDDY_VECTOR_DB', 'pinecone'),
            'database': self.get_database_config(),
            'pinecone': self.get_pinecone_config(),
            'api': self.get_api_config(),
            'external_apis': self.get_external_apis_config(),
            'logging': {
                'level': self.get('LOG_LEVEL', 'INFO'),
                'file': self.get('LOG_FILE'),
            },
            'development': {
                'dev_mode': self.get_bool('DEV_MODE', self.environment == 'development'),
                'hot_reload': self.get_bool('HOT_RELOAD', self.environment == 'development'),
            }
        }
    
    def print_config_summary(self):
        """Print a summary of the current configuration."""
        print(f"\n{'='*50}")
        print(f"BUDDY Environment Configuration")
        print(f"{'='*50}")
        print(f"Environment: {self.environment}")
        print(f"Debug Mode: {self.debug}")
        print(f"Loaded .env files: {', '.join(self.loaded_files) if self.loaded_files else 'None'}")
        
        # Validate configuration
        validation = self.validate_required_config()
        
        if validation['errors']:
            print(f"\n❌ Configuration Errors:")
            for error in validation['errors']:
                print(f"  - {error}")
        
        if validation['warnings']:
            print(f"\n⚠️  Configuration Warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        if validation['valid'] and not validation['warnings']:
            print(f"\n✅ Configuration Valid")
        
        print(f"{'='*50}\n")

# Global environment instance
env = BuddyEnvironment()

# Convenience functions
def get_env(key: str, default: Any = None) -> str:
    """Get environment variable (convenience function)."""
    return env.get(key, default)

def get_config() -> Dict[str, Any]:
    """Get complete configuration (convenience function)."""
    return env.get_all_config()

def validate_config() -> Dict[str, Any]:
    """Validate configuration (convenience function)."""
    return env.validate_required_config()
