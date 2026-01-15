import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';

const MovieContext = createContext(null);

// Get user-specific cache key
const getCacheKey = (baseKey) => {
  const userId = localStorage.getItem('userId');
  return userId ? `${baseKey}_${userId}` : baseKey;
};

// Cache key bases
const CACHE_KEY_BASES = {
  RECOMMENDED: 'movieCache_recommended',
  RECOMMENDED_TIME: 'movieCache_recommendedTime',
  CREDITS: 'movieCache_credits',
};

// Load cached data from localStorage (user-specific)
const loadFromCache = (baseKey) => {
  try {
    const key = getCacheKey(baseKey);
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  } catch {
    return null;
  }
};

// Save data to localStorage (user-specific)
const saveToCache = (baseKey, data) => {
  try {
    const key = getCacheKey(baseKey);
    localStorage.setItem(key, JSON.stringify(data));
  } catch {
    // localStorage full or unavailable
  }
};

export const useMovieContext = () => {
  const context = useContext(MovieContext);
  if (!context) {
    throw new Error('useMovieContext must be used within MovieProvider');
  }
  return context;
};

export const MovieProvider = ({ children }) => {
  // Start with empty state - will load from cache when user is available
  const [recommendedMovies, setRecommendedMovies] = useState([]);
  const [creditsCache, setCreditsCache] = useState({});
  const [watchlist, setWatchlist] = useState([]);
  const [lastFetchTime, setLastFetchTime] = useState(null);

  // Track if initial fetch has been done this session (persists across navigation)
  const [isMoviesLoading, setIsMoviesLoading] = useState(false);
  const [hasFetchedMovies, setHasFetchedMovies] = useState(false);

  // Track the current userId to detect changes
  const [currentUserId, setCurrentUserId] = useState(null);

  // Track pending credit requests to avoid duplicates
  const pendingCredits = useRef({});

  // Check and sync userId on every render and storage events
  const syncWithUserId = useCallback(() => {
    const userId = localStorage.getItem('userId');

    if (userId && userId !== currentUserId) {
      // User changed or just logged in - load their cache
      setCurrentUserId(userId);
      setHasFetchedMovies(false);

      const cachedMovies = loadFromCache(CACHE_KEY_BASES.RECOMMENDED);
      const cachedCredits = loadFromCache(CACHE_KEY_BASES.CREDITS);
      const cachedTime = loadFromCache(CACHE_KEY_BASES.RECOMMENDED_TIME);

      if (cachedMovies) setRecommendedMovies(cachedMovies);
      if (cachedCredits) setCreditsCache(cachedCredits);
      if (cachedTime) setLastFetchTime(cachedTime);
    } else if (!userId && currentUserId) {
      // User logged out - clear state
      setCurrentUserId(null);
      setRecommendedMovies([]);
      setCreditsCache({});
      setWatchlist([]);
      setLastFetchTime(null);
      setHasFetchedMovies(false);
    }
  }, [currentUserId]);

  // Sync on mount and when storage changes
  useEffect(() => {
    syncWithUserId();

    // Listen for storage changes (works across tabs and when we dispatch manually)
    const handleStorage = (e) => {
      if (e.key === 'userId') {
        syncWithUserId();
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [syncWithUserId]);

  // Persist credits cache to localStorage when it changes
  useEffect(() => {
    if (Object.keys(creditsCache).length > 0) {
      saveToCache(CACHE_KEY_BASES.CREDITS, creditsCache);
    }
  }, [creditsCache]);

  // Fetch recommended movies (with stale-while-revalidate)
  const fetchRecommendedMovies = useCallback(async (forceRefresh = false) => {
    const userId = localStorage.getItem('userId');
    if (!userId) return recommendedMovies;

    const now = Date.now();
    const cacheAge = lastFetchTime ? now - lastFetchTime : Infinity;
    const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

    // Return cached data immediately if valid and not forcing refresh
    if (!forceRefresh && recommendedMovies.length > 0 && cacheAge < CACHE_TTL) {
      setHasFetchedMovies(true);
      return recommendedMovies;
    }

    setIsMoviesLoading(true);
    try {
      const response = await fetch(`/api/v1/movies/recommended/${userId}`);
      if (!response.ok) throw new Error('Failed to fetch movies');
      const movies = await response.json();

      // Update state and persist to localStorage
      setRecommendedMovies(movies);
      setLastFetchTime(now);
      saveToCache(CACHE_KEY_BASES.RECOMMENDED, movies);
      saveToCache(CACHE_KEY_BASES.RECOMMENDED_TIME, now);

      return movies;
    } catch (error) {
      console.error('Error fetching recommended movies:', error);
      return recommendedMovies; // Return cached data on error
    } finally {
      setIsMoviesLoading(false);
      setHasFetchedMovies(true);
    }
  }, [recommendedMovies, lastFetchTime]);

  // Fetch credits for a movie (with cache and request deduplication)
  const fetchCredits = useCallback(async (movieId) => {
    // Return cached if available
    if (creditsCache[movieId]) {
      return creditsCache[movieId];
    }

    // Return pending promise if already fetching
    if (pendingCredits.current[movieId]) {
      return pendingCredits.current[movieId];
    }

    // Create and track the fetch promise
    const fetchPromise = (async () => {
      try {
        const response = await fetch(`/api/v1/movies/${movieId}/credits`);
        const data = await response.json();
        const credits = data.cast || [];
        setCreditsCache(prev => ({ ...prev, [movieId]: credits }));
        return credits;
      } catch (error) {
        console.error('Error fetching credits:', error);
        return [];
      } finally {
        delete pendingCredits.current[movieId];
      }
    })();

    pendingCredits.current[movieId] = fetchPromise;
    return fetchPromise;
  }, [creditsCache]);

  // Prefetch credits for current and adjacent movies
  const prefetchCredits = useCallback(async (currentIndex, movies) => {
    if (!movies || movies.length === 0) return;

    // Prefetch current + next 2 movies
    const indicesToFetch = [currentIndex, currentIndex + 1, currentIndex + 2]
      .filter(i => i >= 0 && i < movies.length);

    const movieIds = indicesToFetch
      .map(i => movies[i]?.id)
      .filter(id => id && !creditsCache[id]);

    // Fetch all in parallel
    await Promise.all(movieIds.map(id => fetchCredits(id)));
  }, [creditsCache, fetchCredits]);

  // Fetch watchlist (with cache)
  const fetchWatchlist = useCallback(async (forceRefresh = false) => {
    const userId = localStorage.getItem('userId');
    if (!userId) return watchlist;

    if (!forceRefresh && watchlist.length > 0) {
      return watchlist;
    }

    try {
      const response = await fetch(`/api/v1/users/${userId}/watchlist`);
      if (!response.ok) throw new Error('Failed to fetch watchlist');
      const data = await response.json();
      setWatchlist(data);
      return data;
    } catch (error) {
      console.error('Error fetching watchlist:', error);
      return watchlist;
    }
  }, [watchlist]);

  // Remove movie from recommended list (local state update)
  const removeFromRecommended = useCallback((movieId) => {
    setRecommendedMovies(prev => prev.filter(m => m.id !== movieId));
  }, []);

  // Add to watchlist (local state update)
  const addToWatchlistLocal = useCallback((movie) => {
    setWatchlist(prev => [...prev, movie]);
  }, []);

  // Remove from watchlist (local state update)
  const removeFromWatchlistLocal = useCallback((movieId) => {
    setWatchlist(prev => prev.filter(m => m.id !== movieId));
  }, []);

  // Clear cache (for logout or data refresh)
  const clearCache = useCallback(() => {
    setRecommendedMovies([]);
    setCreditsCache({});
    setWatchlist([]);
    setLastFetchTime(null);
    setIsMoviesLoading(false);
    setHasFetchedMovies(false);
    // Clear localStorage cache (user-specific keys)
    localStorage.removeItem(getCacheKey(CACHE_KEY_BASES.RECOMMENDED));
    localStorage.removeItem(getCacheKey(CACHE_KEY_BASES.RECOMMENDED_TIME));
    localStorage.removeItem(getCacheKey(CACHE_KEY_BASES.CREDITS));
  }, []);

  const value = {
    recommendedMovies,
    creditsCache,
    watchlist,
    isMoviesLoading,
    hasFetchedMovies,
    fetchRecommendedMovies,
    fetchCredits,
    prefetchCredits,
    fetchWatchlist,
    removeFromRecommended,
    addToWatchlistLocal,
    removeFromWatchlistLocal,
    clearCache,
  };

  return (
    <MovieContext.Provider value={value}>
      {children}
    </MovieContext.Provider>
  );
};

export default MovieContext;
