"""Alert Service for monitoring sentiment metrics and triggering alerts"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func, and_
import asyncio
import os
import redis.asyncio as aioredis
from models.database import SocialMediaPost, SentimentAnalysis, SentimentAlert


class AlertService:
    """
    Monitors sentiment metrics and triggers alerts on anomalies
    """
    
    def __init__(self, db_session_maker, redis_client):
        """
        Initialize with configuration from environment variables
        
        Loads:
        - ALERT_NEGATIVE_RATIO_THRESHOLD (default: 2.0)
        - ALERT_WINDOW_MINUTES (default: 5)
        - ALERT_MIN_POSTS (default: 10)
        """
        self.db_session_maker = db_session_maker
        self.redis_client = redis_client
        
        # Load configuration from environment
        self.negative_ratio_threshold = float(os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", "2.0"))
        self.window_minutes = int(os.getenv("ALERT_WINDOW_MINUTES", "5"))
        self.min_posts = int(os.getenv("ALERT_MIN_POSTS", "10"))
    
    async def check_thresholds(self) -> Optional[dict]:
        """
        Check if current sentiment metrics exceed alert thresholds
        
        Logic:
        1. Count positive/negative posts in last ALERT_WINDOW_MINUTES
        2. If total posts < ALERT_MIN_POSTS, return None (not enough data)
        3. Calculate ratio = negative_count / positive_count
        4. If ratio > ALERT_NEGATIVE_RATIO_THRESHOLD, trigger alert
        
        Returns:
            dict if alert triggered:
            {
                "alert_triggered": True,
                "alert_type": "high_negative_ratio",
                "threshold": 2.0,
                "actual_ratio": 3.5,
                "window_minutes": 5,
                "metrics": {
                    "positive_count": 10,
                    "negative_count": 35,
                    "neutral_count": 15,
                    "total_count": 60
                },
                "timestamp": "2025-01-15T10:30:00Z"
            }
            
            None if no alert
        """
        async with self.db_session_maker() as db:
            # Calculate time window
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(minutes=self.window_minutes)
            
            # Query sentiment counts in the window
            query = select(
                SentimentAnalysis.sentiment_label,
                func.count(SentimentAnalysis.id).label('count')
            ).where(
                SentimentAnalysis.analyzed_at >= window_start
            ).group_by(SentimentAnalysis.sentiment_label)
            
            result = await db.execute(query)
            rows = result.all()
            
            # Build metrics
            metrics = {
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "total_count": 0
            }
            
            for row in rows:
                metrics[f"{row.sentiment_label}_count"] = row.count
                metrics["total_count"] += row.count
            
            # Check if we have enough data
            if metrics["total_count"] < self.min_posts:
                return None
            
            # Calculate ratio (avoid division by zero)
            if metrics["positive_count"] == 0:
                # If no positive posts, any negative posts trigger alert
                if metrics["negative_count"] > 0:
                    actual_ratio = float('inf')
                else:
                    return None
            else:
                actual_ratio = metrics["negative_count"] / metrics["positive_count"]
            
            # Check if threshold exceeded
            if actual_ratio > self.negative_ratio_threshold:
                return {
                    "alert_triggered": True,
                    "alert_type": "high_negative_ratio",
                    "threshold": self.negative_ratio_threshold,
                    "actual_ratio": actual_ratio if actual_ratio != float('inf') else 999.99,
                    "window_minutes": self.window_minutes,
                    "window_start": window_start,
                    "window_end": now,
                    "metrics": metrics,
                    "timestamp": now.isoformat()
                }
            
            return None
    
    async def save_alert(self, alert_data: dict) -> int:
        """
        Save alert to database
        
        Args:
            alert_data: Alert information from check_thresholds()
        
        Returns:
            int: Database ID of saved alert
        
        Inserts into sentiment_alerts table
        """
        async with self.db_session_maker() as db:
            alert = SentimentAlert(
                alert_type=alert_data["alert_type"],
                threshold_value=alert_data["threshold"],
                actual_value=alert_data["actual_ratio"],
                window_start=alert_data["window_start"],
                window_end=alert_data["window_end"],
                post_count=alert_data["metrics"]["total_count"],
                triggered_at=datetime.now(timezone.utc),
                details={
                    "positive_count": alert_data["metrics"]["positive_count"],
                    "negative_count": alert_data["metrics"]["negative_count"],
                    "neutral_count": alert_data["metrics"]["neutral_count"]
                }
            )
            
            db.add(alert)
            await db.commit()
            await db.refresh(alert)
            
            return alert.id  # type: ignore
    
    async def run_monitoring_loop(self, check_interval_seconds: int = 60):
        """
        Continuously monitor and trigger alerts
        
        Args:
            check_interval_seconds: How often to check (default: 60)
        
        Loop:
        1. Check thresholds
        2. If alert triggered, save to database and log
        3. Sleep for check_interval_seconds
        4. Repeat
        """
        print(f"🚨 Alert monitoring started (check interval: {check_interval_seconds}s)")
        print(f"   - Threshold: {self.negative_ratio_threshold}x negative/positive ratio")
        print(f"   - Window: {self.window_minutes} minutes")
        print(f"   - Min posts: {self.min_posts}")
        
        while True:
            try:
                # Check thresholds
                alert_data = await self.check_thresholds()
                
                if alert_data:
                    # Save alert to database
                    alert_id = await self.save_alert(alert_data)
                    
                    # Log alert
                    print(f"\nALERT TRIGGERED (ID: {alert_id})")
                    print(f"   Type: {alert_data['alert_type']}")
                    print(f"   Ratio: {alert_data['actual_ratio']:.2f} (threshold: {alert_data['threshold']})")
                    print(f"   Metrics: {alert_data['metrics']}")
                    print(f"   Time: {alert_data['timestamp']}\n")
                
            except Exception as e:
                print(f"Error in alert monitoring loop: {e}")
            
            # Wait before next check
            await asyncio.sleep(check_interval_seconds)


# Singleton instance functions
_alert_service_instance = None

async def get_alert_service():
    """Get or create alert service singleton"""
    global _alert_service_instance
    
    if _alert_service_instance is None:
        # Setup database
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://sentiment_user:secure_password_123@localhost:5432/sentiment_db")
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
        
        # Setup Redis
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
        redis_client = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
        
        _alert_service_instance = AlertService(AsyncSessionLocal, redis_client)
    
    return _alert_service_instance


async def start_alert_monitoring():
    """Start the alert monitoring service"""
    alert_service = await get_alert_service()
    await alert_service.run_monitoring_loop()


if __name__ == "__main__":
    # Run alert service standalone
    asyncio.run(start_alert_monitoring())
