-- ============================================================
-- TMDB Pipeline - Pending Tables
-- ============================================================
-- These tables store movie data waiting for approval.
-- Movies go here first when added via add-new or search commands.
-- After approval, data moves to the production tables.
-- ============================================================

-- Movies Pending table (mirrors movies table)
CREATE TABLE IF NOT EXISTS movies_pending (
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

    -- Indexes (fewer than production, optimized for approval workflow)
    INDEX idx_pending_movies_release_date (release_date),
    INDEX idx_pending_movies_title (title),
    FULLTEXT INDEX ft_pending_movies_title (title),
    FULLTEXT INDEX ft_pending_movies_search (title, overview)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- People Pending table
CREATE TABLE IF NOT EXISTS people_pending (
    id INT PRIMARY KEY,                    -- TMDB person ID
    name VARCHAR(255) NOT NULL,
    profile_path VARCHAR(255),
    gender INT,
    known_for_department VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_pending_people_name (name),
    FULLTEXT INDEX ft_pending_people_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Credits Pending table
CREATE TABLE IF NOT EXISTS credits_pending (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    person_id INT NOT NULL,
    credit_type VARCHAR(50) NOT NULL,
    character_name VARCHAR(255),
    credit_order INT,
    department VARCHAR(100),
    job VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_pending_credits_movie_id (movie_id),
    INDEX idx_pending_credits_person_id (person_id),
    INDEX idx_pending_credits_movie_type (movie_id, credit_type),
    FULLTEXT INDEX ft_pending_credits_character (character_name),

    -- Unique constraint
    UNIQUE KEY uk_pending_credits (movie_id, person_id, credit_type, COALESCE(job, ''), COALESCE(character_name, ''))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Genres Pending table
CREATE TABLE IF NOT EXISTS genres_pending (
    movie_id INT NOT NULL,
    genre_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (movie_id, genre_name),
    INDEX idx_pending_genres_movie_id (movie_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
