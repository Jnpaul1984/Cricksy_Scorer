from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(Integer, primary_key=True)
    agentKey = Column(String(64), nullable=False)
    userId = Column(String(64), nullable=False)
    since = Column(String(32), nullable=False)
    until = Column(String(32), nullable=False)
    model = Column(String(32), nullable=False)
    tokensIn = Column(Integer, nullable=False)
    tokensOut = Column(Integer, nullable=False)
    costUsdEstimate = Column(Float, nullable=False)
    createdAt = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(32), nullable=False)
    markdownReport = Column(Text, nullable=True)
