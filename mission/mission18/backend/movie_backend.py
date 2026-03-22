from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import List, Optional
from transformers import AutoTokenizer, pipeline
from optimum.onnxruntime import ORTModelForSequenceClassification
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uvicorn
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# 1. Database Configuration
SQLALCHEMY_DATABASE_URL = os.environ.get("POSTGRESQL_URL", "sqlite:///./movies.db")

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 2. Database Models
class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    release_date = Column(String)
    director = Column(String)
    genre = Column(String)
    poster_url = Column(String)
    reviews = relationship(
        "Review", back_populates="movie", cascade="all, delete-orphan"
    )


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"))
    author = Column(String)
    content = Column(String)
    sentiment_score = Column(Float)
    sentiment_label = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    movie = relationship("Movie", back_populates="reviews")


Base.metadata.create_all(bind=engine)


# 3. Pydantic Models
class ReviewCreate(BaseModel):
    movie_id: int
    author: str
    content: str


class ReviewRead(BaseModel):
    id: int
    movie_id: int
    author: str
    content: str
    sentiment_score: float
    sentiment_label: str
    created_at: datetime

    class Config:
        from_attributes = True


class MovieCreate(BaseModel):
    title: str
    release_date: str
    director: str
    genre: str
    poster_url: str


class MovieRead(BaseModel):
    id: int
    title: str
    release_date: str
    director: str
    genre: str
    poster_url: str
    average_rating: Optional[float] = 0.0

    class Config:
        from_attributes = True


# 4. Sentiment Analysis Setup (ONNX Runtime)
ONNX_DIR = "./koelectra_onnx"
print("Loading Sentiment Analysis Model (KoELECTRA ONNX)...")
try:
    _model = ORTModelForSequenceClassification.from_pretrained(ONNX_DIR)
    _tokenizer = AutoTokenizer.from_pretrained(ONNX_DIR)
    classifier = pipeline("sentiment-analysis", model=_model, tokenizer=_tokenizer)
    print("ONNX 모델 로드 완료")
except Exception as e:
    print(f"ONNX 로드 실패: {e} → HuggingFace 원본 모델로 fallback")
    classifier = pipeline(
        "sentiment-analysis", model="daekeun-ml/koelectra-small-v3-nsmc"
    )

# 라벨 매핑 진단
_pos_test = classifier("정말 재미있고 감동적인 영화입니다")[0]
_neg_test = classifier("최악의 영화, 시간 낭비였습니다")[0]
print(f"[진단] 긍정 문장 → label={_pos_test['label']}, score={_pos_test['score']:.3f}")
print(f"[진단] 부정 문장 → label={_neg_test['label']}, score={_neg_test['score']:.3f}")

# 5. 비동기 추론용 ThreadPoolExecutor (CPU 바운드 작업을 이벤트 루프 밖에서 실행)
_executor = ThreadPoolExecutor(max_workers=2)

# 6. FastAPI App

app = FastAPI(title="Movie Review API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 배포 후 Streamlit Cloud 주소로 교체
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# API Endpoints
@app.post("/movies/", response_model=MovieRead)
def create_movie(movie: MovieCreate, db: Session = Depends(get_db)):
    db_movie = Movie(**movie.model_dump())
    db.add(db_movie)
    db.commit()
    db.refresh(db_movie)
    return db_movie


@app.get("/movies/", response_model=List[MovieRead])
def get_movies(db: Session = Depends(get_db)):
    movies = db.query(Movie).all()
    result = []
    for movie in movies:
        avg_rating = (
            db.query(func.avg(Review.sentiment_score))
            .filter(Review.movie_id == movie.id)
            .scalar()
            or 0.0
        )
        movie_data = MovieRead.from_orm(movie)
        movie_data.average_rating = round(float(avg_rating) * 5, 1)
        result.append(movie_data)
    return result


@app.put("/movies/{movie_id}", response_model=MovieRead)
def update_movie(movie_id: int, movie: MovieCreate, db: Session = Depends(get_db)):
    db_movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    for key, value in movie.model_dump().items():
        setattr(db_movie, key, value)
    db.commit()
    db.refresh(db_movie)
    return db_movie


@app.delete("/movies/{movie_id}")
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    db.delete(movie)
    db.commit()
    return {"message": "Movie deleted"}


@app.post("/reviews/", response_model=ReviewRead)
async def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    loop = asyncio.get_event_loop()
    analysis = await loop.run_in_executor(
        _executor, lambda: classifier(review.content)[0]
    )
    raw_label = analysis["label"]
    score = analysis["score"]

    # koelectra-nsmc: 0=부정, 1=긍정
    if raw_label == "1":
        label = "positive"
        s_score = score
    else:  # "0"
        label = "negative"
        s_score = 1.0 - score

    db_review = Review(
        movie_id=review.movie_id,
        author=review.author,
        content=review.content,
        sentiment_score=s_score,
        sentiment_label=label,
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


@app.delete("/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(review)
    db.commit()
    return {"message": "Review deleted"}


@app.get("/reviews/", response_model=List[ReviewRead])
def get_reviews(movie_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Review)
    if movie_id is not None:
        query = query.filter(Review.movie_id == movie_id)
    return query.order_by(Review.created_at.desc()).limit(10).all()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
