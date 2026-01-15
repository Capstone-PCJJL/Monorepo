import '../Styling.css';
import './HomeStyling.css';
import HomeCard from './HomeCard';
import LoadingSpinner from '../LoadingSpinner';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AiOutlineUser } from "react-icons/ai";
import { FaArrowLeft, FaArrowRight } from 'react-icons/fa';
import { FiRefreshCw } from 'react-icons/fi';
import useConsentGuard from '../utils/useConsentGuard';
import { useMovieContext } from '../MovieContext';

// Notification Popups
import { ToastContainer } from 'react-toastify';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';


const Home = () => {
  const loadingConsent = useConsentGuard();
  const {
    recommendedMovies,
    creditsCache,
    isMoviesLoading,
    hasFetchedMovies,
    fetchRecommendedMovies,
    prefetchCredits,
    removeFromRecommended,
  } = useMovieContext();

  const [currentIndex, setCurrentIndex] = useState(0);
  const [ratings, setRatings] = useState({});
  const [refreshing, setRefreshing] = useState(false);
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');

  const pages = [
    { title: "Home", path: "/Home" },
    { title: "Watchlist", path: '/Watchlist' },
  ];

  const renderLinks = () =>
    pages.map((page) => (
      <li key={page.title}>
        <a
          href={page.path}
          className={
            window.location.pathname.toLowerCase() === page.path.toLowerCase()
              ? "active"
              : ""
          }
          onClick={(e) => {
            e.preventDefault();
            navigate(page.path);
          }}
        >
          {page.title}
        </a>
      </li>
    ));

  // Load movies on mount
  useEffect(() => {
    // Fetch movies - context handles caching and loading state
    fetchRecommendedMovies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Prefetch credits for current and next movies
  useEffect(() => {
    if (recommendedMovies.length > 0) {
      prefetchCredits(currentIndex, recommendedMovies);
    }
  }, [currentIndex, recommendedMovies, prefetchCredits]);

  // Force refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    setCurrentIndex(0);
    await fetchRecommendedMovies(true); // force refresh
    setRefreshing(false);
  };

  // User is not interested in film
  const handleNotInterested = async (movie) => {
    try {
      removeFromRecommended(movie.id);

      const response = await fetch(`/api/v1/users/${userId}/not-interested`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movie_id: movie.id }),
      });

      if (!response.ok) throw new Error('Failed to save not interested movie');

      toast.warn('Movie added to not interested', { closeButton: false });
    } catch (error) {
      console.error('Error sending not interested to server:', error);
    }
  };

  // User adds film to watchlist
  const handleAddToWatchlist = async (movie) => {
    try {
      removeFromRecommended(movie.id);

      const response = await fetch(`/api/v1/users/${userId}/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movie_id: movie.id }),
      });

      if (!response.ok) throw new Error('Failed to add to watchlist');

      toast.success('Added to Watchlist!', { closeButton: false });
    } catch (error) {
      console.error('Error adding to watchlist:', error);
    }
  };

  const handleRatingChange = (id, rating) => {
    setRatings(prev => ({ ...prev, [id]: rating }));
  };

  // Reset currentIndex if movies list changes
  useEffect(() => {
    if (currentIndex >= recommendedMovies.length && recommendedMovies.length > 0) {
      setCurrentIndex(0);
    }
  }, [recommendedMovies, currentIndex]);

  // When user confirms their rating
  const handleConfirmRating = async (movieId) => {
    const rating = ratings[movieId];
    if (!rating) return;

    try {
      const response = await fetch(`/api/v1/users/${userId}/ratings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movie_id: movieId, rating }),
      });

      if (!response.ok) throw new Error('Failed to save rating');

      toast.success('Rating saved!', { closeButton: false });
      removeFromRecommended(movieId);
    } catch (error) {
      console.error('Error saving rating:', error);
    }
  };

  // When user likes a movie
  const handleLikeMovie = async (movie) => {
    try {
      const response = await fetch(`/api/v1/users/${userId}/likes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movie_id: movie.id }),
      });

      if (!response.ok) throw new Error('Failed to like movie');

      toast.success('Movie liked!');
      removeFromRecommended(movie.id);
    } catch (error) {
      console.error('Error liking movie:', error);
      toast.error('Error liking movie');
    }
  };

  // Get current movie with credits
  const currentMovie = recommendedMovies[currentIndex];
  const currentMovieWithCredits = currentMovie ? {
    ...currentMovie,
    credits: creditsCache[currentMovie.id] || []
  } : null;

  if (loadingConsent) return <LoadingSpinner fullscreen message="Loading..." />;

  return (
    <div>
      <header className="navbar">
        <img src="logo-placeholder.png" alt="Logo" className="navbar-logo" />
        <ul className="navbar-links">{renderLinks()}</ul>
        <div className="navbar-profile">
          <a
            href="/Profile"
            onClick={(e) => {
              e.preventDefault();
              navigate("/Profile");
            }}
          >
            <AiOutlineUser className="navbar-profile-icon" />
          </a>
        </div>
      </header>

      <div className="main-content">
        <ToastContainer position="top-right" autoClose={3000} />
        <div className="recommendation-header">
          <h2 className="recommendation-title">
            Please see your recommended films:
          </h2>

          {recommendedMovies.length > 0 && currentIndex < recommendedMovies.length && (
            <div className="navigation-buttons">
              <button
                className="nav-button"
                onClick={() => setCurrentIndex(i => Math.max(i - 1, 0))}
                disabled={currentIndex === 0}
              >
                <FaArrowLeft style={{ marginRight: '8px' }} />
                Previous
              </button>
              <button
                className="nav-button"
                onClick={() => setCurrentIndex(i => Math.min(i + 1, recommendedMovies.length - 1))}
                disabled={currentIndex >= recommendedMovies.length - 1}
              >
                Next
                <FaArrowRight style={{ marginLeft: '8px' }} />
              </button>
            </div>
          )}

          <button onClick={handleRefresh} className="refresh-button" disabled={isMoviesLoading || refreshing}>
            <FiRefreshCw style={{ marginRight: '8px' }} />
            {(isMoviesLoading || refreshing) ? 'Loading...' : 'Refresh Recommendations'}
          </button>
        </div>

        {(isMoviesLoading || (!hasFetchedMovies && recommendedMovies.length === 0)) ? (
          <LoadingSpinner fullscreen message="Loading recommendations..." />
        ) : recommendedMovies.length === 0 ? (
          <div className="no-movies">No recommendations available. Try refreshing!</div>
        ) : currentMovieWithCredits && (
          <HomeCard
            key={currentMovieWithCredits.id}
            movie={currentMovieWithCredits}
            rating={ratings[currentMovieWithCredits.id]}
            onRate={handleRatingChange}
            onNotInterested={handleNotInterested}
            onAddToWatchlist={handleAddToWatchlist}
            onConfirmRating={handleConfirmRating}
            onLike={handleLikeMovie}
          />
        )}
      </div>
    </div>
  );
}

export default Home;
