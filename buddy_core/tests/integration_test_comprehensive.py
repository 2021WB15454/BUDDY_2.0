#!/usr/bin/env python3
"""
Comprehensive Integration Test for BUDDY's Optimized Database Components

Tests the integration of:
- OptimizedLocalDatabase with device-adaptive configurations
- IntelligentSyncScheduler with priority-based synchronization
- DatabasePerformanceMonitor with real-time monitoring
- Cross-platform memory layer integration
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
import logging

# Import our optimized components
from buddy_core.database.optimized_local_db import (
    OptimizedLocalDatabase, DeviceCapability, DatabaseConfig
)
from buddy_core.database.intelligent_sync import (
    IntelligentSyncScheduler, SyncPriority, NetworkQuality, DeviceConstraint
)
from buddy_core.database.performance_monitor import (
    DatabasePerformanceMonitor, QueryType, AlertLevel
)
from buddy_core.memory.cross_platform import CrossPlatformMemory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IntegrationTestSuite:
    """Comprehensive integration test suite for optimized database components"""
    
    def __init__(self):
        self.test_results = {}
        self.temp_dirs = []
        self.databases = {}
        self.sync_schedulers = {}
        self.performance_monitors = {}
        self.memory_layers = {}
        
        # Test configuration
        self.device_types = ['desktop', 'mobile', 'watch', 'tv', 'car']
        self.test_data_scale = {
            'conversations': 100,
            'preferences': 50,
            'sync_operations': 200
        }
    
    async def setup_test_environment(self):
        """Set up test environment with all device types"""
        logger.info("🚀 Setting up comprehensive test environment...")
        
        for device_type in self.device_types:
            # Create temporary directory for device
            temp_dir = tempfile.mkdtemp(prefix=f"buddy_test_{device_type}_")
            self.temp_dirs.append(temp_dir)
            
            # Initialize optimized database
            capability = self._get_device_capability(device_type)
            config = DatabaseConfig.for_device_capability(capability)
            
            db = OptimizedLocalDatabase(
                db_path=os.path.join(temp_dir, "buddy.db"),
                config=config
            )
            await db.initialize()
            self.databases[device_type] = db
            
            # Initialize sync scheduler
            sync_scheduler = IntelligentSyncScheduler(device_type)
            self.sync_schedulers[device_type] = sync_scheduler
            
            # Initialize performance monitor with test callback
            async def alert_callback(alert):
                logger.warning(f"[{device_type}] Performance Alert: {alert.message}")
            
            performance_monitor = DatabasePerformanceMonitor(device_type, alert_callback)
            await performance_monitor.start_monitoring()
            self.performance_monitors[device_type] = performance_monitor
            
            # Initialize cross-platform memory layer
            memory_layer = CrossPlatformMemory(
                device_id=f"test_{device_type}",
                device_type=device_type,
                storage_path=temp_dir
            )
            await memory_layer.initialize()
            
            # Inject optimized database into memory layer
            memory_layer.local_db = db
            memory_layer.performance_monitor = performance_monitor
            
            self.memory_layers[device_type] = memory_layer
            
            logger.info(f"✅ {device_type.capitalize()} environment initialized")
        
        logger.info("🎯 Test environment setup complete!")
    
    def _get_device_capability(self, device_type: str) -> DeviceCapability:
        """Map device type to capability level"""
        capability_map = {
            'desktop': DeviceCapability.HIGH_PERFORMANCE,
            'mobile': DeviceCapability.MEDIUM_PERFORMANCE,
            'tv': DeviceCapability.MEDIUM_PERFORMANCE,
            'watch': DeviceCapability.CONSTRAINED,
            'car': DeviceCapability.LOW_PERFORMANCE
        }
        return capability_map.get(device_type, DeviceCapability.MEDIUM_PERFORMANCE)
    
    async def test_optimized_database_operations(self):
        """Test optimized database operations across all device types"""
        logger.info("🔍 Testing optimized database operations...")
        
        test_results = {}
        
        for device_type, db in self.databases.items():
            logger.info(f"Testing {device_type} database operations...")
            
            device_results = {
                'conversation_ops': [],
                'preference_ops': [],
                'performance_metrics': {}
            }
            
            # Test conversation operations
            start_time = time.time()
            for i in range(self.test_data_scale['conversations']):
                conversation_data = {
                    'user_input': f"Test user message {i} for {device_type}",
                    'assistant_response': f"Test assistant response {i} for {device_type}",
                    'metadata': {
                        'session_id': f"session_{i % 10}",
                        'device_type': device_type,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                }
                
                # Use performance monitor to track operation
                monitor = self.performance_monitors[device_type]
                await monitor.monitor_query(
                    QueryType.CONVERSATION_INSERT,
                    db.store_conversation_optimized,
                    conversation_data
                )
                
                device_results['conversation_ops'].append({
                    'operation': 'insert',
                    'success': True,
                    'message_id': i
                })
            
            conversation_time = time.time() - start_time
            
            # Test conversation retrieval
            start_time = time.time()
            conversations = await monitor.monitor_query(
                QueryType.CONVERSATION_SELECT,
                db.get_conversation_history_optimized,
                limit=50
            )
            retrieval_time = time.time() - start_time
            
            # Test preference operations
            start_time = time.time()
            for i in range(self.test_data_scale['preferences']):
                preference_data = {
                    'key': f'test_preference_{i}',
                    'value': f'test_value_{i}_{device_type}',
                    'device_type': device_type
                }
                
                await monitor.monitor_query(
                    QueryType.PREFERENCE_UPSERT,
                    db.set_preference_optimized,
                    preference_data['key'],
                    preference_data['value']
                )
                
                device_results['preference_ops'].append({
                    'operation': 'upsert',
                    'success': True,
                    'key': preference_data['key']
                })
            
            preference_time = time.time() - start_time
            
            # Get performance metrics
            performance_metrics = await db.get_performance_metrics()
            device_results['performance_metrics'] = {
                'conversation_insert_time': conversation_time,
                'conversation_retrieval_time': retrieval_time,
                'preference_ops_time': preference_time,
                'conversations_stored': len(device_results['conversation_ops']),
                'preferences_stored': len(device_results['preference_ops']),
                'database_metrics': performance_metrics
            }
            
            test_results[device_type] = device_results
            
            logger.info(f"✅ {device_type} operations completed:")
            logger.info(f"   - Conversations: {len(device_results['conversation_ops'])} ops in {conversation_time:.2f}s")
            logger.info(f"   - Preferences: {len(device_results['preference_ops'])} ops in {preference_time:.2f}s")
            logger.info(f"   - Retrieved: {len(conversations)} conversations in {retrieval_time:.2f}s")
        
        self.test_results['database_operations'] = test_results
        return test_results
    
    async def test_intelligent_sync_operations(self):
        """Test intelligent sync scheduler across devices"""
        logger.info("🔄 Testing intelligent sync operations...")
        
        sync_results = {}
        
        for device_type, scheduler in self.sync_schedulers.items():
            logger.info(f"Testing {device_type} sync scheduler...")
            
            device_sync_results = {
                'operations_queued': 0,
                'operations_processed': 0,
                'priority_distribution': {},
                'network_adaptations': 0
            }
            
            # Create sync operations with different priorities
            priorities = [SyncPriority.REALTIME, SyncPriority.HIGH, SyncPriority.MEDIUM, 
                         SyncPriority.LOW, SyncPriority.BACKGROUND]
            
            for i in range(self.test_data_scale['sync_operations']):
                priority = priorities[i % len(priorities)]
                
                # Create sync operation
                operation_data = {
                    'type': 'conversation_sync',
                    'device_id': f"test_{device_type}",
                    'data': {
                        'conversation_id': f"conv_{i}",
                        'content': f"Sync test data {i} for {device_type}",
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                }
                
                # Queue operation
                operation_id = await scheduler.queue_sync_operation(
                    operation_data, priority
                )
                
                device_sync_results['operations_queued'] += 1
                
                # Track priority distribution
                priority_key = priority.value
                device_sync_results['priority_distribution'][priority_key] = \
                    device_sync_results['priority_distribution'].get(priority_key, 0) + 1
            
            # Test network quality adaptation
            network_qualities = [NetworkQuality.EXCELLENT, NetworkQuality.GOOD, 
                               NetworkQuality.POOR, NetworkQuality.MINIMAL]
            
            for network_quality in network_qualities:
                # Update sync context with different network conditions
                context_update = {
                    'network_quality': network_quality,
                    'device_constraints': [DeviceConstraint.BATTERY] if device_type == 'mobile' else []
                }
                
                await scheduler.update_sync_context(context_update)
                device_sync_results['network_adaptations'] += 1
            
            # Process some operations
            processed_count = 0
            max_process_attempts = 20
            
            for _ in range(max_process_attempts):
                processed = await scheduler.process_next_sync_batch(batch_size=10)
                if not processed:
                    break
                processed_count += len(processed)
                await asyncio.sleep(0.1)  # Small delay between batches
            
            device_sync_results['operations_processed'] = processed_count
            
            # Get scheduler statistics
            stats = await scheduler.get_sync_statistics()
            device_sync_results['scheduler_stats'] = stats
            
            sync_results[device_type] = device_sync_results
            
            logger.info(f"✅ {device_type} sync operations completed:")
            logger.info(f"   - Queued: {device_sync_results['operations_queued']} operations")
            logger.info(f"   - Processed: {device_sync_results['operations_processed']} operations")
            logger.info(f"   - Network adaptations: {device_sync_results['network_adaptations']}")
        
        self.test_results['sync_operations'] = sync_results
        return sync_results
    
    async def test_performance_monitoring(self):
        """Test performance monitoring across all devices"""
        logger.info("📊 Testing performance monitoring...")
        
        monitoring_results = {}
        
        for device_type, monitor in self.performance_monitors.items():
            logger.info(f"Testing {device_type} performance monitoring...")
            
            # Let monitor collect some data
            await asyncio.sleep(2)
            
            # Generate performance report
            report = monitor.generate_performance_report(hours_back=1)
            
            # Get real-time metrics
            real_time_metrics = await monitor.get_real_time_metrics()
            
            # Get optimization recommendations
            recommendations = monitor.get_optimization_recommendations()
            
            monitoring_results[device_type] = {
                'performance_report': report,
                'real_time_metrics': real_time_metrics,
                'optimization_recommendations': recommendations,
                'monitoring_active': monitor.is_monitoring
            }
            
            logger.info(f"✅ {device_type} monitoring results:")
            if 'overall_stats' in report:
                stats = report['overall_stats']
                logger.info(f"   - Total queries: {stats['total_queries']}")
                logger.info(f"   - Success rate: {stats['success_rate_percent']:.1f}%")
                logger.info(f"   - Avg execution time: {stats['avg_execution_time']:.4f}s")
            logger.info(f"   - Recommendations: {len(recommendations)}")
        
        self.test_results['performance_monitoring'] = monitoring_results
        return monitoring_results
    
    async def test_cross_platform_integration(self):
        """Test cross-platform memory layer integration"""
        logger.info("🌐 Testing cross-platform integration...")
        
        integration_results = {}
        
        # Test data synchronization between devices
        for source_device in self.device_types[:3]:  # Test with first 3 devices
            source_memory = self.memory_layers[source_device]
            
            device_results = {
                'conversations_stored': 0,
                'preferences_set': 0,
                'sync_operations': 0
            }
            
            # Store conversations using optimized methods
            for i in range(20):
                conversation = {
                    'user_input': f"Cross-platform test {i} from {source_device}",
                    'assistant_response': f"Response {i} for cross-platform test",
                    'metadata': {
                        'test_id': f"cross_platform_{i}",
                        'source_device': source_device
                    }
                }
                
                await source_memory.store_conversation_optimized(conversation)
                device_results['conversations_stored'] += 1
            
            # Set preferences using optimized methods
            for i in range(10):
                key = f"cross_platform_pref_{i}"
                value = f"value_from_{source_device}_{i}"
                
                await source_memory.set_preference_optimized(key, value)
                device_results['preferences_set'] += 1
            
            # Test performance metrics retrieval
            performance_metrics = await source_memory.get_performance_metrics()
            device_results['performance_metrics'] = performance_metrics
            
            # Test data cleanup
            await source_memory.cleanup_expired_data_optimized()
            device_results['cleanup_performed'] = True
            
            integration_results[source_device] = device_results
            
            logger.info(f"✅ {source_device} cross-platform operations:")
            logger.info(f"   - Stored: {device_results['conversations_stored']} conversations")
            logger.info(f"   - Set: {device_results['preferences_set']} preferences")
        
        self.test_results['cross_platform_integration'] = integration_results
        return integration_results
    
    async def test_device_capability_adaptation(self):
        """Test device capability-based adaptations"""
        logger.info("⚙️ Testing device capability adaptations...")
        
        capability_results = {}
        
        for device_type, db in self.databases.items():
            capability = self._get_device_capability(device_type)
            config = db.config
            
            capability_results[device_type] = {
                'device_capability': capability.value,
                'cache_size': config.cache_size,
                'batch_size': config.batch_size,
                'connection_pool_size': config.connection_pool_size,
                'pragma_settings': config.pragma_settings,
                'performance_optimized': True
            }
            
            # Test capability-specific operations
            if capability == DeviceCapability.HIGH_PERFORMANCE:
                # Desktop should handle large operations efficiently
                large_data = {'data': 'x' * 10000}  # 10KB data
                start_time = time.time()
                
                for i in range(50):
                    await db.store_conversation_optimized({
                        'user_input': f'Large data test {i}',
                        'assistant_response': json.dumps(large_data),
                        'metadata': {'test_type': 'large_data'}
                    })
                
                large_data_time = time.time() - start_time
                capability_results[device_type]['large_data_performance'] = large_data_time
                
            elif capability == DeviceCapability.CONSTRAINED:
                # Watch should prioritize minimal operations
                start_time = time.time()
                
                for i in range(10):  # Smaller test for constrained devices
                    await db.store_conversation_optimized({
                        'user_input': f'Minimal test {i}',
                        'assistant_response': f'Quick response {i}',
                        'metadata': {'test_type': 'minimal'}
                    })
                
                minimal_time = time.time() - start_time
                capability_results[device_type]['minimal_operations_performance'] = minimal_time
            
            logger.info(f"✅ {device_type} capability adaptation:")
            logger.info(f"   - Capability: {capability.value}")
            logger.info(f"   - Cache size: {config.cache_size}")
            logger.info(f"   - Batch size: {config.batch_size}")
        
        self.test_results['device_capability_adaptation'] = capability_results
        return capability_results
    
    async def run_comprehensive_test(self):
        """Run the complete integration test suite"""
        logger.info("🎯 Starting comprehensive integration test suite...")
        
        try:
            # Setup test environment
            await self.setup_test_environment()
            
            # Run all test phases
            test_phases = [
                ('Database Operations', self.test_optimized_database_operations),
                ('Sync Operations', self.test_intelligent_sync_operations),
                ('Performance Monitoring', self.test_performance_monitoring),
                ('Cross-Platform Integration', self.test_cross_platform_integration),
                ('Device Capability Adaptation', self.test_device_capability_adaptation)
            ]
            
            for phase_name, test_method in test_phases:
                logger.info(f"\n{'='*60}")
                logger.info(f"PHASE: {phase_name}")
                logger.info(f"{'='*60}")
                
                start_time = time.time()
                await test_method()
                phase_time = time.time() - start_time
                
                logger.info(f"✅ {phase_name} completed in {phase_time:.2f}s")
            
            # Generate comprehensive report
            await self.generate_comprehensive_report()
            
            logger.info("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY! 🎉")
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            raise
        
        finally:
            await self.cleanup_test_environment()
    
    async def generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        logger.info("📋 Generating comprehensive test report...")
        
        report = {
            'test_execution_time': datetime.now(timezone.utc).isoformat(),
            'devices_tested': self.device_types,
            'test_data_scale': self.test_data_scale,
            'test_results': self.test_results,
            'summary': {
                'total_devices': len(self.device_types),
                'total_conversations_stored': 0,
                'total_preferences_set': 0,
                'total_sync_operations': 0,
                'performance_issues_detected': 0,
                'optimization_recommendations': []
            }
        }
        
        # Calculate summary statistics
        for device_type in self.device_types:
            # Database operations summary
            if 'database_operations' in self.test_results:
                db_results = self.test_results['database_operations'].get(device_type, {})
                report['summary']['total_conversations_stored'] += len(
                    db_results.get('conversation_ops', [])
                )
                report['summary']['total_preferences_set'] += len(
                    db_results.get('preference_ops', [])
                )
            
            # Sync operations summary
            if 'sync_operations' in self.test_results:
                sync_results = self.test_results['sync_operations'].get(device_type, {})
                report['summary']['total_sync_operations'] += sync_results.get(
                    'operations_queued', 0
                )
            
            # Performance monitoring summary
            if 'performance_monitoring' in self.test_results:
                perf_results = self.test_results['performance_monitoring'].get(device_type, {})
                recommendations = perf_results.get('optimization_recommendations', [])
                report['summary']['optimization_recommendations'].extend([
                    f"[{device_type}] {rec}" for rec in recommendations
                ])
        
        # Save report to file
        report_path = os.path.join(tempfile.gettempdir(), 'buddy_integration_test_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Comprehensive report saved to: {report_path}")
        
        # Print summary
        summary = report['summary']
        logger.info("\n📈 TEST SUMMARY:")
        logger.info(f"   Devices tested: {summary['total_devices']}")
        logger.info(f"   Conversations stored: {summary['total_conversations_stored']}")
        logger.info(f"   Preferences set: {summary['total_preferences_set']}")
        logger.info(f"   Sync operations: {summary['total_sync_operations']}")
        logger.info(f"   Optimization recommendations: {len(summary['optimization_recommendations'])}")
        
        return report
    
    async def cleanup_test_environment(self):
        """Clean up test environment"""
        logger.info("🧹 Cleaning up test environment...")
        
        # Stop performance monitors
        for monitor in self.performance_monitors.values():
            await monitor.stop_monitoring()
        
        # Close databases
        for db in self.databases.values():
            await db.close()
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to remove temp dir {temp_dir}: {e}")
        
        logger.info("✅ Test environment cleanup completed")


async def main():
    """Run the comprehensive integration test"""
    test_suite = IntegrationTestSuite()
    await test_suite.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
