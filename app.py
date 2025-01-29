from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from fastapi.responses import FileResponse
import shutil
import uuid
import os

# Database setup
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Create the Dog model
class Dog(Base):
    __tablename__ = 'dogs'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    breed = Column(String)
    color = Column(String)
    photo = Column(String, nullable=True)

# Create the database tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()
from fastapi.staticfiles import StaticFiles

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500","https://incomparable-starburst-0415bc.netlify.app"],  # or "*", but not recommended for production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

UPLOAD_FOLDER = "uploads"  # Local folder for images
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoint to add a new dog with photo
@app.post("/", response_model=dict)
async def create_dog(
    name: str = Form(...),
    breed: str = Form(...),
    color: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    unique_filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    file_location = os.path.join(UPLOAD_FOLDER, unique_filename)

    # Save file
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Store in DB with correct image URL
    db_dog = Dog(
        name=name,
        breed=breed,
        color=color,
        photo=f"http://127.0.0.1:8000/uploads/{unique_filename}"
    )
    db.add(db_dog)
    db.commit()
    db.refresh(db_dog)

    return {
        "id": db_dog.id,
        "name": db_dog.name,
        "breed": db_dog.breed,
        "color": db_dog.color,
        "photo": db_dog.photo
    }


# Serve uploaded images
@app.get("/uploads/{filename}")
async def serve_image(filename: str):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Image not found")

# Fetch all dogs
@app.get("/dogs")
async def get_all_dogs(db: Session = Depends(get_db)):
    dogs = db.query(Dog).all()
    return [{"id": dog.id, "name": dog.name, "breed": dog.breed, "color": dog.color, "photo": dog.photo} for dog in dogs]
