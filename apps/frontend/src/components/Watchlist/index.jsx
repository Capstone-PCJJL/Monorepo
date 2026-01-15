import '../Styling.css';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AiOutlineUser } from "react-icons/ai";
import MovieCard from './SavedMovie';
import LoadingSpinner from '../LoadingSpinner';
import useConsentGuard from '../utils/useConsentGuard';
import { useMovieContext } from '../MovieContext';

const Watchlist = () => {
    const loadingConsent = useConsentGuard();
    const { watchlist, fetchWatchlist, removeFromWatchlistLocal } = useMovieContext();

    const userId = localStorage.getItem('userId');
    const [loading, setLoading] = useState(false);

    const pages = [
        { title: "Home", path: "/Home" },
        { title: "Watchlist", path: '/Watchlist' },
    ];

    const navigate = useNavigate();

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

    useEffect(() => {
        const loadWatchlist = async () => {
            if (watchlist.length === 0) {
                setLoading(true);
                await fetchWatchlist();
                setLoading(false);
            }
        };
        loadWatchlist();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleRemoveFromWatchlist = async (movieId) => {
        try {
            const res = await fetch(`/api/v1/users/${userId}/watchlist/${movieId}`, {
                method: 'DELETE',
            });

            if (!res.ok) throw new Error('Failed to remove movie from watchlist');

            removeFromWatchlistLocal(movieId);
        } catch (err) {
            console.error('Error removing movie:', err);
        }
    };

    if (loadingConsent) return <LoadingSpinner fullscreen message="Loading..." />;

    return (
        <div>
            <header className="navbar">
                <img
                    src="logo-placeholder.png"
                    alt="Logo"
                    className="navbar-logo"
                />
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
                <h2 style={{ color: 'white', fontWeight: 'bold', marginLeft: '20px' }}>
                    Your Watchlist
                </h2>
                {loading ? (
                    <LoadingSpinner fullscreen message="Loading watchlist..." />
                ) : watchlist.length > 0 ? (
                    watchlist.map((movie) => (
                        <MovieCard
                            key={movie.id}
                            movie={movie}
                            onRemoveFromWatchlist={handleRemoveFromWatchlist}
                        />
                    ))
                ) : (
                    <p style={{ color: 'white', marginLeft: '20px' }}>No movies in your watchlist yet.</p>
                )}
            </div>
        </div>
    );
}

export default Watchlist;
