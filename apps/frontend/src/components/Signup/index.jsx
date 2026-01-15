import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import FirebaseContext from '../Firebase/context';
import LoadingSpinner from '../LoadingSpinner';
import './SignUp.css';

const SignUp = () => {
  const firebase = useContext(FirebaseContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!email || !password || !confirmPassword) {
      setError('All fields are required');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const authUser = await firebase.doCreateUserWithEmailAndPassword(email, password);
      console.log('User created successfully:', authUser);
      // localStorage.setItem('userId', authUser.user.uid); // ✅ fixed variable name
      const firebaseId = authUser.user.uid;
      await fetch('/api/v1/users/firebase', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ firebase_id: firebaseId }),
      });
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      // navigate('/import-csv');
      navigate('/verifyemail')
    } catch (error) {
      console.error('Error creating user:', error);
      setError(error.message);
    }
  };

  const isInvalid = !email || !password || !confirmPassword || loading;

  return (
    <div className="container_s">
      <div className="form">
        <h1>Sign Up</h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
            />
          </div>

          <div className="form-group">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
            />
          </div>

          <div className="form-group">
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm Password"
              required
            />
          </div>

          {error && <div className="error">{error}</div>}

          <button
            className="signup-btn"
            type="submit"
            disabled={isInvalid}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <LoadingSpinner size="small" message="" />
                Creating Account...
              </span>
            ) : 'Sign Up'}
          </button>
        </form>

        <div className="signup-footer">
          <p>
            Already have an account? <a href="/login">Login</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignUp;
