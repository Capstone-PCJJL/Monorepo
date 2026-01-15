import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const Consent = () => {
  const [agreed, setAgreed] = useState(false);
  const navigate = useNavigate();

  const userId = localStorage.getItem('userId');

  useEffect(() => {
    const checkConsentStatus = async () => {
      if (!userId) {
        navigate('/login'); // fallback if no user
        return;
      }

      try {
        const res = await fetch(`/api/v1/users/${userId}/consent`);
        if (!res.ok) throw new Error('Failed to check consent');

        const data = await res.json();
        if (data.consented) {
          // If already consented, check import status
          const importRes = await fetch(`/api/v1/users/${userId}/import-status`);
          const importData = await importRes.json();
          if (!importRes.ok) throw new Error(importData.error || 'Failed to check import status');
          if (!importData.imported) {
            navigate('/import-csv');
          } else {
            navigate('/Home');
          }
        }
      } catch (err) {
        console.error('Error checking consent/import:', err);
      }
    };

    checkConsentStatus();
  }, [userId, navigate]);

  const handleConsentSubmit = async () => {
    if (!agreed) return;

    try {
      const response = await fetch(`/api/v1/users/${userId}/consent`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Consent update failed');
      }

      // After consent, check import status
      const importRes = await fetch(`/api/v1/users/${userId}/import-status`);
      const importData = await importRes.json();
      if (!importRes.ok) throw new Error(importData.error || 'Failed to check import status');
      if (!importData.imported) {
        navigate('/import-csv');
      } else {
        navigate('/Home');
      }
    } catch (err) {
      console.error(err);
      alert('There was an error submitting your consent.');
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#1c1b2d',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '2rem',
    }}>
      <form style={{
        backgroundColor: '#2e2c45',
        color: 'white',
        borderRadius: '8px',
        padding: '2rem',
        width: '100%',
        maxWidth: '600px',
        boxShadow: '0 0 10px rgba(0,0,0,0.5)',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <h2 style={{ marginBottom: '1rem', textAlign: 'center' }}>Terms and Conditions</h2>

        <div style={{
          maxHeight: '300px',
          overflowY: 'scroll',
          backgroundColor: '#1e1d30',
          padding: '1rem',
          borderRadius: '5px',
          marginBottom: '1.5rem',
          fontSize: '0.9rem',
          lineHeight: '1.5',
        }}>
          <p>Welcome to our app! Please read these Terms and Conditions carefully before using our services.</p>
          <p>1. Acceptance: By using this app, you agree to these terms.</p>
          <p>2. Privacy: We respect your privacy and will not share your data without consent.</p>
          <p>3. Usage: You agree not to misuse the application for illegal activities.</p>
          <p>4. Data: We may collect anonymized usage data to improve user experience.</p>
          <p>5. Termination: Violation of terms may result in account suspension.</p>
          <p>6. Changes: These terms may be updated at any time with notice.</p>
          <p>Please scroll and review the full text before consenting.</p>
        </div>

        <label style={{ display: 'flex', alignItems: 'center', marginBottom: '1.5rem' }}>
          <input
            type="checkbox"
            checked={agreed}
            onChange={() => setAgreed(!agreed)}
            style={{ marginRight: '0.5rem' }}
          />
          I agree to the Terms and Conditions
        </label>

        <button
          type="button"
          onClick={handleConsentSubmit}
          disabled={!agreed}
          style={{
            padding: '0.75rem',
            backgroundColor: agreed ? '#4CAF50' : '#888',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: agreed ? 'pointer' : 'not-allowed',
            fontSize: '1rem',
          }}
        >
          Consent
        </button>
      </form>
    </div>
  );
};

export default Consent;
