"""
SmartSelf Learning Chatbot - Admin Dashboard
Administrative interface for system management and monitoring.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from ..chatbot.learning_chatbot import LearningChatbot, create_learning_chatbot
from ..learning.continuous_learner import ContinuousLearner, LearningConfig
from ..monitoring.analytics import LearningAnalytics, PerformanceMonitor
from ..knowledge.knowledge_integrator import KnowledgeIntegrator

logger = logging.getLogger(__name__)


# Admin API Models
class SystemConfig(BaseModel):
    max_concurrent_crawls: int = 10
    crawl_rate_limit: int = 1
    daily_crawl_limit: int = 1000
    min_quality_score: float = 0.3
    auto_learning: bool = True


class LearningTask(BaseModel):
    urls: List[str]
    priority: str = "normal"  # low, normal, high
    schedule: Optional[str] = None


class UserManagement(BaseModel):
    action: str  # create, update, delete, ban, unban
    user_id: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None


class AdminDashboard:
    """Administrative dashboard for system management"""
    
    def __init__(self):
        """Initialize admin dashboard"""
        self.app = FastAPI(
            title="Learning Chatbot Admin Dashboard",
            description="Administrative interface for system management",
            version="1.0.0"
        )
        
        # Initialize components
        self.chatbot = None
        self.analytics = LearningAnalytics()
        self.performance_monitor = PerformanceMonitor(self.analytics)
        
        # Admin sessions
        self.admin_sessions: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: List[WebSocket] = []
        
        # System metrics cache
        self.metrics_cache = {}
        self.cache_ttl = 30  # seconds
        self.last_cache_update = None
        
        # Setup templates
        self.templates = Jinja2Templates(directory="admin/templates")
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Admin dashboard initialized")
    
    def _setup_routes(self):
        """Setup admin dashboard routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def admin_home(request: Request):
            """Admin dashboard home page"""
            return self.templates.TemplateResponse("admin_dashboard.html", {
                "request": request,
                "title": "Admin Dashboard"
            })
        
        @self.app.get("/api/system/status")
        async def get_system_status():
            """Get comprehensive system status"""
            try:
                if not self.chatbot:
                    return JSONResponse({
                        "status": "error",
                        "message": "Chatbot not initialized"
                    })
                
                # Get chatbot status
                chatbot_status = await self.chatbot.get_chatbot_status()
                
                # Get analytics summaries
                learning_summary = self.analytics.get_learning_summary(24)
                chat_summary = self.analytics.get_chat_summary(24)
                system_summary = self.analytics.get_system_summary(24)
                
                # Get performance metrics
                performance_metrics = self.analytics.get_real_time_metrics()
                
                return JSONResponse({
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat(),
                    "chatbot": chatbot_status,
                    "analytics": {
                        "learning": learning_summary,
                        "chat": chat_summary,
                        "system": system_summary
                    },
                    "performance": performance_metrics
                })
                
            except Exception as e:
                logger.error(f"Error getting system status: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.get("/api/system/metrics")
        async def get_system_metrics():
            """Get detailed system metrics"""
            try:
                # Check cache
                current_time = datetime.utcnow()
                if (self.last_cache_update and 
                    (current_time - self.last_cache_update).seconds < self.cache_ttl and
                    self.metrics_cache):
                    return JSONResponse(self.metrics_cache)
                
                # Generate fresh metrics
                metrics = await self._generate_system_metrics()
                
                # Update cache
                self.metrics_cache = metrics
                self.last_cache_update = current_time
                
                return JSONResponse(metrics)
                
            except Exception as e:
                logger.error(f"Error getting system metrics: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.post("/api/system/config")
        async def update_system_config(config: SystemConfig):
            """Update system configuration"""
            try:
                if not self.chatbot:
                    return JSONResponse({
                        "status": "error",
                        "message": "Chatbot not initialized"
                    })
                
                # Validate configuration
                if config.max_concurrent_crawls < 1 or config.max_concurrent_crawls > 100:
                    return JSONResponse({
                        "status": "error",
                        "message": "max_concurrent_crawls must be between 1 and 100"
                    })
                
                if config.crawl_rate_limit < 0.1 or config.crawl_rate_limit > 10:
                    return JSONResponse({
                        "status": "error",
                        "message": "crawl_rate_limit must be between 0.1 and 10"
                    })
                
                # Update configuration
                old_config = self.chatbot.learning_config
                self.chatbot.learning_config = LearningConfig(
                    max_concurrent_crawls=config.max_concurrent_crawls,
                    crawl_rate_limit=config.crawl_rate_limit,
                    daily_crawl_limit=config.daily_crawl_limit,
                    min_quality_score=config.min_quality_score
                )
                
                # Restart learning with new config if needed
                if config.auto_learning and not self.chatbot.is_learning:
                    await self.chatbot.continuous_learner.start_learning()
                elif not config.auto_learning and self.chatbot.is_learning:
                    await self.chatbot.continuous_learner.stop_learning()
                
                return JSONResponse({
                    "status": "success",
                    "message": "Configuration updated successfully",
                    "old_config": old_config.__dict__,
                    "new_config": config.__dict__
                })
                
            except Exception as e:
                logger.error(f"Error updating system config: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.post("/api/learning/start")
        async def start_learning():
            """Start the learning system"""
            try:
                if not self.chatbot:
                    return JSONResponse({
                        "status": "error",
                        "message": "Chatbot not initialized"
                    })
                
                if self.chatbot.is_learning:
                    return JSONResponse({
                        "status": "warning",
                        "message": "Learning system is already running"
                    })
                
                await self.chatbot.continuous_learner.start_learning()
                
                return JSONResponse({
                    "status": "success",
                    "message": "Learning system started successfully"
                })
                
            except Exception as e:
                logger.error(f"Error starting learning: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.post("/api/learning/stop")
        async def stop_learning():
            """Stop the learning system"""
            try:
                if not self.chatbot:
                    return JSONResponse({
                        "status": "error",
                        "message": "Chatbot not initialized"
                    })
                
                if not self.chatbot.is_learning:
                    return JSONResponse({
                        "status": "warning",
                        "message": "Learning system is not running"
                    })
                
                await self.chatbot.continuous_learner.stop_learning()
                
                return JSONResponse({
                    "status": "success",
                    "message": "Learning system stopped successfully"
                })
                
            except Exception as e:
                logger.error(f"Error stopping learning: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.post("/api/learning/task")
        async def create_learning_task(task: LearningTask):
            """Create and execute learning task"""
            try:
                if not self.chatbot:
                    return JSONResponse({
                        "status": "error",
                        "message": "Chatbot not initialized"
                    })
                
                # Validate URLs
                if not task.urls:
                    return JSONResponse({
                        "status": "error",
                        "message": "No URLs provided"
                    })
                
                # Execute learning task
                result = await self.chatbot.manual_learn(task.urls)
                
                # Log task for analytics
                await self._log_learning_task(task, result)
                
                return JSONResponse({
                    "status": "success",
                    "message": "Learning task completed",
                    "task": task.__dict__,
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Error creating learning task: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.get("/api/knowledge/stats")
        async def get_knowledge_stats():
            """Get knowledge base statistics"""
            try:
                if not self.chatbot:
                    return JSONResponse({
                        "status": "error",
                        "message": "Chatbot not initialized"
                    })
                
                stats = await self.chatbot.knowledge_integrator.get_stats()
                
                return JSONResponse({
                    "status": "success",
                    "stats": stats
                })
                
            except Exception as e:
                logger.error(f"Error getting knowledge stats: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.post("/api/knowledge/cleanup")
        async def cleanup_knowledge():
            """Clean up knowledge base"""
            try:
                if not self.chatbot:
                    return JSONResponse({
                        "status": "error",
                        "message": "Chatbot not initialized"
                    })
                
                # Perform cleanup
                await self.chatbot.knowledge_integrator.cleanup_old_data(days_old=30)
                await self.chatbot.knowledge_integrator.optimize_index()
                
                return JSONResponse({
                    "status": "success",
                    "message": "Knowledge base cleanup completed"
                })
                
            except Exception as e:
                logger.error(f"Error cleaning up knowledge: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.get("/api/analytics/report")
        async def generate_analytics_report():
            """Generate comprehensive analytics report"""
            try:
                report = self.analytics.generate_learning_report()
                
                return JSONResponse({
                    "status": "success",
                    "report": report
                })
                
            except Exception as e:
                logger.error(f"Error generating analytics report: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.get("/api/analytics/export")
        async def export_analytics():
            """Export analytics data"""
            try:
                # Export to JSON
                export_data = {
                    "learning_metrics": [asdict(m) for m in self.analytics.learning_metrics],
                    "chat_metrics": [asdict(m) for m in self.analytics.chat_metrics],
                    "system_metrics": [asdict(m) for m in self.analytics.system_metrics],
                    "export_timestamp": datetime.utcnow().isoformat()
                }
                
                return JSONResponse({
                    "status": "success",
                    "data": export_data
                })
                
            except Exception as e:
                logger.error(f"Error exporting analytics: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.get("/api/users")
        async def get_users():
            """Get user statistics and management"""
            try:
                # This would integrate with a user management system
                # For now, return mock data
                users_data = {
                    "total_users": 100,
                    "active_users": 45,
                    "new_users_today": 5,
                    "top_users": [
                        {"id": "user1", "messages": 150, "satisfaction": 4.5},
                        {"id": "user2", "messages": 120, "satisfaction": 4.7},
                        {"id": "user3", "messages": 95, "satisfaction": 4.2}
                    ]
                }
                
                return JSONResponse({
                    "status": "success",
                    "users": users_data
                })
                
            except Exception as e:
                logger.error(f"Error getting user data: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.post("/api/users/manage")
        async def manage_users(user_mgmt: UserManagement):
            """Manage users (create, update, delete, ban, unban)"""
            try:
                # This would integrate with a user management system
                # For now, just log the action
                logger.info(f"User management action: {user_mgmt.action}")
                
                return JSONResponse({
                    "status": "success",
                    "message": f"User management action '{user_mgmt.action}' completed"
                })
                
            except Exception as e:
                logger.error(f"Error managing users: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.get("/api/logs")
        async def get_logs(lines: int = 100):
            """Get system logs"""
            try:
                log_file = Path("logs/learning_chatbot.log")
                
                if not log_file.exists():
                    return JSONResponse({
                        "status": "success",
                        "logs": []
                    })
                
                # Read last N lines
                with open(log_file, 'r') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                return JSONResponse({
                    "status": "success",
                    "logs": recent_lines,
                    "total_lines": len(all_lines)
                })
                
            except Exception as e:
                logger.error(f"Error getting logs: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time updates"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Receive message
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    
                    if message_data.get('type') == 'ping':
                        await websocket.send_text(json.dumps({'type': 'pong'}))
                    elif message_data.get('type') == 'subscribe':
                        # Subscribe to real-time updates
                        await self._handle_subscription(websocket, message_data.get('data'))
                    elif message_data.get('type') == 'command':
                        # Handle admin commands
                        await self._handle_admin_command(websocket, message_data.get('data'))
                        
            except WebSocketDisconnect:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
        
        @self.app.post("/api/system/shutdown")
        async def shutdown_system():
            """Shutdown the system (admin only)"""
            try:
                if self.chatbot:
                    await self.chatbot.stop()
                
                await self.performance_monitor.stop_monitoring()
                
                return JSONResponse({
                    "status": "success",
                    "message": "System shutdown initiated"
                })
                
            except Exception as e:
                logger.error(f"Error shutting down system: {e}")
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)
    
    async def _generate_system_metrics(self) -> Dict[str, Any]:
        """Generate comprehensive system metrics"""
        try:
            # Get basic metrics
            learning_summary = self.analytics.get_learning_summary(24)
            chat_summary = self.analytics.get_chat_summary(24)
            system_summary = self.analytics.get_system_summary(24)
            
            # Get detailed metrics
            performance_metrics = self.analytics.get_real_time_metrics()
            
            # Calculate derived metrics
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "learning": {
                    "urls_crawled_24h": learning_summary.get('total_urls_crawled', 0),
                    "content_processed_24h": learning_summary.get('total_content_processed', 0),
                    "knowledge_added_24h": learning_summary.get('total_knowledge_added', 0),
                    "average_quality": learning_summary.get('average_quality_score', 0),
                    "learning_efficiency": learning_summary.get('learning_efficiency', 0),
                    "active_sources": len(self.chatbot.continuous_learner.active_sources) if self.chatbot else 0
                },
                "chat": {
                    "conversations_24h": chat_summary.get('total_conversations', 0),
                    "messages_24h": chat_summary.get('total_messages', 0),
                    "average_response_time": chat_summary.get('average_response_time', 0),
                    "user_satisfaction": chat_summary.get('average_user_satisfaction', 0),
                    "knowledge_usage_rate": chat_summary.get('average_knowledge_usage_rate', 0)
                },
                "system": {
                    "cpu_usage": system_summary.get('average_cpu_usage', 0),
                    "memory_usage": system_summary.get('average_memory_usage', 0),
                    "disk_usage": system_summary.get('average_disk_usage', 0),
                    "system_health": system_summary.get('system_health', 'unknown'),
                    "uptime": performance_metrics.get('system', {}).get('uptime', 0)
                },
                "performance": performance_metrics,
                "alerts": self._generate_system_alerts()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error generating system metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def _generate_system_alerts(self) -> List[Dict[str, Any]]:
        """Generate system alerts"""
        alerts = []
        
        try:
            # Check learning alerts
            if self.chatbot and self.chatbot.is_learning:
                learning_stats = self.chatbot.continuous_learner.get_learning_progress()
                if learning_stats.get('stats', {}).get('average_quality_score', 1.0) < 0.3:
                    alerts.append({
                        "type": "warning",
                        "message": "Low content quality detected",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Check system alerts
            system_metrics = self.analytics.get_system_summary(1)
            if system_metrics.get('average_memory_usage', 0) > 0.8:
                alerts.append({
                    "type": "critical",
                    "message": "High memory usage detected",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            if system_metrics.get('average_cpu_usage', 0) > 0.9:
                alerts.append({
                    "type": "warning",
                    "message": "High CPU usage detected",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")
        
        return alerts
    
    async def _handle_subscription(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle WebSocket subscription"""
        subscription_type = data.get('type')
        
        if subscription_type == 'metrics':
            # Send current metrics
            metrics = await self._generate_system_metrics()
            await websocket.send_text(json.dumps({
                'type': 'metrics_update',
                'data': metrics
            }))
    
    async def _handle_admin_command(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle admin commands via WebSocket"""
        command = data.get('command')
        params = data.get('params', {})
        
        try:
            if command == 'restart_learning':
                if self.chatbot:
                    await self.chatbot.continuous_learner.stop_learning()
                    await self.chatbot.continuous_learner.start_learning()
                
                await websocket.send_text(json.dumps({
                    'type': 'command_response',
                    'data': {'status': 'success', 'message': 'Learning system restarted'}
                }))
            
            elif command == 'clear_cache':
                self.metrics_cache = {}
                self.last_cache_update = None
                
                await websocket.send_text(json.dumps({
                    'type': 'command_response',
                    'data': {'status': 'success', 'message': 'Cache cleared'}
                }))
            
            else:
                await websocket.send_text(json.dumps({
                    'type': 'command_response',
                    'data': {'status': 'error', 'message': f'Unknown command: {command}'}
                }))
        
        except Exception as e:
            await websocket.send_text(json.dumps({
                'type': 'command_response',
                'data': {'status': 'error', 'message': str(e)}
            }))
    
    async def _log_learning_task(self, task: LearningTask, result: Dict[str, Any]):
        """Log learning task for analytics"""
        try:
            # Create log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'task': task.__dict__,
                'result': result
            }
            
            # Save to log file
            log_file = Path("logs/learning_tasks.log")
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
        except Exception as e:
            logger.error(f"Error logging learning task: {e}")
    
    async def broadcast_update(self, message_type: str, data: Dict[str, Any]):
        """Broadcast update to all connected admins"""
        if not self.websocket_connections:
            return
        
        message = json.dumps({
            'type': message_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)
    
    async def start(self, host: str = "0.0.0.0", port: int = 8001):
        """Start the admin dashboard"""
        # Initialize chatbot
        self.chatbot = create_learning_chatbot()
        await self.chatbot.start()
        
        # Start performance monitoring
        await self.performance_monitor.start_monitoring()
        
        # Start web server
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        logger.info(f"Admin dashboard started on {host}:{port}")
        await server.serve()
    
    async def stop(self):
        """Stop the admin dashboard"""
        if self.chatbot:
            await self.chatbot.stop()
        
        await self.performance_monitor.stop_monitoring()


# Create admin dashboard instance
admin_dashboard = AdminDashboard()

# Expose FastAPI app for deployment
app = admin_dashboard.app


# Main function for running the admin dashboard
async def main():
    """Main function to run the admin dashboard"""
    await admin_dashboard.start()


if __name__ == "__main__":
    asyncio.run(main())
