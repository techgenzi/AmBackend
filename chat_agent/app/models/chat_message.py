from .. import db_client
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, Boolean, Float
from sqlalchemy.sql import func

class ChatMessage(db_client.Model):
    __tablename__ = 'fabrico_chat_messages'

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    company_code = Column(Integer)
    compcode = Column(String(50))
    message = Column(Text)
    response = Column(Text)
    image_url = Column(String(500))
    
    # Token and cost tracking
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    token_cost = Column(Float, default=0.0)
    
    # Quality metrics
    relevance_score = Column(Float, default=0.0)
    retry_attempts = Column(Integer, default=0)
    
    # Provider, model, endpoint, and tools
    provider = Column(String(50), default="Google / Gemma")
    model = Column(String(250), default="gemma4:31b")
    llm_url = Column(String(500))
    tools_used = Column(Text)
    
    # Timestamps
    created_on = Column(DateTime, default=func.now())
    timestamp = Column(DateTime, default=func.now())
    deleted = Column(Boolean, default=False)
