from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.common.schema import AgentStatus, TaskStatus, TaskAction
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./aicipc.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AgentModel(Base):
    __tablename__ = "agents"

    rack_id = Column(String, primary_key=True, index=True)
    status = Column(String, default="OFFLINE")
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    ip_address = Column(String)
    dut_count = Column(Float)
    metadata_json = Column(JSON) # To store full RegisterRequest data

class TaskModel(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, index=True)
    rack_id = Column(String, index=True)
    dut_id = Column(String)
    action = Column(String)
    status = Column(String, default="PENDING")
    progress = Column(Float, default=0.0)
    message = Column(String)
    params = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
