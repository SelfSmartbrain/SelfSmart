'''procedural_memory.py

Stores procedural knowledge such as skills, workflows, and execution patterns.
Implemented as a PostgreSQL table accessed via SQLAlchemy.
''' 

from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProceduralMemory(Base):
    __tablename__ = "procedural_memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True)
    code_snippet = Column(JSON, nullable=False)  # Store code as JSON (e.g., {'language': 'python', 'code': '...'} )

    def __repr__(self):
        return f"<ProceduralMemory id={self.id} name={self.name}>"

# Helper functions for CRUD operations
def add_procedure(session, name: str, description: str, code: Dict[str, Any]):
    proc = ProceduralMemory(name=name, description=description, code_snippet=code)
    session.add(proc)
    session.commit()
    return proc

def get_procedure(session, name: str):
    return session.query(ProceduralMemory).filter_by(name=name).first()
