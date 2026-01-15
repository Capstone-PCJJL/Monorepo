import React from 'react';
import { FaHeart } from 'react-icons/fa';

// HomeCard contains all the information required for a user to rate and review initial movies
const HomeCard = ({ movie, rating, onRate, onNotInterested, onAddToWatchlist, onConfirmRating, onLike}) => {
  if (!movie) return null; // safety check

  return (
    <div className="home-card">
      <img
        src={`https://image.tmdb.org/t/p/w500${movie.poster_path}`}
        alt={`${movie.title} Poster`}
        className="movie-poster"
        loading="lazy"
      />
      <div className="movie-info">
        <div className="movie-header">
          <h2 className="movie-title">
            {movie.title} <span className="movie-date">({new Date(movie.release_date).getFullYear()})</span>
          </h2>
          <p className="movie-genres">
            <span className="genre-label">Genres:</span>{' '}
            <span className="genre-list">{movie.genres?.join(', ')}</span>
          </p>
          <p className="movie-runtime">
            <span className="runtime-label">Runtime:</span>{' '}
            <span className="runtime-list">{movie.runtime} minutes</span>
          </p>
          <p className="movie-overview">{movie.overview}</p>
          <div className="movie-credits">
            <span className="director-label">Director: </span>
            <span className="director-name">
              {movie.credits
                ?.filter(c => c.credit_type?.toLowerCase() === "crew")
                .map(c => c.name)
                .join(', ')}
            </span>
          </div>
          <div className="movie-actors">
            <span className="actors-label">Cast: </span>
            <span className="actors-names">
              {movie.credits
                ?.filter(c => c.credit_type?.toLowerCase() !== "crew")
                .map(c => c.name)
                .join(', ')}
            </span>
          </div>
        </div>
        <div className="button-row">
          {onRate && (
            <div className="movie-rating">
              <label htmlFor={`rating-${movie.id}`}>Rate this movie:</label>
              <select
                id={`rating-${movie.id}`}
                value={rating || ""}
                onChange={(e) => onRate(movie.id, e.target.value)}
              >
                <option value="" disabled>
                  Select rating
                </option>
                {[0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5].map((r) => (
                  <option key={r} value={r}>
                    {r} ★
                  </option>
                ))}
              </select>
              {rating && (
                <button
                  className="confirm-rating-button"
                  onClick={() => onConfirmRating(movie.id)}
                >
                  ✅ Confirm Rating
                </button>
              )}
            </div>
          )}
          {onLike && (
            <button className="like-button" onClick={() => onLike(movie)}>
              <FaHeart className="heart-icon" />
              Like
            </button>
          )}
          {onAddToWatchlist && (
            <button className="add-to-watchlist-button" onClick={() => onAddToWatchlist(movie)}>
              ➕ Add to Watchlist
            </button>
          )}

          {onNotInterested && (
            <button className="not-interested-button" onClick={() => onNotInterested(movie)}>
              Not Interested
            </button>
          )}
        </div>
      </div>
    </div>
  );  
};

export default HomeCard;