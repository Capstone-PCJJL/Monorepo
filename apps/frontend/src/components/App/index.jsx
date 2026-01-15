import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Home from '../Home';
import Watchlist from '../Watchlist';
import Login from '../Login';
import Signup from '../Signup';
import Profile from '../Profile';
import ImportCsv from '../ImportCsv';
import Project from '../Project';
import Consent from '../Consent';
import VerifyEmail from '../VerifyEmail';
import ForgotPassword from '../ForgotPassword';
import { MovieProvider } from '../MovieContext';

const App = () => {

  return (
    <Router>
      <MovieProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
        <Route path="/Watchlist" element={<Watchlist />} />
        <Route path="/Home" element={<Home/>} />
        <Route path="/Profile" element={<Profile />} />
        <Route path="/project" element={<Project />} />
        <Route path="/consent" element={<Consent />} />
        <Route path="/import-csv" element={<ImportCsv />} />
        <Route path="/verifyemail" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />

        {/* Redirects */}
        <Route path="/" element={<Navigate to="/project" replace />} />
        <Route path="*" element={<Navigate to="/project" replace />} />


      </Routes>
      </MovieProvider>
    </Router>
  );
};

export default App;

