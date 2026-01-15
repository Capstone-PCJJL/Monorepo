import React from 'react';
import './LandingPage.css'; // External CSS

const Project = () => {
  return (
    <div className="landing-page">
      <div className="container">
        <h1 className="logo">Welcome to CinemaStack!</h1>
        <p className="description">
          Discover your next favorite movie with our intelligent recommendation system.
          Developed by University of Waterloo students, CinemaStack analyzes your preferences
          and suggests films that match your taste, helping you discover hidden gems. Note your
          movie data may be used by researchers at the University of Waterloo. Your private
          information like emails and passwords will remain confidential.
        </p>
        <div className="button-container">
          <a href="/signup" className="btn btn-primary">Sign Up</a>
          <a href="/login" className="btn btn-secondary">Log In</a>
        </div>
      </div>
    </div>
  );
};

export default Project;