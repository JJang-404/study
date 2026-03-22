import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

sqlite_conn = sqlite3.connect("movies.db")
sqlite_cur = sqlite_conn.cursor()

pg_conn = psycopg2.connect(os.environ.get("POSTGRESQL_URL"))
pg_cur = pg_conn.cursor()

# movies 마이그레이션
sqlite_cur.execute(
    "SELECT id, title, release_date, director, genre, poster_url FROM movies"
)
movies = sqlite_cur.fetchall()
for movie in movies:
    pg_cur.execute(
        "INSERT INTO movies (id, title, release_date, director, genre, poster_url) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        movie,
    )


# revies 마이그레이션
sqlite_cur.execute(
    "SELECT id, movie_id, author, content, sentiment_score, sentiment_label, created_at FROM reviews"
)
reviews = sqlite_cur.fetchall()
for review in reviews:
    pg_cur.execute(
        "INSERT INTO reviews (id, movie_id, author, content, sentiment_score, sentiment_label, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        review,
    )

pg_conn.commit()
print(f"완료: 영화 {len(movies)}개, 리뷰 {len(reviews)}개")

sqlite_conn.close()
pg_conn.close()
