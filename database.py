import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# The format for a passwordless connection is "username:@"
# The database name at the end is 'agile_db'.
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@127.0.0.1/agile_db"


engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
