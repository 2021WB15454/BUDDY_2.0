#!/usr/bin/env python3
"""
Database Performance Monitor for BUDDY Cross-Platform AI Assistant

Real-time performance monitoring, analysis, and optimization recommendations
for BUDDY's cross-platform database architecture.
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import statistics
import json

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of database queries being monitored"""
    CONVERSATION_INSERT = "conversation_insert"
    CONVERSATION_SELECT = "conversation_select"
    CONVERSATION_UPDATE = "conversation_update"
    PREFERENCE_UPSERT = "preference_upsert"
    PREFERENCE_SELECT = "preference_select"
    CONTEXT_INSERT = "context_insert"
    CONTEXT_SEARCH = "context_search"
    SYNC_QUEUE_INSERT = "sync_queue_insert"
    SYNC_QUEUE_SELECT = "sync_queue_select"
    CLEANUP_OPERATION = "cleanup_operation"
    INDEX_OPTIMIZATION = "index_optimization"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class QueryMetrics:
    """Metrics for a single database query"""
    query_type: QueryType
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    rows_affected: int
    timestamp: datetime
    device_type: str
    success: bool
    error_message: Optional[str] = None
    query_size_bytes: int = 0
    cache_hit: bool = False


@dataclass
class PerformanceAlert:
    """Performance alert information"""
    level: AlertLevel
    message: str
    metric_type: str
    value: float
    threshold: float
    timestamp: datetime
    device_type: str
    query_type: Optional[QueryType] = None


@dataclass
class DeviceResourceState:
    """Current device resource state"""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    storage_free_mb: float
    network_connected: bool
    battery_percent: Optional[float] = None
    is_charging: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DatabasePerformanceMonitor:
    """
    Comprehensive database performance monitoring system that tracks:
    - Query execution times and resource usage
    - Device resource consumption
    - Performance trends and anomalies
    - Automatic optimization recommendations
    """
    
    def __init__(self, device_type: str, alert_callback: Optional[Callable] = None):
        self.device_type = device_type
        self.alert_callback = alert_callback
        
        # Metrics storage
        self.query_metrics: List[QueryMetrics] = []
        self.resource_states: List[DeviceResourceState] = []
        self.performance_alerts: List[PerformanceAlert] = []
        
        # Configuration
        self.max_metrics_stored = 10000
        self.metrics_retention_hours = 24
        
        # Alert thresholds (device-specific)
        self.alert_thresholds = self._get_alert_thresholds()
        
        # Performance baselines (learned over time)
        self.performance_baselines: Dict[QueryType, Dict[str, float]] = {}
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_task = None
        self.cleanup_task = None
        
        # Thread-safe access
        self.metrics_lock = threading.RLock()
        
        logger.info(f"Performance monitor initialized for {device_type}")
    
    def _get_alert_thresholds(self) -> Dict[str, float]:
        """Get device-specific alert thresholds"""
        base_thresholds = {
            'query_time_warning': 1.0,      # 1 second
            'query_time_critical': 5.0,     # 5 seconds
            'memory_usage_warning': 100,     # 100 MB
            'memory_usage_critical': 500,    # 500 MB
            'cpu_usage_warning': 70,         # 70%
            'cpu_usage_critical': 90,        # 90%
            'error_rate_warning': 0.05,      # 5%
            'error_rate_critical': 0.20,     # 20%
            'storage_warning_mb': 100,       # 100 MB free
            'storage_critical_mb': 50        # 50 MB free
        }
        
        # Adjust thresholds based on device type
        if self.device_type in ['watch', 'car']:
            # More conservative thresholds for constrained devices
            base_thresholds.update({
                'query_time_warning': 0.5,
                'query_time_critical': 2.0,
                'memory_usage_warning': 50,
                'memory_usage_critical': 100,
                'cpu_usage_warning': 50,
                'cpu_usage_critical': 70
            })
        elif self.device_type == 'desktop':
            # More relaxed thresholds for desktop
            base_thresholds.update({
                'query_time_warning': 2.0,
                'query_time_critical': 10.0,
                'memory_usage_warning': 200,
                'memory_usage_critical': 1000
            })
        
        return base_thresholds
    
    async def start_monitoring(self):
        """Start the performance monitoring system"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        
        # Start monitoring tasks
        self.monitor_task = asyncio.create_task(self._resource_monitoring_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop the performance monitoring system"""
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def monitor_query(self, query_type: QueryType, query_func: Callable, 
                          *args, **kwargs) -> Any:
        """
        Monitor a database query and collect performance metrics
        
        Args:
            query_type: Type of query being executed
            query_func: The async function to execute
            *args, **kwargs: Arguments to pass to the query function
        
        Returns:
            The result of the query function
        """
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent()
        
        success = True
        result = None
        error_message = None
        rows_affected = 0
        
        try:
            # Execute the query
            result = await query_func(*args, **kwargs)
            
            # Try to determine rows affected
            if hasattr(result, '__len__'):
                rows_affected = len(result)
            elif isinstance(result, str):
                rows_affected = 1  # Single operation like insert
            
        except Exception as e:
            success = False
            error_message = str(e)
            raise e
        
        finally:
            # Calculate metrics
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            end_cpu = psutil.cpu_percent()
            
            execution_time = end_time - start_time
            memory_usage = max(0, end_memory - start_memory)
            cpu_usage = end_cpu
            
            # Create metrics record
            metrics = QueryMetrics(
                query_type=query_type,
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                rows_affected=rows_affected,
                timestamp=datetime.now(timezone.utc),
                device_type=self.device_type,
                success=success,
                error_message=error_message
            )
            
            # Store metrics
            await self._record_metrics(metrics)
            
            # Check for alerts
            await self._check_for_alerts(metrics)
        
        return result
    
    async def _record_metrics(self, metrics: QueryMetrics):
        """Record performance metrics thread-safely"""
        with self.metrics_lock:
            self.query_metrics.append(metrics)
            
            # Maintain maximum metrics limit
            if len(self.query_metrics) > self.max_metrics_stored:
                # Remove oldest 10% when limit is reached
                remove_count = self.max_metrics_stored // 10
                self.query_metrics = self.query_metrics[remove_count:]
        
        # Update performance baselines
        await self._update_performance_baselines(metrics)
    
    async def _update_performance_baselines(self, metrics: QueryMetrics):
        """Update performance baselines for the query type"""
        query_type = metrics.query_type
        
        if query_type not in self.performance_baselines:
            self.performance_baselines[query_type] = {
                'avg_execution_time': metrics.execution_time,
                'avg_memory_usage': metrics.memory_usage_mb,
                'avg_cpu_usage': metrics.cpu_usage_percent,
                'sample_count': 1
            }
        else:
            baseline = self.performance_baselines[query_type]
            count = baseline['sample_count']
            
            # Use exponential moving average for adaptive baselines
            alpha = 0.1  # Learning rate
            baseline['avg_execution_time'] = (
                (1 - alpha) * baseline['avg_execution_time'] + 
                alpha * metrics.execution_time
            )
            baseline['avg_memory_usage'] = (
                (1 - alpha) * baseline['avg_memory_usage'] + 
                alpha * metrics.memory_usage_mb
            )
            baseline['avg_cpu_usage'] = (
                (1 - alpha) * baseline['avg_cpu_usage'] + 
                alpha * metrics.cpu_usage_percent
            )
            baseline['sample_count'] = count + 1
    
    async def _check_for_alerts(self, metrics: QueryMetrics):
        """Check if metrics exceed alert thresholds"""
        alerts = []
        
        # Query execution time alerts
        if metrics.execution_time > self.alert_thresholds['query_time_critical']:
            alerts.append(PerformanceAlert(
                level=AlertLevel.CRITICAL,
                message=f"Query execution time critical: {metrics.execution_time:.2f}s",
                metric_type="execution_time",
                value=metrics.execution_time,
                threshold=self.alert_thresholds['query_time_critical'],
                timestamp=metrics.timestamp,
                device_type=self.device_type,
                query_type=metrics.query_type
            ))
        elif metrics.execution_time > self.alert_thresholds['query_time_warning']:
            alerts.append(PerformanceAlert(
                level=AlertLevel.WARNING,
                message=f"Query execution time high: {metrics.execution_time:.2f}s",
                metric_type="execution_time",
                value=metrics.execution_time,
                threshold=self.alert_thresholds['query_time_warning'],
                timestamp=metrics.timestamp,
                device_type=self.device_type,
                query_type=metrics.query_type
            ))
        
        # Memory usage alerts
        if metrics.memory_usage_mb > self.alert_thresholds['memory_usage_critical']:
            alerts.append(PerformanceAlert(
                level=AlertLevel.CRITICAL,
                message=f"Memory usage critical: {metrics.memory_usage_mb:.1f}MB",
                metric_type="memory_usage",
                value=metrics.memory_usage_mb,
                threshold=self.alert_thresholds['memory_usage_critical'],
                timestamp=metrics.timestamp,
                device_type=self.device_type,
                query_type=metrics.query_type
            ))
        elif metrics.memory_usage_mb > self.alert_thresholds['memory_usage_warning']:
            alerts.append(PerformanceAlert(
                level=AlertLevel.WARNING,
                message=f"Memory usage high: {metrics.memory_usage_mb:.1f}MB",
                metric_type="memory_usage",
                value=metrics.memory_usage_mb,
                threshold=self.alert_thresholds['memory_usage_warning'],
                timestamp=metrics.timestamp,
                device_type=self.device_type,
                query_type=metrics.query_type
            ))
        
        # CPU usage alerts
        if metrics.cpu_usage_percent > self.alert_thresholds['cpu_usage_critical']:
            alerts.append(PerformanceAlert(
                level=AlertLevel.CRITICAL,
                message=f"CPU usage critical: {metrics.cpu_usage_percent:.1f}%",
                metric_type="cpu_usage",
                value=metrics.cpu_usage_percent,
                threshold=self.alert_thresholds['cpu_usage_critical'],
                timestamp=metrics.timestamp,
                device_type=self.device_type,
                query_type=metrics.query_type
            ))
        
        # Query failure alert
        if not metrics.success:
            alerts.append(PerformanceAlert(
                level=AlertLevel.WARNING,
                message=f"Query failed: {metrics.error_message}",
                metric_type="error",
                value=1.0,
                threshold=0.0,
                timestamp=metrics.timestamp,
                device_type=self.device_type,
                query_type=metrics.query_type
            ))
        
        # Store and notify alerts
        for alert in alerts:
            self.performance_alerts.append(alert)
            if self.alert_callback:
                try:
                    await self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    async def _resource_monitoring_loop(self):
        """Continuously monitor device resources"""
        while self.is_monitoring:
            try:
                # Collect current resource state
                state = DeviceResourceState(
                    cpu_percent=psutil.cpu_percent(interval=1),
                    memory_percent=psutil.virtual_memory().percent,
                    memory_available_mb=psutil.virtual_memory().available / 1024 / 1024,
                    storage_free_mb=psutil.disk_usage('/').free / 1024 / 1024,
                    network_connected=self._check_network_connectivity()
                )
                
                # Add battery info if available (mobile devices)
                try:
                    if hasattr(psutil, 'sensors_battery') and psutil.sensors_battery():
                        battery = psutil.sensors_battery()
                        state.battery_percent = battery.percent
                        state.is_charging = battery.power_plugged
                except:
                    pass  # Battery info not available
                
                self.resource_states.append(state)
                
                # Maintain resource state history (keep last 1000 records)
                if len(self.resource_states) > 1000:
                    self.resource_states = self.resource_states[-1000:]
                
                # Check for resource-based alerts
                await self._check_resource_alerts(state)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(60)  # Error recovery delay
    
    def _check_network_connectivity(self) -> bool:
        """Check if network is connected (simplified check)"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except:
            return False
    
    async def _check_resource_alerts(self, state: DeviceResourceState):
        """Check for resource-based alerts"""
        alerts = []
        
        # Storage alerts
        if state.storage_free_mb < self.alert_thresholds['storage_critical_mb']:
            alerts.append(PerformanceAlert(
                level=AlertLevel.CRITICAL,
                message=f"Storage critically low: {state.storage_free_mb:.0f}MB free",
                metric_type="storage",
                value=state.storage_free_mb,
                threshold=self.alert_thresholds['storage_critical_mb'],
                timestamp=state.timestamp,
                device_type=self.device_type
            ))
        elif state.storage_free_mb < self.alert_thresholds['storage_warning_mb']:
            alerts.append(PerformanceAlert(
                level=AlertLevel.WARNING,
                message=f"Storage low: {state.storage_free_mb:.0f}MB free",
                metric_type="storage",
                value=state.storage_free_mb,
                threshold=self.alert_thresholds['storage_warning_mb'],
                timestamp=state.timestamp,
                device_type=self.device_type
            ))
        
        # Memory alerts
        if state.memory_percent > 90:
            alerts.append(PerformanceAlert(
                level=AlertLevel.CRITICAL,
                message=f"System memory critically high: {state.memory_percent:.1f}%",
                metric_type="system_memory",
                value=state.memory_percent,
                threshold=90.0,
                timestamp=state.timestamp,
                device_type=self.device_type
            ))
        elif state.memory_percent > 75:
            alerts.append(PerformanceAlert(
                level=AlertLevel.WARNING,
                message=f"System memory high: {state.memory_percent:.1f}%",
                metric_type="system_memory",
                value=state.memory_percent,
                threshold=75.0,
                timestamp=state.timestamp,
                device_type=self.device_type
            ))
        
        # Network connectivity alert
        if not state.network_connected:
            alerts.append(PerformanceAlert(
                level=AlertLevel.WARNING,
                message="Network connectivity lost",
                metric_type="network",
                value=0.0,
                threshold=1.0,
                timestamp=state.timestamp,
                device_type=self.device_type
            ))
        
        # Battery alerts (if available)
        if state.battery_percent is not None:
            if state.battery_percent < 10 and not state.is_charging:
                alerts.append(PerformanceAlert(
                    level=AlertLevel.CRITICAL,
                    message=f"Battery critically low: {state.battery_percent:.0f}%",
                    metric_type="battery",
                    value=state.battery_percent,
                    threshold=10.0,
                    timestamp=state.timestamp,
                    device_type=self.device_type
                ))
        
        # Process alerts
        for alert in alerts:
            self.performance_alerts.append(alert)
            if self.alert_callback:
                try:
                    await self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    async def _cleanup_loop(self):
        """Periodically cleanup old metrics and alerts"""
        while self.is_monitoring:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_data(self):
        """Remove old metrics and alerts beyond retention period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.metrics_retention_hours)
        
        with self.metrics_lock:
            # Cleanup query metrics
            self.query_metrics = [
                m for m in self.query_metrics 
                if m.timestamp > cutoff_time
            ]
            
            # Cleanup alerts
            self.performance_alerts = [
                a for a in self.performance_alerts 
                if a.timestamp > cutoff_time
            ]
            
            # Cleanup resource states
            self.resource_states = [
                s for s in self.resource_states 
                if s.timestamp > cutoff_time
            ]
        
        logger.debug(f"Cleaned up old performance data before {cutoff_time}")
    
    def generate_performance_report(self, hours_back: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        with self.metrics_lock:
            # Filter recent metrics
            recent_metrics = [
                m for m in self.query_metrics 
                if m.timestamp > cutoff_time
            ]
            
            recent_alerts = [
                a for a in self.performance_alerts 
                if a.timestamp > cutoff_time
            ]
        
        if not recent_metrics:
            return {
                "error": "No metrics available for the specified time period",
                "device_type": self.device_type,
                "time_period_hours": hours_back
            }
        
        # Overall statistics
        total_queries = len(recent_metrics)
        successful_queries = sum(1 for m in recent_metrics if m.success)
        success_rate = successful_queries / total_queries if total_queries > 0 else 0
        
        # Performance statistics
        execution_times = [m.execution_time for m in recent_metrics]
        memory_usages = [m.memory_usage_mb for m in recent_metrics]
        cpu_usages = [m.cpu_usage_percent for m in recent_metrics]
        
        # Group by query type
        query_type_stats = {}
        for query_type in QueryType:
            type_metrics = [m for m in recent_metrics if m.query_type == query_type]
            if type_metrics:
                type_execution_times = [m.execution_time for m in type_metrics]
                type_success_rate = sum(1 for m in type_metrics if m.success) / len(type_metrics)
                
                query_type_stats[query_type.value] = {
                    "count": len(type_metrics),
                    "success_rate": round(type_success_rate * 100, 2),
                    "avg_execution_time": round(statistics.mean(type_execution_times), 4),
                    "max_execution_time": round(max(type_execution_times), 4),
                    "min_execution_time": round(min(type_execution_times), 4),
                    "median_execution_time": round(statistics.median(type_execution_times), 4)
                }
        
        # Alert summary
        alert_summary = {}
        for level in AlertLevel:
            level_alerts = [a for a in recent_alerts if a.level == level]
            alert_summary[level.value] = len(level_alerts)
        
        # Resource utilization
        recent_resources = [
            s for s in self.resource_states 
            if s.timestamp > cutoff_time
        ]
        
        resource_summary = {}
        if recent_resources:
            resource_summary = {
                "avg_cpu_percent": round(statistics.mean(s.cpu_percent for s in recent_resources), 2),
                "max_cpu_percent": round(max(s.cpu_percent for s in recent_resources), 2),
                "avg_memory_percent": round(statistics.mean(s.memory_percent for s in recent_resources), 2),
                "max_memory_percent": round(max(s.memory_percent for s in recent_resources), 2),
                "min_storage_free_mb": round(min(s.storage_free_mb for s in recent_resources), 0),
                "network_uptime_percent": round(
                    sum(1 for s in recent_resources if s.network_connected) / len(recent_resources) * 100, 2
                )
            }
        
        return {
            "device_type": self.device_type,
            "time_period_hours": hours_back,
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_stats": {
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "success_rate_percent": round(success_rate * 100, 2),
                "avg_execution_time": round(statistics.mean(execution_times), 4),
                "max_execution_time": round(max(execution_times), 4),
                "avg_memory_usage_mb": round(statistics.mean(memory_usages), 2),
                "max_memory_usage_mb": round(max(memory_usages), 2),
                "avg_cpu_usage_percent": round(statistics.mean(cpu_usages), 2)
            },
            "query_type_breakdown": query_type_stats,
            "alert_summary": alert_summary,
            "resource_utilization": resource_summary,
            "performance_baselines": {
                k.value: v for k, v in self.performance_baselines.items()
            }
        }
    
    def get_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on performance data"""
        recommendations = []
        
        # Generate report for analysis
        report = self.generate_performance_report(hours_back=24)
        
        if "error" in report:
            return ["Insufficient data for optimization recommendations"]
        
        overall_stats = report["overall_stats"]
        query_breakdown = report["query_type_breakdown"]
        resource_util = report.get("resource_utilization", {})
        
        # Execution time recommendations
        if overall_stats["avg_execution_time"] > 0.5:
            recommendations.append(
                f"Overall query performance is slow (avg: {overall_stats['avg_execution_time']:.2f}s). "
                "Consider adding database indexes or optimizing query patterns."
            )
        
        # Memory usage recommendations
        if overall_stats["avg_memory_usage_mb"] > 100:
            recommendations.append(
                f"High memory usage per query (avg: {overall_stats['avg_memory_usage_mb']:.1f}MB). "
                "Consider implementing result pagination or reducing batch sizes."
            )
        
        # Success rate recommendations
        if overall_stats["success_rate_percent"] < 95:
            recommendations.append(
                f"Query success rate is low ({overall_stats['success_rate_percent']:.1f}%). "
                "Review error patterns and implement better error handling."
            )
        
        # Query-specific recommendations
        for query_type, stats in query_breakdown.items():
            if stats["avg_execution_time"] > 1.0:
                recommendations.append(
                    f"Optimize {query_type} queries - current avg: {stats['avg_execution_time']:.2f}s"
                )
            
            if stats["success_rate"] < 90:
                recommendations.append(
                    f"Improve {query_type} reliability - current success rate: {stats['success_rate']:.1f}%"
                )
        
        # Resource-based recommendations
        if resource_util.get("avg_memory_percent", 0) > 80:
            recommendations.append(
                "System memory usage is high. Consider reducing cache sizes or optimizing memory usage."
            )
        
        if resource_util.get("min_storage_free_mb", float('inf')) < 500:
            recommendations.append(
                "Storage space is low. Implement data cleanup policies or increase retention thresholds."
            )
        
        if resource_util.get("network_uptime_percent", 100) < 95:
            recommendations.append(
                "Network connectivity issues detected. Improve offline operation capabilities."
            )
        
        # Device-specific recommendations
        if self.device_type in ['watch', 'car']:
            if overall_stats["avg_execution_time"] > 0.2:
                recommendations.append(
                    f"For {self.device_type} devices, consider more aggressive optimization. "
                    "Current performance may impact user experience."
                )
        
        return recommendations if recommendations else ["Performance is within acceptable ranges"]
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time performance metrics"""
        current_time = datetime.now(timezone.utc)
        recent_cutoff = current_time - timedelta(minutes=5)  # Last 5 minutes
        
        with self.metrics_lock:
            recent_metrics = [
                m for m in self.query_metrics 
                if m.timestamp > recent_cutoff
            ]
        
        if not recent_metrics:
            return {
                "status": "no_recent_activity",
                "current_time": current_time.isoformat()
            }
        
        # Calculate real-time stats
        current_stats = {
            "current_time": current_time.isoformat(),
            "queries_last_5min": len(recent_metrics),
            "avg_execution_time_5min": round(
                statistics.mean(m.execution_time for m in recent_metrics), 4
            ),
            "success_rate_5min": round(
                sum(1 for m in recent_metrics if m.success) / len(recent_metrics) * 100, 2
            ),
            "active_query_types": list(set(m.query_type.value for m in recent_metrics))
        }
        
        # Add current resource state if available
        if self.resource_states:
            latest_state = self.resource_states[-1]
            current_stats.update({
                "current_cpu_percent": latest_state.cpu_percent,
                "current_memory_percent": latest_state.memory_percent,
                "current_memory_available_mb": round(latest_state.memory_available_mb, 0),
                "current_storage_free_mb": round(latest_state.storage_free_mb, 0),
                "network_connected": latest_state.network_connected
            })
            
            if latest_state.battery_percent is not None:
                current_stats.update({
                    "battery_percent": latest_state.battery_percent,
                    "is_charging": latest_state.is_charging
                })
        
        return current_stats


# Example usage and testing
async def main():
    """Example usage of DatabasePerformanceMonitor"""
    
    async def mock_alert_callback(alert: PerformanceAlert):
        """Mock alert callback for testing"""
        print(f"🚨 {alert.level.value.upper()}: {alert.message}")
    
    # Create monitor for mobile device
    monitor = DatabasePerformanceMonitor('mobile', mock_alert_callback)
    await monitor.start_monitoring()
    
    try:
        # Simulate some database operations
        async def mock_fast_query():
            await asyncio.sleep(0.1)
            return ["result1", "result2"]
        
        async def mock_slow_query():
            await asyncio.sleep(2.0)  # Intentionally slow
            return ["slow_result"]
        
        async def mock_failing_query():
            raise Exception("Database connection failed")
        
        # Monitor various queries
        for i in range(10):
            try:
                # Fast query
                result = await monitor.monitor_query(
                    QueryType.CONVERSATION_SELECT, 
                    mock_fast_query
                )
                print(f"Fast query {i} completed")
                
                # Slow query (should trigger alert)
                if i == 5:
                    result = await monitor.monitor_query(
                        QueryType.CONVERSATION_INSERT,
                        mock_slow_query
                    )
                    print("Slow query completed")
                
                # Failing query (should trigger alert)
                if i == 7:
                    try:
                        await monitor.monitor_query(
                            QueryType.PREFERENCE_UPSERT,
                            mock_failing_query
                        )
                    except Exception:
                        print("Failing query handled")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Query {i} failed: {e}")
        
        # Wait a bit for resource monitoring
        await asyncio.sleep(10)
        
        # Generate performance report
        report = monitor.generate_performance_report()
        print("\n📊 Performance Report:")
        print(json.dumps(report, indent=2))
        
        # Get optimization recommendations
        recommendations = monitor.get_optimization_recommendations()
        print("\n💡 Optimization Recommendations:")
        for rec in recommendations:
            print(f"  • {rec}")
        
        # Get real-time metrics
        real_time = await monitor.get_real_time_metrics()
        print("\n⏱️  Real-time Metrics:")
        print(json.dumps(real_time, indent=2))
        
    finally:
        await monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
