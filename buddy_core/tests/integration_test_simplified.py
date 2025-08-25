#!/usr/bin/env python3
"""
Simplified Integration Test for BUDDY's Optimized Database Components

Tests the core integration of our optimized database architecture.
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
import logging

# Import our optimized components
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Now import relative to project root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database'))

from optimized_local_db import (
    OptimizedLocalDatabase, DeviceCapability, DatabaseConfig
)
from intelligent_sync import (
    IntelligentSyncScheduler, SyncPriority, NetworkQuality, DeviceConstraint
)
from performance_monitor import (
    DatabasePerformanceMonitor, QueryType, AlertLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimplifiedIntegrationTest:
    """Simplified integration test for core optimized components"""
    
    def __init__(self):
        self.temp_dir = None
        self.database = None
        self.sync_scheduler = None
        self.performance_monitor = None
        
    async def setup_test_environment(self):
        """Set up test environment"""
        logger.info("🚀 Setting up test environment...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="buddy_integration_test_")
        
        # Initialize optimized database for desktop (high performance)
        config = DatabaseConfig.for_device_capability(DeviceCapability.HIGH_PERFORMANCE)
        self.database = OptimizedLocalDatabase(
            db_path=os.path.join(self.temp_dir, "buddy_test.db"),
            config=config
        )
        await self.database.initialize()
        
        # Initialize sync scheduler
        self.sync_scheduler = IntelligentSyncScheduler("desktop")
        
        # Initialize performance monitor
        async def alert_callback(alert):
            logger.warning(f"Performance Alert: {alert.message}")
        
        self.performance_monitor = DatabasePerformanceMonitor("desktop", alert_callback)
        await self.performance_monitor.start_monitoring()
        
        logger.info("✅ Test environment setup complete!")
    
    async def test_optimized_database(self):
        """Test optimized database operations"""
        logger.info("🔍 Testing optimized database operations...")
        
        # Test conversation storage with performance monitoring
        conversations_stored = 0
        for i in range(50):
            conversation_data = {
                'user_input': f"Test user message {i}",
                'assistant_response': f"Test assistant response {i}",
                'metadata': {
                    'session_id': f"session_{i % 5}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Monitor the operation
            await self.performance_monitor.monitor_query(
                QueryType.CONVERSATION_INSERT,
                self.database.store_conversation_optimized,
                conversation_data
            )
            conversations_stored += 1
        
        # Test conversation retrieval
        conversations = await self.performance_monitor.monitor_query(
            QueryType.CONVERSATION_SELECT,
            self.database.get_conversation_history_optimized,
            limit=25
        )
        
        # Test preference operations
        preferences_set = 0
        for i in range(20):
            await self.performance_monitor.monitor_query(
                QueryType.PREFERENCE_UPSERT,
                self.database.set_preference_optimized,
                f'test_pref_{i}',
                f'test_value_{i}'
            )
            preferences_set += 1
        
        # Get performance metrics
        metrics = await self.database.get_performance_metrics()
        
        logger.info(f"✅ Database operations completed:")
        logger.info(f"   - Conversations stored: {conversations_stored}")
        logger.info(f"   - Conversations retrieved: {len(conversations)}")
        logger.info(f"   - Preferences set: {preferences_set}")
        logger.info(f"   - Database metrics: {json.dumps(metrics, indent=2)}")
        
        return {
            'conversations_stored': conversations_stored,
            'conversations_retrieved': len(conversations),
            'preferences_set': preferences_set,
            'metrics': metrics
        }
    
    async def test_intelligent_sync(self):
        """Test intelligent sync scheduler"""
        logger.info("🔄 Testing intelligent sync scheduler...")
        
        # Queue operations with different priorities
        operations_queued = 0
        priorities = [SyncPriority.REALTIME, SyncPriority.HIGH, SyncPriority.MEDIUM, 
                     SyncPriority.LOW, SyncPriority.BACKGROUND]
        
        for i in range(25):
            priority = priorities[i % len(priorities)]
            
            operation_data = {
                'type': 'conversation_sync',
                'device_id': 'test_desktop',
                'data': {
                    'conversation_id': f"conv_{i}",
                    'content': f"Sync test data {i}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            operation_id = await self.sync_scheduler.queue_sync_operation(
                operation_data, priority
            )
            operations_queued += 1
        
        # Test network quality adaptation
        for network_quality in [NetworkQuality.EXCELLENT, NetworkQuality.GOOD, NetworkQuality.POOR]:
            context_update = {
                'network_quality': network_quality,
                'device_constraints': []
            }
            await self.sync_scheduler.update_sync_context(context_update)
        
        # Process sync operations
        operations_processed = 0
        for _ in range(5):  # Process in batches
            processed = await self.sync_scheduler.process_next_sync_batch(batch_size=5)
            if not processed:
                break
            operations_processed += len(processed)
            await asyncio.sleep(0.1)
        
        # Get statistics
        stats = await self.sync_scheduler.get_sync_statistics()
        
        logger.info(f"✅ Sync operations completed:")
        logger.info(f"   - Operations queued: {operations_queued}")
        logger.info(f"   - Operations processed: {operations_processed}")
        logger.info(f"   - Sync statistics: {json.dumps(stats, indent=2)}")
        
        return {
            'operations_queued': operations_queued,
            'operations_processed': operations_processed,
            'stats': stats
        }
    
    async def test_performance_monitoring(self):
        """Test performance monitoring"""
        logger.info("📊 Testing performance monitoring...")
        
        # Let monitor collect data
        await asyncio.sleep(3)
        
        # Generate performance report
        report = self.performance_monitor.generate_performance_report(hours_back=1)
        
        # Get real-time metrics
        real_time_metrics = await self.performance_monitor.get_real_time_metrics()
        
        # Get optimization recommendations
        recommendations = self.performance_monitor.get_optimization_recommendations()
        
        logger.info(f"✅ Performance monitoring completed:")
        if 'overall_stats' in report:
            stats = report['overall_stats']
            logger.info(f"   - Total queries: {stats['total_queries']}")
            logger.info(f"   - Success rate: {stats['success_rate_percent']:.1f}%")
            logger.info(f"   - Avg execution time: {stats['avg_execution_time']:.4f}s")
        
        logger.info(f"   - Optimization recommendations: {len(recommendations)}")
        for rec in recommendations[:3]:  # Show first 3 recommendations
            logger.info(f"     • {rec}")
        
        return {
            'report': report,
            'real_time_metrics': real_time_metrics,
            'recommendations': recommendations
        }
    
    async def test_integration_workflow(self):
        """Test complete integration workflow"""
        logger.info("🌐 Testing complete integration workflow...")
        
        # Simulate a complete BUDDY interaction workflow
        workflow_results = {
            'conversations_processed': 0,
            'sync_operations_created': 0,
            'performance_tracked': True
        }
        
        # Simulate 10 conversation interactions
        for i in range(10):
            # 1. Store conversation with performance monitoring
            conversation = {
                'user_input': f"Workflow test conversation {i}",
                'assistant_response': f"BUDDY response for workflow test {i}",
                'metadata': {
                    'workflow_test': True,
                    'interaction_id': i,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            await self.performance_monitor.monitor_query(
                QueryType.CONVERSATION_INSERT,
                self.database.store_conversation_optimized,
                conversation
            )
            workflow_results['conversations_processed'] += 1
            
            # 2. Create sync operation for the conversation
            sync_data = {
                'type': 'conversation_backup',
                'device_id': 'test_desktop',
                'data': conversation
            }
            
            # Use different priorities for different conversations
            priority = SyncPriority.HIGH if i % 3 == 0 else SyncPriority.MEDIUM
            
            await self.sync_scheduler.queue_sync_operation(sync_data, priority)
            workflow_results['sync_operations_created'] += 1
            
            # Small delay to simulate real interaction timing
            await asyncio.sleep(0.1)
        
        # Process sync operations
        sync_processed = 0
        for _ in range(3):
            processed = await self.sync_scheduler.process_next_sync_batch(batch_size=5)
            if processed:
                sync_processed += len(processed)
            await asyncio.sleep(0.1)
        
        workflow_results['sync_operations_processed'] = sync_processed
        
        # Get final performance metrics
        final_metrics = await self.database.get_performance_metrics()
        workflow_results['final_metrics'] = final_metrics
        
        logger.info(f"✅ Integration workflow completed:")
        logger.info(f"   - Conversations processed: {workflow_results['conversations_processed']}")
        logger.info(f"   - Sync operations created: {workflow_results['sync_operations_created']}")
        logger.info(f"   - Sync operations processed: {workflow_results['sync_operations_processed']}")
        
        return workflow_results
    
    async def run_comprehensive_test(self):
        """Run the complete integration test"""
        logger.info("🎯 Starting comprehensive integration test...")
        
        start_time = time.time()
        test_results = {}
        
        try:
            # Setup environment
            await self.setup_test_environment()
            
            # Run test phases
            test_results['database_test'] = await self.test_optimized_database()
            test_results['sync_test'] = await self.test_intelligent_sync()
            test_results['monitoring_test'] = await self.test_performance_monitoring()
            test_results['integration_test'] = await self.test_integration_workflow()
            
            # Generate summary
            total_time = time.time() - start_time
            test_results['summary'] = {
                'total_execution_time': total_time,
                'test_completed': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Save results
            results_path = os.path.join(self.temp_dir, 'integration_test_results.json')
            with open(results_path, 'w') as f:
                json.dump(test_results, f, indent=2)
            
            logger.info(f"\n🎉 INTEGRATION TEST COMPLETED SUCCESSFULLY! 🎉")
            logger.info(f"Total execution time: {total_time:.2f} seconds")
            logger.info(f"Results saved to: {results_path}")
            
            # Print summary
            logger.info("\n📈 TEST SUMMARY:")
            db_results = test_results['database_test']
            sync_results = test_results['sync_test']
            workflow_results = test_results['integration_test']
            
            logger.info(f"   Database operations: {db_results['conversations_stored']} conversations, {db_results['preferences_set']} preferences")
            logger.info(f"   Sync operations: {sync_results['operations_queued']} queued, {sync_results['operations_processed']} processed")
            logger.info(f"   Workflow integration: {workflow_results['conversations_processed']} interactions processed")
            
            return test_results
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            raise
        
        finally:
            await self.cleanup_test_environment()
    
    async def cleanup_test_environment(self):
        """Clean up test environment"""
        logger.info("🧹 Cleaning up test environment...")
        
        try:
            if self.performance_monitor:
                await self.performance_monitor.stop_monitoring()
            
            if self.database:
                await self.database.close()
            
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            logger.info("✅ Test environment cleanup completed")
            
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


async def main():
    """Run the simplified integration test"""
    test = SimplifiedIntegrationTest()
    await test.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
