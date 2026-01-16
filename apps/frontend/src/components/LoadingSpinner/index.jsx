import React from 'react';
import './LoadingSpinner.css';

/**
 * Film clapperboard themed loading spinner
 * Animation: opens → snaps closed → spins → opens again
 * @param {string} message - Optional loading message
 * @param {boolean} fullscreen - Whether to display fullscreen overlay
 * @param {string} size - Size variant: 'small', 'medium', 'large'
 */
const LoadingSpinner = ({ message = 'Loading...', fullscreen = false, size = 'medium' }) => {
  const spinner = (
    <div className={`clapperboard-spinner clapperboard-spinner--${size}`}>
      <div className="clapperboard-container">
        <div className="clapperboard">
          {/* Top clapper (the part that snaps down) */}
          <div className="clapper-top">
            <div className="stripe"></div>
            <div className="stripe"></div>
            <div className="stripe"></div>
            <div className="stripe"></div>
            <div className="stripe"></div>
          </div>
          {/* Bottom board (the slate) */}
          <div className="clapper-bottom">
            <div className="stripe"></div>
            <div className="stripe"></div>
            <div className="stripe"></div>
            <div className="stripe"></div>
            <div className="stripe"></div>
            <div className="slate-body">
              <div className="slate-line"></div>
              <div className="slate-line"></div>
              <div className="slate-line"></div>
            </div>
          </div>
        </div>
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
