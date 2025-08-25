"""
BUDDY Cross-Platform Database Layer

Supports:
- Local databases (SQLite, Realm)
- Cloud synchronization (MongoDB Atlas)
- Vector storage (ChromaDB/Pinecone)
- Offline-first with sync when online
- Cross-platform compatibility
- End-to-end encryption
"""

from .local_db import LocalDatabase
from .cloud_db import CloudDatabase
from .vector_db import VectorDatabase
from .sync_manager import SyncManager
from .encryption import EncryptionManager

__all__ = [
    'LocalDatabase',
    'CloudDatabase', 
    'VectorDatabase',
    'SyncManager',
    'EncryptionManager'
]
