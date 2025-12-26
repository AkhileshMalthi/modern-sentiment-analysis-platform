"""
Data Aggregation Service

This module provides business logic for aggregating sentiment data
across different time periods and sources.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import redis.asyncio as aioredis

from models.database import SocialMediaPost, SentimentAnalysis


class AggregatorService:
    """
    Service for aggregating sentiment data with caching
    """
    
    def __init__(self, db_session: AsyncSession, redis_client: Optional[aioredis.Redis] = None):
        """
        Initialize aggregator service
        
        Args:
            db_session: SQLAlchemy async session
            redis_client: Optional Redis client for caching
        """
        self.db = db_session
        self.redis = redis_client
    
    async def get_sentiment_aggregate(
        self,
        period: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get sentiment counts aggregated by time period
        
        Args:
            period: Aggregation granularity ('minute', 'hour', or 'day')
            start_date: Start of time range (default: 24 hours ago)
            end_date: End of time range (default: now)
            source: Optional filter by platform
        
        Returns:
            Dictionary with aggregated sentiment data including:
            - period, start_date, end_date
            - data: List of time buckets with sentiment counts and percentages
            - summary: Total counts across all periods
        """
        # Set default dates
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(hours=24)
        
        # Check cache first
        if self.redis:
            cached_data = await self._get_from_cache(period, source, start_date, end_date)
            if cached_data:
                return cached_data
        
        # Build aggregation query using date_trunc for PostgreSQL
        time_bucket = func.date_trunc(period, SentimentAnalysis.analyzed_at).label('time_bucket')
        
        query = select(
            time_bucket,
            SentimentAnalysis.sentiment_label,
            func.count(SentimentAnalysis.id).label('count'),
            func.avg(SentimentAnalysis.confidence_score).label('avg_confidence')
        ).join(
            SocialMediaPost,
            SentimentAnalysis.post_id == SocialMediaPost.post_id
        ).where(
            and_(
                SentimentAnalysis.analyzed_at >= start_date,
                SentimentAnalysis.analyzed_at <= end_date
            )
        )
        
        if source:
            query = query.where(SocialMediaPost.source == source)
        
        query = query.group_by(time_bucket, SentimentAnalysis.sentiment_label).order_by(time_bucket)
        
        # Execute query
        result = await self.db.execute(query)
        rows = result.all()
        
        # Process results
        time_buckets = self._organize_by_timestamp(rows)
        data, summary = self._calculate_percentages_and_summary(time_buckets)
        
        response = {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": data,
            "summary": summary
        }
        
        # Cache the result
        if self.redis:
            await self._save_to_cache(period, source, start_date, end_date, response)
        
        return response
    
    async def get_sentiment_distribution(
        self,
        hours: int = 24,
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current sentiment distribution for dashboard
        
        Args:
            hours: Look back period in hours (1-168)
            source: Optional filter by platform
        
        Returns:
            Dictionary with sentiment distribution, percentages, and top emotions
        """
        # Check cache first
        if self.redis:
            cache_key = f"sentiment_cache:distribution:{hours}:{source or 'all'}"
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    result = json.loads(cached_data)
                    result["cached"] = True
                    return result
            except Exception as e:
                print(f"Redis cache read error: {e}")
        
        # Calculate time threshold
        threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Build query for sentiment counts
        query = select(
            SentimentAnalysis.sentiment_label,
            func.count(SentimentAnalysis.id).label('count')
        ).join(
            SocialMediaPost,
            SentimentAnalysis.post_id == SocialMediaPost.post_id
        ).where(
            SentimentAnalysis.analyzed_at >= threshold
        )
        
        if source:
            query = query.where(SocialMediaPost.source == source)
        
        query = query.group_by(SentimentAnalysis.sentiment_label)
        
        # Execute sentiment count query
        result = await self.db.execute(query)
        sentiment_counts = {row[0]: int(row[1]) for row in result.all()}
        
        # Get emotion counts
        top_emotions = await self._get_top_emotions(threshold, source)
        
        # Calculate totals and percentages
        distribution: Dict[str, int] = {
            "positive": sentiment_counts.get("positive", 0),
            "negative": sentiment_counts.get("negative", 0),
            "neutral": sentiment_counts.get("neutral", 0)
        }
        total = sum(distribution.values())
        
        percentages = self._calculate_percentages(distribution, total)
        
        cached_at = datetime.now(timezone.utc).isoformat()
        
        response = {
            "timeframe_hours": hours,
            "source": source,
            "distribution": distribution,
            "total": total,
            "percentages": percentages,
            "top_emotions": top_emotions,
            "cached": False,
            "cached_at": cached_at
        }
        
        # Cache the result
        if self.redis:
            cache_key = f"sentiment_cache:distribution:{hours}:{source or 'all'}"
            try:
                await self.redis.setex(cache_key, 60, json.dumps(response))
            except Exception as e:
                print(f"Redis cache write error: {e}")
        
        return response
    
    def _organize_by_timestamp(self, rows) -> Dict[str, Dict]:
        """
        Organize database rows by timestamp buckets
        
        Args:
            rows: List of query result rows
        
        Returns:
            Dictionary mapping timestamps to sentiment counts
        """
        time_buckets: Dict[str, Dict] = {}
        for row in rows:
            timestamp = row.time_bucket.isoformat()
            if timestamp not in time_buckets:
                time_buckets[timestamp] = {
                    "timestamp": timestamp,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "total_count": 0,
                    "confidence_sum": 0,
                    "confidence_count": 0
                }
            
            sentiment = row.sentiment_label
            count_value = row.count
            time_buckets[timestamp][f"{sentiment}_count"] = count_value
            time_buckets[timestamp]["total_count"] += count_value
            time_buckets[timestamp]["confidence_sum"] += (row.avg_confidence or 0) * count_value
            time_buckets[timestamp]["confidence_count"] += count_value
        
        return time_buckets
    
    def _calculate_percentages_and_summary(self, time_buckets: Dict) -> tuple[List[Dict], Dict]:
        """
        Calculate percentages for each time bucket and overall summary
        
        Args:
            time_buckets: Dictionary of time buckets with counts
        
        Returns:
            Tuple of (data list, summary dict)
        """
        data = []
        summary = {"total_posts": 0, "positive_total": 0, "negative_total": 0, "neutral_total": 0}
        
        for timestamp in sorted(time_buckets.keys()):
            bucket = time_buckets[timestamp]
            total = bucket["total_count"]
            
            if total > 0:
                positive_pct = round((bucket["positive_count"] / total) * 100, 2)
                negative_pct = round((bucket["negative_count"] / total) * 100, 2)
                neutral_pct = round((bucket["neutral_count"] / total) * 100, 2)
                avg_conf = round(bucket["confidence_sum"] / bucket["confidence_count"], 2) if bucket["confidence_count"] > 0 else 0.0
            else:
                positive_pct = negative_pct = neutral_pct = 0.0
                avg_conf = 0.0
            
            data.append({
                "timestamp": timestamp,
                "positive_count": bucket["positive_count"],
                "negative_count": bucket["negative_count"],
                "neutral_count": bucket["neutral_count"],
                "total_count": total,
                "positive_percentage": positive_pct,
                "negative_percentage": negative_pct,
                "neutral_percentage": neutral_pct,
                "average_confidence": avg_conf
            })
            
            summary["total_posts"] += total
            summary["positive_total"] += bucket["positive_count"]
            summary["negative_total"] += bucket["negative_count"]
            summary["neutral_total"] += bucket["neutral_count"]
        
        return data, summary
    
    def _calculate_percentages(self, distribution: Dict[str, int], total: int) -> Dict[str, float]:
        """
        Calculate percentage distribution of sentiments
        
        Args:
            distribution: Dictionary with sentiment counts
            total: Total count
        
        Returns:
            Dictionary with sentiment percentages
        """
        if total > 0:
            return {
                "positive": round((distribution["positive"] / total) * 100, 2),
                "negative": round((distribution["negative"] / total) * 100, 2),
                "neutral": round((distribution["neutral"] / total) * 100, 2)
            }
        return {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
    
    async def _get_top_emotions(self, threshold: datetime, source: Optional[str] = None) -> Dict[str, int]:
        """
        Get top 5 emotions from the time period
        
        Args:
            threshold: Minimum timestamp for emotions
            source: Optional filter by platform
        
        Returns:
            Dictionary mapping emotions to counts
        """
        emotion_query = select(
            SentimentAnalysis.emotion,
            func.count(SentimentAnalysis.id).label('count')
        ).join(
            SocialMediaPost,
            SentimentAnalysis.post_id == SocialMediaPost.post_id
        ).where(
            SentimentAnalysis.analyzed_at >= threshold,
            SentimentAnalysis.emotion.isnot(None)
        )
        
        if source:
            emotion_query = emotion_query.where(SocialMediaPost.source == source)
        
        emotion_query = emotion_query.group_by(SentimentAnalysis.emotion).order_by(
            func.count(SentimentAnalysis.id).desc()
        ).limit(5)
        
        emotion_result = await self.db.execute(emotion_query)
        return {str(row[0]): int(row[1]) for row in emotion_result.all()}
    
    async def _get_from_cache(
        self,
        period: str,
        source: Optional[str],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict]:
        """
        Try to retrieve cached aggregate data
        
        Returns:
            Cached data dict or None if not found
        """
        if not self.redis:
            return None
            
        cache_key = f"sentiment_cache:aggregate:{period}:{source or 'all'}:{start_date.isoformat()}:{end_date.isoformat()}"
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"Redis cache read error: {e}")
        return None
    
    async def _save_to_cache(
        self,
        period: str,
        source: Optional[str],
        start_date: datetime,
        end_date: datetime,
        response: Dict
    ):
        """
        Save aggregate data to cache with 60-second TTL
        """
        if not self.redis:
            return
            
        cache_key = f"sentiment_cache:aggregate:{period}:{source or 'all'}:{start_date.isoformat()}:{end_date.isoformat()}"
        try:
            await self.redis.setex(cache_key, 60, json.dumps(response))
        except Exception as e:
            print(f"Redis cache write error: {e}")
