import React from 'react';
import './LoadingSpinner.css';

/**
 * Film reel themed loading spinner
 * @param {string} message - Optional loading message
 * @param {boolean} fullscreen - Whether to display fullscreen overlay
 * @param {string} size - Size variant: 'small', 'medium', 'large'
 */
const LoadingSpinner = ({ message = 'Loading...', fullscreen = false, size = 'medium' }) => {
  const spinner = (
    <div className={`film-spinner film-spinner--${size}`}>
      <div className="film-reel">
        <div className="reel-center"></div>
        <div className="sprocket sprocket-1"></div>
        <div className="sprocket sprocket-2"></div>
        <div className="sprocket sprocket-3"></div>
        <div className="sprocket sprocket-4"></div>
        <div className="sprocket sprocket-5"></div>
        <div className="sprocket sprocket-6"></div>
      </div>
      {message && <p className="spinner-message">{message}</p>}
    </div>
  );

  if (fullscreen) {
    return <div className="spinner-fullscreen">{spinner}</div>;
  }

  return spinner;
};

export default LoadingSpinner;
