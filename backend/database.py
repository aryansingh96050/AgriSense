import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, NodeSettings

DB_FILE = os.path.join(os.path.dirname(__file__), "agrisense.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Initialize default settings row if not present
    db = SessionLocal()
    try:
        settings = db.query(NodeSettings).first()
        if not settings:
            settings = NodeSettings(
                id=1,
                active_crop="wheat",
                active_stage="crown_root",
                auto_pump_enabled=True,
                pump_override_state=False,
                farmer_phone="+919876543210",
                farmer_name="Ramesh Kumar (रमेश कुमार)",
                field_size_acres=2.5,
                alert_cooldown_mins=120
            )
            db.add(settings)
            db.commit()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
