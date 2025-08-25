#!/usr/bin/env python3
"""
BUDDY 2.0 Phase 2: Mobile Platform Implementation
Building on our optimized database foundation for complete cross-platform deployment

This implementation integrates our proven optimized database components
with a comprehensive mobile platform strategy.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Import our proven optimized components
from buddy_core.database.optimized_local_db import (
    OptimizedLocalDatabase, DeviceCapability, DatabaseConfig
)
from buddy_core.database.intelligent_sync import (
    IntelligentSyncScheduler, SyncPriority, NetworkQuality, DeviceConstraint
)
from buddy_core.database.performance_monitor import (
    DatabasePerformanceMonitor, QueryType, AlertLevel
)

logger = logging.getLogger(__name__)


class MobilePlatformType(Enum):
    """Mobile platform types supported by BUDDY"""
    IOS = "ios"
    ANDROID = "android"
    REACT_NATIVE = "react_native"
    FLUTTER = "flutter"
    PWA = "pwa"


class MobileDeviceProfile(Enum):
    """Mobile device performance profiles"""
    FLAGSHIP = "flagship"          # High-end devices (iPhone 15 Pro, Samsung S24 Ultra)
    PREMIUM = "premium"            # Premium devices (iPhone 14, Samsung S23)
    STANDARD = "standard"          # Standard devices (iPhone SE, mid-range Android)
    BUDGET = "budget"              # Budget devices (older iPhones, entry-level Android)
    TABLET = "tablet"              # Tablets (iPad, Android tablets)


@dataclass
class MobileConfiguration:
    """Mobile-specific configuration for BUDDY"""
    platform: MobilePlatformType
    device_profile: MobileDeviceProfile
    storage_limit_mb: int
    cache_limit_mb: int
    sync_batch_size: int
    background_sync_interval: int  # seconds
    voice_enabled: bool
    push_notifications: bool
    biometric_auth: bool
    offline_mode: bool
    data_saver_mode: bool
    
    @classmethod
    def for_device_profile(cls, platform: MobilePlatformType, profile: MobileDeviceProfile) -> 'MobileConfiguration':
        """Generate optimal configuration for device profile"""
        configs = {
            MobileDeviceProfile.FLAGSHIP: cls(
                platform=platform,
                device_profile=profile,
                storage_limit_mb=500,      # 500MB storage
                cache_limit_mb=64,         # 64MB cache
                sync_batch_size=100,       # Large batches
                background_sync_interval=30,  # 30 seconds
                voice_enabled=True,
                push_notifications=True,
                biometric_auth=True,
                offline_mode=True,
                data_saver_mode=False
            ),
            MobileDeviceProfile.PREMIUM: cls(
                platform=platform,
                device_profile=profile,
                storage_limit_mb=300,      # 300MB storage
                cache_limit_mb=32,         # 32MB cache
                sync_batch_size=75,        # Medium batches
                background_sync_interval=60,  # 1 minute
                voice_enabled=True,
                push_notifications=True,
                biometric_auth=True,
                offline_mode=True,
                data_saver_mode=False
            ),
            MobileDeviceProfile.STANDARD: cls(
                platform=platform,
                device_profile=profile,
                storage_limit_mb=150,      # 150MB storage
                cache_limit_mb=16,         # 16MB cache
                sync_batch_size=50,        # Medium batches
                background_sync_interval=120,  # 2 minutes
                voice_enabled=True,
                push_notifications=True,
                biometric_auth=False,
                offline_mode=True,
                data_saver_mode=True
            ),
            MobileDeviceProfile.BUDGET: cls(
                platform=platform,
                device_profile=profile,
                storage_limit_mb=75,       # 75MB storage
                cache_limit_mb=8,          # 8MB cache
                sync_batch_size=25,        # Small batches
                background_sync_interval=300,  # 5 minutes
                voice_enabled=False,       # Disable voice on budget devices
                push_notifications=True,
                biometric_auth=False,
                offline_mode=True,
                data_saver_mode=True
            ),
            MobileDeviceProfile.TABLET: cls(
                platform=platform,
                device_profile=profile,
                storage_limit_mb=800,      # 800MB storage
                cache_limit_mb=128,        # 128MB cache
                sync_batch_size=150,       # Large batches
                background_sync_interval=45,  # 45 seconds
                voice_enabled=True,
                push_notifications=True,
                biometric_auth=True,
                offline_mode=True,
                data_saver_mode=False
            )
        }
        return configs.get(profile, configs[MobileDeviceProfile.STANDARD])


class MobileBuddyCore:
    """
    Core BUDDY implementation for mobile platforms
    Integrates our proven optimized database with mobile-specific features
    """
    
    def __init__(self, user_id: str, device_id: str, mobile_config: MobileConfiguration):
        self.user_id = user_id
        self.device_id = device_id
        self.mobile_config = mobile_config
        
        # Map mobile profile to database capability
        self.db_capability = self._map_to_db_capability(mobile_config.device_profile)
        
        # Core components (using our proven implementations)
        self.optimized_db: Optional[OptimizedLocalDatabase] = None
        self.sync_scheduler: Optional[IntelligentSyncScheduler] = None
        self.performance_monitor: Optional[DatabasePerformanceMonitor] = None
        
        # Mobile-specific components
        self.voice_manager: Optional['MobileVoiceManager'] = None
        self.notification_manager: Optional['MobileNotificationManager'] = None
        self.offline_manager: Optional['MobileOfflineManager'] = None
        
        # State tracking
        self.is_initialized = False
        self.is_foreground = True
        self.network_available = True
        self.battery_optimized = False
        
        logger.info(f"MobileBuddyCore initialized for {mobile_config.platform.value} "
                   f"({mobile_config.device_profile.value} profile)")
    
    def _map_to_db_capability(self, profile: MobileDeviceProfile) -> DeviceCapability:
        """Map mobile device profile to database capability"""
        mapping = {
            MobileDeviceProfile.FLAGSHIP: DeviceCapability.HIGH_PERFORMANCE,
            MobileDeviceProfile.PREMIUM: DeviceCapability.MEDIUM_PERFORMANCE,
            MobileDeviceProfile.STANDARD: DeviceCapability.MEDIUM_PERFORMANCE,
            MobileDeviceProfile.BUDGET: DeviceCapability.LOW_PERFORMANCE,
            MobileDeviceProfile.TABLET: DeviceCapability.HIGH_PERFORMANCE
        }
        return mapping.get(profile, DeviceCapability.MEDIUM_PERFORMANCE)
    
    async def initialize(self) -> bool:
        """Initialize BUDDY mobile core with optimized components"""
        try:
            # 1. Initialize optimized database with mobile configuration
            db_config = DatabaseConfig.for_device_capability(self.db_capability)
            # Override with mobile-specific settings
            db_config.cache_size = self.mobile_config.cache_limit_mb * 1024  # Convert to KB
            db_config.batch_size = self.mobile_config.sync_batch_size
            
            self.optimized_db = OptimizedLocalDatabase(
                db_path=f"buddy_mobile_{self.user_id}.db",
                config=db_config
            )
            await self.optimized_db.initialize()
            logger.info("Optimized database initialized for mobile")
            
            # 2. Initialize sync scheduler with mobile constraints
            self.sync_scheduler = IntelligentSyncScheduler("mobile")
            await self.sync_scheduler.initialize()
            logger.info("Mobile sync scheduler initialized")
            
            # 3. Initialize performance monitor
            async def mobile_alert_callback(alert):
                await self._handle_performance_alert(alert)
            
            self.performance_monitor = DatabasePerformanceMonitor("mobile", mobile_alert_callback)
            await self.performance_monitor.start_monitoring()
            logger.info("Mobile performance monitor initialized")
            
            # 4. Initialize mobile-specific managers
            if self.mobile_config.voice_enabled:
                self.voice_manager = MobileVoiceManager(self.mobile_config.platform)
                await self.voice_manager.initialize()
            
            if self.mobile_config.push_notifications:
                self.notification_manager = MobileNotificationManager(self.mobile_config.platform)
                await self.notification_manager.initialize()
            
            if self.mobile_config.offline_mode:
                self.offline_manager = MobileOfflineManager(
                    self.optimized_db, 
                    self.sync_scheduler,
                    self.mobile_config
                )
                await self.offline_manager.initialize()
            
            # 5. Setup mobile lifecycle handlers
            await self._setup_mobile_lifecycle()
            
            self.is_initialized = True
            logger.info("BUDDY mobile core fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"Mobile core initialization failed: {e}")
            return False
    
    async def send_message(self, message: str, session_id: Optional[str] = None, 
                          voice_input: bool = False) -> Dict[str, Any]:
        """Send message with mobile optimizations"""
        if not self.is_initialized:
            raise RuntimeError("Mobile core not initialized")
        
        # Generate message data optimized for mobile
        message_data = {
            'user_input': message,
            'session_id': session_id or f"mobile_session_{int(time.time())}",
            'metadata': {
                'device_id': self.device_id,
                'device_type': 'mobile',
                'platform': self.mobile_config.platform.value,
                'device_profile': self.mobile_config.device_profile.value,
                'voice_input': voice_input,
                'network_available': self.network_available,
                'foreground': self.is_foreground,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Store locally first (offline-first approach)
        conversation_id = await self.performance_monitor.monitor_query(
            QueryType.CONVERSATION_INSERT,
            self.optimized_db.store_conversation_optimized,
            message_data
        )
        
        # Queue for sync with appropriate priority
        sync_priority = SyncPriority.REALTIME if voice_input else SyncPriority.HIGH
        await self.sync_scheduler.queue_sync_operation(
            {
                'type': 'conversation_sync',
                'conversation_id': conversation_id,
                'data': message_data
            },
            sync_priority
        )
        
        # Generate response (would integrate with AI backend)
        response = await self._generate_mobile_response(message, message_data)
        
        # Store response
        response_data = {
            'assistant_response': response['content'],
            'session_id': message_data['session_id'],
            'metadata': {
                **message_data['metadata'],
                'response_time': response['response_time'],
                'confidence': response.get('confidence', 0.8),
                'mobile_optimized': True
            }
        }
        
        response_id = await self.performance_monitor.monitor_query(
            QueryType.CONVERSATION_INSERT,
            self.optimized_db.store_conversation_optimized,
            response_data
        )
        
        # Queue response for sync
        await self.sync_scheduler.queue_sync_operation(
            {
                'type': 'conversation_sync',
                'conversation_id': response_id,
                'data': response_data
            },
            SyncPriority.HIGH
        )
        
        # Trigger notification if app is in background
        if not self.is_foreground and self.notification_manager:
            await self.notification_manager.send_response_notification(response['content'])
        
        return {
            'conversation_id': conversation_id,
            'response_id': response_id,
            'response': response['content'],
            'session_id': message_data['session_id'],
            'metadata': {
                'response_time': response['response_time'],
                'network_used': self.network_available,
                'cached_response': response.get('cached', False)
            }
        }
    
    async def get_conversation_history(self, session_id: Optional[str] = None, 
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history optimized for mobile display"""
        conversations = await self.performance_monitor.monitor_query(
            QueryType.CONVERSATION_SELECT,
            self.optimized_db.get_conversation_history_optimized,
            limit=limit
        )
        
        # Filter by session if specified
        if session_id:
            conversations = [
                conv for conv in conversations 
                if conv.get('session_id') == session_id
            ]
        
        # Add mobile-specific metadata
        for conv in conversations:
            conv['mobile_metadata'] = {
                'platform': self.mobile_config.platform.value,
                'can_read_aloud': self.mobile_config.voice_enabled and self.voice_manager,
                'offline_available': True,  # Already stored locally
                'sync_status': 'synced'  # Would check actual sync status
            }
        
        return conversations
    
    async def process_voice_input(self, audio_data: bytes) -> Dict[str, Any]:
        """Process voice input using mobile voice manager"""
        if not self.voice_manager:
            raise RuntimeError("Voice input not enabled")
        
        # Transcribe audio
        transcription = await self.voice_manager.transcribe_audio(audio_data)
        
        if transcription:
            # Send as voice message
            result = await self.send_message(transcription, voice_input=True)
            
            # Generate voice response if enabled
            if self.mobile_config.voice_enabled:
                await self.voice_manager.speak_response(result['response'])
            
            return {
                **result,
                'transcription': transcription,
                'voice_processing_time': self.voice_manager.last_processing_time
            }
        else:
            raise RuntimeError("Voice transcription failed")
    
    async def set_mobile_preference(self, key: str, value: Any, sync_immediately: bool = False):
        """Set mobile-specific preference"""
        await self.performance_monitor.monitor_query(
            QueryType.PREFERENCE_UPSERT,
            self.optimized_db.set_preference_optimized,
            key, value
        )
        
        if sync_immediately:
            await self.sync_scheduler.queue_sync_operation(
                {
                    'type': 'preference_sync',
                    'key': key,
                    'value': value
                },
                SyncPriority.HIGH
            )
    
    async def handle_app_state_change(self, is_foreground: bool):
        """Handle mobile app state changes"""
        self.is_foreground = is_foreground
        
        if is_foreground:
            # App came to foreground - trigger sync
            await self._trigger_foreground_sync()
        else:
            # App went to background - optimize for battery
            await self._optimize_for_background()
    
    async def handle_network_change(self, network_available: bool, network_type: str):
        """Handle network connectivity changes"""
        self.network_available = network_available
        
        # Update sync scheduler with network status
        network_quality = self._map_network_type_to_quality(network_type)
        await self.sync_scheduler.update_sync_context({
            'network_quality': network_quality,
            'device_constraints': self._get_current_constraints()
        })
        
        if network_available:
            # Network restored - process queued operations
            await self._process_offline_queue()
    
    async def handle_battery_change(self, battery_level: float, is_charging: bool):
        """Handle battery level changes"""
        # Adjust operation based on battery level
        if battery_level < 0.15 and not is_charging:  # Below 15%
            self.battery_optimized = True
            await self._enable_battery_optimization()
        elif battery_level > 0.30 or is_charging:  # Above 30% or charging
            self.battery_optimized = False
            await self._disable_battery_optimization()
    
    async def get_mobile_status(self) -> Dict[str, Any]:
        """Get comprehensive mobile status"""
        # Get performance metrics
        performance_metrics = await self.optimized_db.get_performance_metrics()
        
        # Get sync status
        sync_stats = await self.sync_scheduler.get_sync_statistics()
        
        # Get real-time monitoring data
        real_time_metrics = await self.performance_monitor.get_real_time_metrics()
        
        return {
            'platform': self.mobile_config.platform.value,
            'device_profile': self.mobile_config.device_profile.value,
            'is_foreground': self.is_foreground,
            'network_available': self.network_available,
            'battery_optimized': self.battery_optimized,
            'voice_enabled': self.mobile_config.voice_enabled,
            'offline_mode': self.mobile_config.offline_mode,
            'database_performance': performance_metrics,
            'sync_performance': sync_stats,
            'real_time_metrics': real_time_metrics,
            'storage_usage': {
                'used_mb': performance_metrics.get('storage_used_mb', 0),
                'limit_mb': self.mobile_config.storage_limit_mb,
                'percentage': min(100, (performance_metrics.get('storage_used_mb', 0) / self.mobile_config.storage_limit_mb) * 100)
            }
        }
    
    async def cleanup_mobile_data(self) -> Dict[str, Any]:
        """Cleanup mobile data based on storage limits"""
        cleanup_results = await self.optimized_db.cleanup_expired_data()
        
        # Additional mobile-specific cleanup
        if self.offline_manager:
            offline_cleanup = await self.offline_manager.cleanup_old_data()
            cleanup_results.update(offline_cleanup)
        
        return cleanup_results
    
    async def _generate_mobile_response(self, message: str, context: Dict) -> Dict[str, Any]:
        """Generate AI response optimized for mobile"""
        start_time = time.time()
        
        # This would integrate with actual AI backend
        # For now, return a mobile-optimized mock response
        response_content = f"I understand you said: '{message}'. Here's a mobile-optimized response."
        
        # Add mobile-specific optimizations
        if not self.network_available:
            response_content = "[Offline] " + response_content
        
        if self.mobile_config.data_saver_mode:
            # Shorter responses in data saver mode
            response_content = response_content[:100] + "..." if len(response_content) > 100 else response_content
        
        response_time = time.time() - start_time
        
        return {
            'content': response_content,
            'response_time': response_time,
            'confidence': 0.85,
            'mobile_optimized': True,
            'cached': not self.network_available
        }
    
    async def _handle_performance_alert(self, alert):
        """Handle performance alerts on mobile"""
        if alert.level == AlertLevel.CRITICAL:
            # Critical alert - take immediate action
            if 'memory' in alert.message.lower():
                await self._emergency_memory_cleanup()
            elif 'storage' in alert.message.lower():
                await self._emergency_storage_cleanup()
        
        # Log mobile-specific alert
        logger.warning(f"Mobile performance alert: {alert.message}")
    
    async def _setup_mobile_lifecycle(self):
        """Setup mobile app lifecycle monitoring"""
        # This would integrate with platform-specific lifecycle events
        logger.info("Mobile lifecycle monitoring setup")
    
    async def _trigger_foreground_sync(self):
        """Trigger sync when app comes to foreground"""
        if self.network_available:
            # Process pending sync operations
            await self.sync_scheduler.process_next_sync_batch(batch_size=10)
    
    async def _optimize_for_background(self):
        """Optimize operations for background mode"""
        # Reduce sync frequency
        await self.sync_scheduler.update_sync_context({
            'device_constraints': [DeviceConstraint.BATTERY, DeviceConstraint.PROCESSING]
        })
    
    def _map_network_type_to_quality(self, network_type: str) -> NetworkQuality:
        """Map mobile network type to sync network quality"""
        quality_map = {
            'wifi': NetworkQuality.EXCELLENT,
            '5g': NetworkQuality.EXCELLENT,
            '4g': NetworkQuality.GOOD,
            '3g': NetworkQuality.POOR,
            '2g': NetworkQuality.MINIMAL,
            'none': NetworkQuality.OFFLINE
        }
        return quality_map.get(network_type.lower(), NetworkQuality.POOR)
    
    def _get_current_constraints(self) -> List[DeviceConstraint]:
        """Get current device constraints"""
        constraints = []
        
        if self.battery_optimized:
            constraints.append(DeviceConstraint.BATTERY)
        
        if not self.is_foreground:
            constraints.append(DeviceConstraint.PROCESSING)
        
        if self.mobile_config.data_saver_mode:
            constraints.append(DeviceConstraint.MEMORY)
        
        return constraints
    
    async def _process_offline_queue(self):
        """Process queued operations when network becomes available"""
        if self.offline_manager:
            await self.offline_manager.process_offline_queue()
    
    async def _enable_battery_optimization(self):
        """Enable battery optimization mode"""
        # Reduce background sync frequency
        await self.sync_scheduler.update_sync_context({
            'device_constraints': [DeviceConstraint.BATTERY]
        })
        
        # Reduce performance monitoring frequency
        # This would be implemented in the performance monitor
        
        logger.info("Battery optimization enabled")
    
    async def _disable_battery_optimization(self):
        """Disable battery optimization mode"""
        await self.sync_scheduler.update_sync_context({
            'device_constraints': []
        })
        
        logger.info("Battery optimization disabled")
    
    async def _emergency_memory_cleanup(self):
        """Emergency memory cleanup for critical alerts"""
        # Clear caches
        if hasattr(self.optimized_db, 'clear_cache'):
            await self.optimized_db.clear_cache()
        
        # Run database cleanup
        await self.optimized_db.cleanup_expired_data()
        
        logger.warning("Emergency memory cleanup performed")
    
    async def _emergency_storage_cleanup(self):
        """Emergency storage cleanup for critical alerts"""
        # Run aggressive cleanup
        cleanup_result = await self.cleanup_mobile_data()
        
        logger.warning(f"Emergency storage cleanup performed: {cleanup_result}")
    
    async def close(self):
        """Cleanup mobile core"""
        try:
            # Final sync before closing
            if self.sync_scheduler and self.network_available:
                await self.sync_scheduler.process_next_sync_batch(batch_size=50)
            
            # Stop performance monitoring
            if self.performance_monitor:
                await self.performance_monitor.stop_monitoring()
            
            # Close database
            if self.optimized_db:
                await self.optimized_db.close()
            
            # Cleanup mobile managers
            if self.voice_manager:
                await self.voice_manager.close()
            
            if self.notification_manager:
                await self.notification_manager.close()
            
            if self.offline_manager:
                await self.offline_manager.close()
            
            logger.info("Mobile core closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing mobile core: {e}")


# Placeholder classes for mobile-specific managers
class MobileVoiceManager:
    """Mobile voice input/output manager"""
    
    def __init__(self, platform: MobilePlatformType):
        self.platform = platform
        self.last_processing_time = 0.0
    
    async def initialize(self):
        logger.info(f"Voice manager initialized for {self.platform.value}")
    
    async def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        # Mock transcription
        self.last_processing_time = 0.5  # 500ms processing time
        return "Transcribed voice input"
    
    async def speak_response(self, text: str):
        # Mock TTS
        logger.info(f"Speaking: {text[:50]}...")
    
    async def close(self):
        pass


class MobileNotificationManager:
    """Mobile push notification manager"""
    
    def __init__(self, platform: MobilePlatformType):
        self.platform = platform
    
    async def initialize(self):
        logger.info(f"Notification manager initialized for {self.platform.value}")
    
    async def send_response_notification(self, message: str):
        # Mock notification
        logger.info(f"Notification sent: {message[:30]}...")
    
    async def close(self):
        pass


class MobileOfflineManager:
    """Mobile offline operation manager"""
    
    def __init__(self, db: OptimizedLocalDatabase, sync: IntelligentSyncScheduler, config: MobileConfiguration):
        self.db = db
        self.sync = sync
        self.config = config
    
    async def initialize(self):
        logger.info("Offline manager initialized")
    
    async def process_offline_queue(self):
        # Process queued operations
        await self.sync.process_next_sync_batch(batch_size=self.config.sync_batch_size)
    
    async def cleanup_old_data(self) -> Dict[str, Any]:
        # Cleanup offline data
        return {"offline_cleanup": "completed"}
    
    async def close(self):
        pass


# Example usage and testing
async def test_mobile_implementation():
    """Test the mobile BUDDY implementation"""
    
    # Create mobile configuration for a premium device
    mobile_config = MobileConfiguration.for_device_profile(
        MobilePlatformType.REACT_NATIVE,
        MobileDeviceProfile.PREMIUM
    )
    
    # Initialize mobile BUDDY core
    buddy_mobile = MobileBuddyCore(
        user_id="test_user_123",
        device_id="mobile_device_456",
        mobile_config=mobile_config
    )
    
    try:
        # Initialize
        success = await buddy_mobile.initialize()
        if not success:
            raise RuntimeError("Failed to initialize mobile core")
        
        print("🚀 BUDDY Mobile Core initialized successfully!")
        
        # Test message sending
        print("\n📱 Testing mobile message...")
        result = await buddy_mobile.send_message("Hello BUDDY on mobile!")
        print(f"Message sent: {result['conversation_id']}")
        print(f"Response: {result['response']}")
        
        # Test voice input (mock)
        print("\n🎤 Testing voice input...")
        voice_result = await buddy_mobile.process_voice_input(b"mock_audio_data")
        print(f"Voice transcription: {voice_result['transcription']}")
        
        # Test mobile state changes
        print("\n📲 Testing app state changes...")
        await buddy_mobile.handle_app_state_change(False)  # Background
        await buddy_mobile.handle_network_change(False, "none")  # Offline
        await buddy_mobile.handle_battery_change(0.10, False)  # Low battery
        
        # Get mobile status
        print("\n📊 Mobile status:")
        status = await buddy_mobile.get_mobile_status()
        print(f"Platform: {status['platform']}")
        print(f"Device Profile: {status['device_profile']}")
        print(f"Network: {'Available' if status['network_available'] else 'Offline'}")
        print(f"Battery Optimized: {status['battery_optimized']}")
        print(f"Storage: {status['storage_usage']['percentage']:.1f}% used")
        
        # Test conversation history
        print("\n💬 Testing conversation history...")
        conversations = await buddy_mobile.get_conversation_history(limit=5)
        print(f"Retrieved {len(conversations)} conversations")
        
        print("\n✅ Mobile implementation test completed successfully!")
        
    except Exception as e:
        print(f"❌ Mobile test failed: {e}")
        raise
    
    finally:
        await buddy_mobile.close()


if __name__ == "__main__":
    # Run the mobile implementation test
    asyncio.run(test_mobile_implementation())
