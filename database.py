import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Prefer canonical DATABASE_URL (e.g. provided by Render or other managed DB)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
	SQLALCHEMY_DATABASE_URL = DATABASE_URL
else:
	DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
	DB_DATABASE = os.getenv("DB_DATABASE", "agile_db")
	DB_USER = os.getenv("DB_USER", "root")
	DB_PASSWORD = os.getenv("DB_PASSWORD", "")
	# Default to MySQL using PyMySQL
	SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
