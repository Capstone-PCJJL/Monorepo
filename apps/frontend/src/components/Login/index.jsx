import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import FirebaseContext from '../Firebase/context';
import LoadingSpinner from '../LoadingSpinner';
import './Login.css';
import { Link } from 'react-router-dom';

const Login = () => {
  const firebase = useContext(FirebaseContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const getOrCreateUser = async (firebaseId) => {
    const response = await fetch('/api/v1/users/firebase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ firebase_id: firebaseId }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to link user');
    }

    return data.user_id;
  };

  const handleAuth = async (firebaseUser) => {
    const firebaseId = firebaseUser.uid;
    try {
      const userId = await getOrCreateUser(firebaseId);
      localStorage.setItem('userId', userId);
      localStorage.setItem('firebaseId', firebaseId);
      // Notify MovieContext that userId changed
      window.dispatchEvent(new StorageEvent('storage', { key: 'userId', newValue: userId }));
      navigate('/consent'); // route to consent page after login
    } catch (err) {
      setError(err.message);
    }
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const userCredential = await firebase.doSignInWithEmailAndPassword(email, password);
      const user = userCredential.user;

      await user.reload(); // Make sure we get latest user state from Firebase

      if (!user.emailVerified) {
        setError('Please verify your email before logging in.');
        navigate('/verifyemail');
        return;
      }

      await handleAuth(user);
      setEmail('');
      setPassword('');
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const onGoogleSignIn = async () => {
    setLoading(true);
    setError(null);
    try {
      const userCredential = await firebase.doSignInWithGoogle(); // ✅ capture return value
      // localStorage.setItem('userId', userCredential.user.uid); // ✅ safe now
      // navigate('/Home');
      await handleAuth(userCredential.user);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };


  const isInvalid = password === '' || email === '' || loading;

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>Login</h1>
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email Address"
              className="form-control"
            />
          </div>
          <div className="form-group">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              className="form-control"
            />
          </div>
          <button
            type="submit"
            disabled={isInvalid}
            className={`login-button ${isInvalid ? 'disabled' : ''}`}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <LoadingSpinner size="small" message="" />
                Logging in...
              </span>
            ) : 'Login'}
          </button>

          <button
            type="button"
            onClick={onGoogleSignIn}
            className="login-button google-login"
            disabled={loading}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <LoadingSpinner size="small" message="" />
                Logging in...
              </span>
            ) : 'Login with Google'}
          </button>

          {error && <div className="error-message">{error}</div>}
        </form>

        <div className="login-footer">
          <Link to="/forgot-password" className="forgot-password">
            Forgot Password?
          </Link>
          <p>
            Don't have an account? <a href="/signup">Sign Up</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login; 

