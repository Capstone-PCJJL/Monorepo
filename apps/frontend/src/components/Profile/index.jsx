import '../Styling.css';
import * as React from 'react';
import { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AiOutlineUser } from "react-icons/ai";
import { FiLogOut } from 'react-icons/fi';
import useConsentGuard from '../utils/useConsentGuard';
import { useMovieContext } from '../MovieContext';
import { FirebaseContext } from '../Firebase';
import LoadingSpinner from '../LoadingSpinner';


function Profile() {
    const loadingConsent = useConsentGuard();
    const firebase = useContext(FirebaseContext);
    const { clearCache } = useMovieContext();

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
    
    const isActiveProfile = window.location.pathname.toLowerCase() === "/profile";

    const handleLogout = async () => {
        try {
            clearCache();
            localStorage.removeItem('userId');
            localStorage.removeItem('userConsented');
            localStorage.removeItem('consentVerifiedAt');
            await firebase.doSignOut();
            navigate('/');
        } catch (error) {
            console.error('Error signing out:', error);
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
                        className={isActiveProfile ? "active" : ""}
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
                <div className="profile-container">
                    <h2 style={{ color: 'white', marginBottom: '20px' }}>Profile</h2>
                    <button className="logout-button" onClick={handleLogout}>
                        <FiLogOut style={{ marginRight: '8px' }} />
                        Sign Out
                    </button>
                </div>
            </div>
        </div>
    );
}

export default Profile;
