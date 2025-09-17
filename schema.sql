-- =============================================================
-- 스마트미러 헤어 추천·합성 서비스 — 데이터베이스 스키마
-- Target: PostgreSQL
-- File  : schema.sql
-- =============================================================

-- 0) (선택) 필요 확장 설치 예시: PostGIS/pgvector를 쓰고 싶을 때
-- CREATE EXTENSION IF NOT EXISTS postgis;
-- CREATE EXTENSION IF NOT EXISTS vector;

-- 1) 서비스 전용 스키마 생성
CREATE SCHEMA IF NOT EXISTS hair;

-- 2) 검색 경로를 hair 우선으로 설정 (세션 기준)
SET search_path TO hair, public;

-- 3) 테이블 생성 ------------------------------------------------

-- 3.1 users: 사용자 계정
CREATE TABLE IF NOT EXISTS users (
  id          BIGSERIAL PRIMARY KEY,
  email       TEXT UNIQUE NOT NULL,
  name        TEXT,
  created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 3.2 uploads: 업로드한 원본 이미지 메타데이터
CREATE TABLE IF NOT EXISTS uploads (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  image_url   TEXT NOT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 3.3 styles: 스타일 카탈로그
CREATE TABLE IF NOT EXISTS styles (
  id               BIGSERIAL PRIMARY KEY,
  name             TEXT NOT NULL,
  tags             TEXT[] DEFAULT '{}',
  sample_image_url TEXT
);

-- 3.4 compose_results: 업로드 × 스타일 합성 결과
CREATE TABLE IF NOT EXISTS compose_results (
  id           BIGSERIAL PRIMARY KEY,
  upload_id    BIGINT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
  style_id     BIGINT NOT NULL REFERENCES styles(id)  ON DELETE RESTRICT,
  result_url   TEXT NOT NULL,
  created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (upload_id, style_id)
);

-- 3.5 salons: 미용실
CREATE TABLE IF NOT EXISTS salons (
  id       BIGSERIAL PRIMARY KEY,
  name     TEXT NOT NULL,
  lat      DOUBLE PRECISION NOT NULL,
  lng      DOUBLE PRECISION NOT NULL,
  rating   NUMERIC(2,1),
  tags     TEXT[] DEFAULT '{}'
);

-- 3.6 designers: 디자이너 (매장 소속)
CREATE TABLE IF NOT EXISTS designers (
  id        BIGSERIAL PRIMARY KEY,
  salon_id  BIGINT NOT NULL REFERENCES salons(id) ON DELETE CASCADE,
  name      TEXT NOT NULL,
  tags      TEXT[] DEFAULT '{}'
);

-- 3.7 bookings: 예약
CREATE TABLE IF NOT EXISTS bookings (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
  designer_id  BIGINT NOT NULL REFERENCES designers(id) ON DELETE CASCADE,
  time         TIMESTAMP NOT NULL,
  note         TEXT,
  status       TEXT NOT NULL DEFAULT 'pending'
);

-- 4) 인덱스 생성 ------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_uploads_user_id      ON uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_designers_salon_id   ON designers(salon_id);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id     ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_designer_t  ON bookings(designer_id, time);
CREATE INDEX IF NOT EXISTS idx_styles_tags_gin      ON styles USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_salons_tags_gin      ON salons USING GIN (tags);

-- 5) 샘플 데이터 시드 -------------------------------------------
INSERT INTO users(email, name) VALUES
('alice@example.com','Alice'),
('bob@example.com','Bob')
ON CONFLICT (email) DO NOTHING;

INSERT INTO styles(name, tags, sample_image_url) VALUES
('볼륨매직',        ARRAY['펌','볼륨'], 'https://example.com/sample1.jpg'),
('애쉬브라운 염색', ARRAY['염색','브라운'], 'https://example.com/sample2.jpg'),
('뱅헤어',          ARRAY['컷트','앞머리'], 'https://example.com/sample3.jpg');

INSERT INTO salons(name, lat, lng, rating, tags) VALUES
('민재헤어 수원역점', 37.265, 127.000, 4.7, ARRAY['염색','펌']),
('수원뷰티 살롱',    37.280, 127.020, 4.5, ARRAY['컷트','펌']);

INSERT INTO designers(salon_id, name, tags) VALUES
(1, '곽민재', ARRAY['볼륨','펌']),
(1, '이서',   ARRAY['염색','탈색']),
(2, '헤다찬', ARRAY['컷트','펌']);

INSERT INTO uploads(user_id, image_url) VALUES
(1, 'https://example.com/upload/alice_001.jpg'),
(2, 'https://example.com/upload/bob_001.jpg');

INSERT INTO compose_results(upload_id, style_id, result_url) VALUES
(1, 1, 'https://example.com/result/alice_volumemagic.jpg'),
(1, 2, 'https://example.com/result/alice_ashbrown.jpg');

INSERT INTO bookings(user_id, designer_id, time, note)
VALUES (1, 1, NOW() + INTERVAL '2 days', '볼륨매직 상담');

-- 6) 동작 확인용 쿼리 ------------------------------------------
-- 예시 1: '펌' 태그 포함 스타일 조회
-- SELECT id, name, tags FROM styles WHERE tags @> ARRAY['펌']::text[];

-- 예시 2: 특정 업로드 × 스타일 결과 조회
-- SELECT cr.result_url, s.name FROM compose_results cr
-- JOIN styles s ON s.id = cr.style_id
-- WHERE cr.upload_id = 1;

-- =============================================================
-- EOF
-- =============================================================
