import os
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class ContractMetadata(Base):
    __tablename__ = 'contract_metadata'

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False, default='PROCESSING')
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    file_path = Column(String, nullable=True)  # S3 Key
    processing_time_ms = Column(Float, nullable=True)
    clauses_processed = Column(Integer, nullable=True)

class PolicyDecision(Base):
    __tablename__ = 'policy_decisions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(String, ForeignKey('contract_metadata.id'), nullable=False)
    clause_id = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    requires_human_review = Column(String, nullable=False) # Stored as string "true"/"false" or boolean
    rule_id = Column(String, nullable=True)

    contract = relationship("ContractMetadata", backref="policy_decisions")
