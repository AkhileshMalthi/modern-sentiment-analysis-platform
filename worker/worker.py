import os
import asyncio
import logging
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker
from backend.services.sentiment_analyzer import SentimentAnalyzer
from processor import save_post_and_analysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SentimentWorker:
    def __init__(self, redis_client, db_session_maker, stream_name, consumer_group):
        self.redis = redis_client
        self.db_session_maker = db_session_maker
        self.stream_name = stream_name
        self.group = consumer_group
        self.analyzer = None  # Lazy initialization
        self.consumer_name = f"worker_{os.getpid()}"
    
    def _get_analyzer(self):
        """Lazy load the analyzer on first use"""
        if self.analyzer is None:
            logger.info("Initializing SentimentAnalyzer...")
            self.analyzer = SentimentAnalyzer(model_type='local')
            logger.info("SentimentAnalyzer initialized successfully")
        return self.analyzer

    async def setup(self):
        try:
            await self.redis.xgroup_create(self.stream_name, self.group, mkstream=True)
        except:
            pass # Already exists

    async def process_message(self, message_id, message_data):
        try:
            content = message_data.get('content')
            analyzer = self._get_analyzer()  # Lazy load
            sentiment = await analyzer.analyze_sentiment(content)
            emotion = await analyzer.analyze_emotion(content)
            
            async with self.db_session_maker() as session:
                await save_post_and_analysis(session, message_data, sentiment, emotion)
            
            await self.redis.xack(self.stream_name, self.group, message_id)
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    async def run(self, batch_size=10):
        await self.setup()
        while True:
            # XREADGROUP pulls messages not yet acknowledged
            streams = await self.redis.xreadgroup(self.group, self.consumer_name, {self.stream_name: ">"}, count=batch_size, block=5000)
            for _, messages in streams:
                tasks = [self.process_message(m_id, m_data) for m_id, m_data in messages]
                await asyncio.gather(*tasks)

if __name__ == "__main__":
    import os
    from sqlalchemy.ext.asyncio import create_async_engine

    async def start_worker():
        # 0. Load environment variables
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable not set")
        
        REDIS_HOST = os.getenv("REDIS_HOST")
        if not REDIS_HOST:
            raise ValueError("REDIS_HOST environment variable not set")
        
        REDIS_STREAM_NAME = os.getenv("REDIS_STREAM_NAME")
        if not REDIS_STREAM_NAME:
            raise ValueError("REDIS_STREAM_NAME environment variable not set")
        
        REDIS_CONSUMER_GROUP = os.getenv("REDIS_CONSUMER_GROUP")
        if not REDIS_CONSUMER_GROUP:
            raise ValueError("REDIS_CONSUMER_GROUP environment variable not set")

        # 1. Setup DB Engine
        engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        
        # 2. Setup Redis
        redis_client = Redis(host=REDIS_HOST, decode_responses=True)

        # 3. Initialize Worker
        worker = SentimentWorker(
            redis_client=redis_client,
            db_session_maker=async_session,
            stream_name=REDIS_STREAM_NAME,
            consumer_group=REDIS_CONSUMER_GROUP
        )
        
        logger.info("Worker is starting up...")  # Use logger instead of print
        print("Worker is starting up...") # Also print for Docker logs
        await worker.run()

    asyncio.run(start_worker())