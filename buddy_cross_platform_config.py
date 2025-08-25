"""
BUDDY Cross-Platform Configuration

This file contains configuration settings for all platforms and database layers.
Supports development, staging, and production environments.
"""

import os
from typing import Dict, Any

# Environment detection
ENVIRONMENT = os.getenv("BUDDY_ENV", "development")
DEBUG = os.getenv("BUDDY_DEBUG", "false").lower() == "true"

class CrossPlatformConfig:
    """Configuration for BUDDY's cross-platform architecture"""
    
    @staticmethod
    def get_config(platform: str = "desktop") -> Dict[str, Any]:
        """Get platform-specific configuration"""
        
        base_config = {
            # Core settings
            "environment": ENVIRONMENT,
            "debug": DEBUG,
            "device_id": os.getenv("BUDDY_DEVICE_ID"),
            
            # Database configuration
            "database": {
                "local_db": {
                    "enabled": True,
                    "path": None,  # Will be set per platform
                    "max_size_mb": 100,
                    "backup_enabled": True
                },
                
                "cloud_db": {
                    "enabled": os.getenv("BUDDY_CLOUD_ENABLED", "true").lower() == "true",
                    "provider": "mongodb",
                    "connection_string": os.getenv("MONGODB_CONNECTION_STRING"),
                    "database_name": "buddy_cloud_" + ENVIRONMENT,
                    "timeout": 30,
                    "retry_attempts": 3
                },
                
                "vector_db": {
                    "enabled": True,
                    "provider": os.getenv("BUDDY_VECTOR_DB", "chroma"),  # chroma, pinecone
                    "dimension": 384,
                    "persist_directory": "./chroma_db",
                    "collection_name": "buddy_context",
                    # Pinecone config (if using Pinecone)
                    "pinecone": {
                        "api_key": os.getenv("PINECONE_API_KEY"),
                        "environment": os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp"),
                        "index_name": "buddy-context-" + ENVIRONMENT
                    }
                },
                
                "sync": {
                    "enabled": True,
                    "interval_seconds": 300,  # 5 minutes
                    "batch_size": 100,
                    "conflict_resolution": "last_writer_wins",  # last_writer_wins, merge_changes, user_choice
                    "retry_delay": 60,
                    "max_retries": 5
                },
                
                "encryption": {
                    "enabled": True,
                    "backend": "cryptography",  # cryptography, pycrypto, basic
                    "key_rotation_days": 90,
                    "require_password": False  # Set to True for production
                }
            },
            
            # API Gateway settings
            "api": {
                "host": "0.0.0.0",
                "port": 8082,
                "cors_enabled": True,
                "rate_limiting": {
                    "enabled": True,
                    "requests_per_minute": 100
                },
                "authentication": {
                    "enabled": False,  # Set to True for production
                    "jwt_secret": os.getenv("BUDDY_JWT_SECRET", "dev-secret-key"),
                    "token_expiry_hours": 24
                }
            },
            
            # Voice settings
            "voice": {
                "enabled": True,
                "asr": {
                    "provider": "system",  # system, whisper, google, azure
                    "language": "en-US",
                    "confidence_threshold": 0.7
                },
                "tts": {
                    "provider": "system",  # system, pyttsx3, google, azure, elevenlabs
                    "voice": "default",
                    "speed": 1.0,
                    "volume": 0.8
                },
                "wake_word": {
                    "enabled": False,  # Enable for always-listening
                    "phrase": "Hey BUDDY",
                    "sensitivity": 0.5
                }
            },
            
            # Platform integrations
            "integrations": {
                "calendar": {
                    "enabled": True,
                    "providers": ["system", "google", "outlook"]
                },
                "contacts": {
                    "enabled": True,
                    "sync_enabled": True
                },
                "location": {
                    "enabled": True,
                    "precision": "city"  # exact, city, country
                },
                "notifications": {
                    "enabled": True,
                    "push_enabled": True
                }
            }
        }
        
        # Platform-specific overrides
        platform_configs = {
            "ios": {
                "database": {
                    "local_db": {
                        "path": "~/Documents/buddy_local.db"
                    }
                },
                "integrations": {
                    "siri": {"enabled": True},
                    "shortcuts": {"enabled": True},
                    "healthkit": {"enabled": True}
                }
            },
            
            "android": {
                "database": {
                    "local_db": {
                        "path": "/data/data/com.buddy.ai/databases/buddy_local.db"
                    }
                },
                "integrations": {
                    "google_assistant": {"enabled": True},
                    "android_auto": {"enabled": True},
                    "google_fit": {"enabled": True}
                }
            },
            
            "windows": {
                "database": {
                    "local_db": {
                        "path": "~/AppData/Local/BUDDY/buddy_local.db"
                    }
                },
                "integrations": {
                    "cortana": {"enabled": False},
                    "windows_hello": {"enabled": True},
                    "timeline": {"enabled": True}
                }
            },
            
            "macos": {
                "database": {
                    "local_db": {
                        "path": "~/Library/Application Support/BUDDY/buddy_local.db"
                    }
                },
                "integrations": {
                    "siri": {"enabled": True},
                    "shortcuts": {"enabled": True},
                    "spotlight": {"enabled": True}
                }
            },
            
            "linux": {
                "database": {
                    "local_db": {
                        "path": "~/.local/share/buddy/buddy_local.db"
                    }
                },
                "integrations": {
                    "dbus": {"enabled": True},
                    "systemd": {"enabled": True}
                }
            },
            
            "watchos": {
                "database": {
                    "local_db": {
                        "path": "~/Documents/buddy_watch.db",
                        "max_size_mb": 10  # Smaller for watch
                    }
                },
                "voice": {
                    "tts": {"enabled": False},  # Haptic feedback preferred
                    "asr": {"enabled": True}
                },
                "integrations": {
                    "healthkit": {"enabled": True},
                    "workout": {"enabled": True},
                    "complications": {"enabled": True}
                }
            },
            
            "wearos": {
                "database": {
                    "local_db": {
                        "max_size_mb": 10
                    }
                },
                "integrations": {
                    "google_fit": {"enabled": True},
                    "tiles": {"enabled": True}
                }
            },
            
            "tvos": {
                "database": {
                    "local_db": {
                        "max_size_mb": 500  # Larger for content caching
                    }
                },
                "integrations": {
                    "homekit": {"enabled": True},
                    "siri_remote": {"enabled": True},
                    "airplay": {"enabled": True}
                }
            },
            
            "androidtv": {
                "database": {
                    "local_db": {
                        "max_size_mb": 500
                    }
                },
                "integrations": {
                    "google_assistant": {"enabled": True},
                    "chromecast": {"enabled": True}
                }
            },
            
            "carplay": {
                "database": {
                    "local_db": {
                        "max_size_mb": 50
                    }
                },
                "voice": {
                    "wake_word": {"enabled": False},  # Use car button
                    "asr": {"enabled": True}
                },
                "integrations": {
                    "maps": {"enabled": True},
                    "siri": {"enabled": True},
                    "carplay": {"enabled": True}
                }
            },
            
            "androidauto": {
                "database": {
                    "local_db": {
                        "max_size_mb": 50
                    }
                },
                "integrations": {
                    "google_assistant": {"enabled": True},
                    "android_auto": {"enabled": True},
                    "google_maps": {"enabled": True}
                }
            }
        }
        
        # Merge platform-specific config
        if platform in platform_configs:
            config = {**base_config}
            platform_config = platform_configs[platform]
            
            # Deep merge dictionaries
            for key, value in platform_config.items():
                if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                    config[key] = {**config[key], **value}
                else:
                    config[key] = value
            
            return config
        
        return base_config
    
    @staticmethod
    def get_database_dependencies() -> Dict[str, str]:
        """Get required Python packages for database functionality"""
        return {
            # Core database packages
            "sqlite3": "built-in",
            
            # Optional cloud database packages
            "pymongo": ">=4.0.0",
            "motor": ">=3.0.0",  # Async MongoDB driver
            
            # Optional vector database packages
            "chromadb": ">=0.4.0",
            "pinecone-client": ">=2.0.0",
            "sentence-transformers": ">=2.0.0",
            
            # Optional encryption packages
            "cryptography": ">=40.0.0",
            "pycryptodome": ">=3.18.0",
            
            # Sync and networking
            "aiohttp": ">=3.8.0",
            "websockets": ">=11.0.0",
            "pydantic": ">=2.0.0",
            "PyJWT": ">=2.0.0"
        }
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration and return status"""
        validation = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check required settings
        if not config.get("device_id"):
            validation["warnings"].append("Device ID not set - will generate random ID")
        
        # Check cloud database
        if config["database"]["cloud_db"]["enabled"]:
            if not config["database"]["cloud_db"]["connection_string"]:
                validation["errors"].append("Cloud database enabled but no connection string provided")
        
        # Check vector database
        vector_config = config["database"]["vector_db"]
        if vector_config["enabled"]:
            if vector_config["provider"] == "pinecone":
                if not vector_config["pinecone"]["api_key"]:
                    validation["errors"].append("Pinecone selected but no API key provided")
        
        # Check encryption
        if config["database"]["encryption"]["enabled"]:
            encryption_config = config["database"]["encryption"]
            if encryption_config["require_password"] and ENVIRONMENT == "production":
                validation["warnings"].append("Password-based encryption required in production")
        
        # Set valid flag
        validation["valid"] = len(validation["errors"]) == 0
        
        return validation

# Development shortcuts
def get_development_config(platform: str = "desktop") -> Dict[str, Any]:
    """Get development-optimized configuration"""
    config = CrossPlatformConfig.get_config(platform)
    
    # Development overrides
    config["database"]["cloud_db"]["enabled"] = False  # Use local only
    config["database"]["encryption"]["enabled"] = False  # Disable for easier debugging
    config["api"]["authentication"]["enabled"] = False  # No auth in dev
    config["database"]["sync"]["interval_seconds"] = 60  # Faster sync for testing
    
    return config

def get_production_config(platform: str = "desktop") -> Dict[str, Any]:
    """Get production-optimized configuration"""
    config = CrossPlatformConfig.get_config(platform)
    
    # Production overrides
    config["debug"] = False
    config["database"]["encryption"]["enabled"] = True
    config["database"]["encryption"]["require_password"] = True
    config["api"]["authentication"]["enabled"] = True
    config["api"]["rate_limiting"]["enabled"] = True
    
    return config
