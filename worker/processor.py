from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from backend.models.database import SocialMediaPost, SentimentAnalysis

async def save_post_and_analysis(db_session, post_data, sentiment_result, emotion_result):
    # Parse created_at if it's a string
    created_at = post_data['created_at']
    if isinstance(created_at, str):
        # Handle ISO format with 'Z' suffix (ingester adds 'Z' after isoformat which already includes +00:00)
        created_at = created_at.rstrip('Z')  # Remove trailing 'Z'
        created_at = datetime.fromisoformat(created_at)
    
    # UPSERT into social_media_posts
    stmt = insert(SocialMediaPost).values(
        post_id=post_data['post_id'],
        source=post_data['source'],
        content=post_data['content'],
        author=post_data['author'],
        created_at=created_at
    ).on_conflict_do_update(
        index_elements=['post_id'],
        set_={'ingested_at': datetime.now(timezone.utc)}
    )
    await db_session.execute(stmt)
    
    # Insert analysis
    analysis = SentimentAnalysis(
        post_id=post_data['post_id'],
        model_name=sentiment_result['model_name'],
        sentiment_label=sentiment_result['sentiment_label'],
        confidence_score=sentiment_result['confidence_score'],
        emotion=emotion_result['emotion']
    )
    db_session.add(analysis)
    await db_session.commit()