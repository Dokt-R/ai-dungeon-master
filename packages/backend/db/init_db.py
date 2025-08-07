from sqlmodel import SQLModel
from packages.shared.models import *  # Import all models


#! Can we decommission this and move logic to db.py?
def initialize_schema(engine):
    """
    Initializes the database schema using SQLModel and a SQLAlchemy Engine.
    """
    SQLModel.metadata.create_all(engine)
