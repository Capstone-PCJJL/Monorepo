import React from 'react';
import '../Styling.css';

// MovieCard containing all information associated with the movie
const SavedMovie = ({ movie, rating, onRate, onNotInterested, onRemoveFromWatchlist }) => (
    <div className="movie-card">
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
                <div className="genre-runtime-box" style={{ display: 'flex', gap: '1rem' }}>
                    <p className="movie-genres">
                        <span className="genre-label">Genres:</span>{' '}
                        <span className="genre-list">{movie.genres?.join(', ')}</span>
                    </p>
                    <p className="movie-runtime">
                        <span className="runtime-label">Runtime:</span>{' '}
                        <span className="runtime-list">{movie.runtime} minutes</span>
                    </p>
                </div>
                <p className="movie-overview">
                    {movie.overview?.length > 700
                        ? movie.overview.slice(0, 700) + '...'
                        : movie.overview}
                </p>
                <div className="movie-credits">
                    <div className="movie-director">
                        <span className="director-label">Director: </span>
                        <span className="director-name">
                        {movie.credits
                            ?.filter(c => c.credit_type?.toLowerCase() === "crew")
                            .map(c => c.name)
                            .join(', ')}
                        </span>
                    </div>
                    <div className="movie-actors">
                        <span className="actors-label">Actors: </span>
                        <span className="actors-names">
                        {movie.credits
                            ?.filter(c => c.credit_type?.toLowerCase() !== "crew")
                            .map(c => c.name)
                            .join(', ')}
                        </span>
                    </div>
                </div>
            </div>
            {onRate && (
                <div className="movie-rating">
                    <label htmlFor={`rating-${movie.id}`}>Rate this movie:</label>
                    <select
                        id={`rating-${movie.id}`}
                        value={rating || ""}
                        onChange={(e) => onRate(movie.id, e.target.value)}
                    >
                        <option value="" disabled>Select rating</option>
                        {[0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5].map(r => (
                            <option key={r} value={r}>{r} ★</option>
                        ))}
                    </select>
                </div>
            )}
        </div>
        {(onRemoveFromWatchlist || onNotInterested) && (
            <div className='movie-actions'>
                {onRemoveFromWatchlist && (
                    <button
                        className="remove-from-watchlist-button"
                        onClick={() => onRemoveFromWatchlist(movie.id)}
                    >
                        ➖Remove from Watchlist
                    </button>
                )}
                {onNotInterested && (
                    <button className="not-interested-button" onClick={() => onNotInterested(movie)}>
                        Not Interested
                    </button>
                )}
            </div>
        )}
    </div>
);

export default SavedMovie;