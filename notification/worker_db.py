from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
DATABASE_URL = Config.SQLALCHEMY_DATABASE_URI

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)