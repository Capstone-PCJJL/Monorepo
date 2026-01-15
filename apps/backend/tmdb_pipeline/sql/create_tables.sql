-- ============================================================
-- TMDB Pipeline - Production Tables
-- ============================================================
-- These tables store approved movie data that is visible to users.
-- Run this script to create the production tables with proper indexes.
-- ============================================================

-- Movies table
CREATE TABLE IF NOT EXISTS movies (
    id INT PRIMARY KEY,                    -- TMDB movie ID
    title VARCHAR(255) NOT NULL,
    original_title VARCHAR(255),
    overview TEXT,
    release_date DATE,
    runtime INT,
    status VARCHAR(50),
    tagline TEXT,
    vote_average FLOAT,
    vote_count INT,
    popularity FLOAT,
    poster_path VARCHAR(255),
    backdrop_path VARCHAR(255),
    budget BIGINT,
    revenue BIGINT,
    imdb_id VARCHAR(25),
    original_language VARCHAR(25),
    origin_country JSON,
    english_name VARCHAR(255),
    spoken_language_codes VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes for common queries
    INDEX idx_movies_release_date (release_date),
    INDEX idx_movies_popularity (popularity),
    INDEX idx_movies_vote_average (vote_average),
    INDEX idx_movies_title (title),
    INDEX idx_movies_imdb_id (imdb_id),
    FULLTEXT INDEX ft_movies_title (title),
    FULLTEXT INDEX ft_movies_search (title, overview)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- People table (actors, directors, etc.)
CREATE TABLE IF NOT EXISTS people (
    id INT PRIMARY KEY,                    -- TMDB person ID
    name VARCHAR(255) NOT NULL,
    profile_path VARCHAR(255),
    gender INT,                            -- 0=unknown, 1=female, 2=male, 3=non-binary
    known_for_department VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_people_name (name),
    FULLTEXT INDEX ft_people_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Credits table (links movies to people)
-- Note: A person can have multiple roles in a movie (actor + producer)
-- So we use (movie_id, person_id, credit_type, job) as a unique constraint
CREATE TABLE IF NOT EXISTS credits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    person_id INT NOT NULL,
    credit_type VARCHAR(50) NOT NULL,      -- 'cast' or 'crew'
    character_name VARCHAR(255),           -- For cast
    credit_order INT,                      -- For cast ordering
    department VARCHAR(100),               -- For crew
    job VARCHAR(100),                      -- For crew (e.g., 'Director')
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_credits_movie_id (movie_id),
    INDEX idx_credits_person_id (person_id),
    INDEX idx_credits_type (credit_type),
    INDEX idx_credits_movie_type (movie_id, credit_type),
    FULLTEXT INDEX ft_credits_character (character_name),

    -- Unique constraint to prevent duplicates
    UNIQUE KEY uk_credits (movie_id, person_id, credit_type, COALESCE(job, ''), COALESCE(character_name, ''))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Genres table (links movies to genres)
CREATE TABLE IF NOT EXISTS genres (
    movie_id INT NOT NULL,
    genre_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (movie_id, genre_name),
    INDEX idx_genres_movie_id (movie_id),
    INDEX idx_genres_genre_name (genre_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
