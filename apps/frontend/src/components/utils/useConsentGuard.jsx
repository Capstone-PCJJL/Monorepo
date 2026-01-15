// src/utils/useConsentGuard.js
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const CONSENT_CACHE_KEY = 'userConsented';
const CONSENT_VERIFIED_KEY = 'consentVerifiedAt';
const VERIFY_INTERVAL = 60 * 60 * 1000; // Re-verify every 1 hour

const useConsentGuard = () => {
  const cachedConsent = localStorage.getItem(CONSENT_CACHE_KEY) === 'true';
  const [loading, setLoading] = useState(!cachedConsent);
  const navigate = useNavigate();

  useEffect(() => {
    const checkConsent = async () => {
      const userId = localStorage.getItem('userId');

      if (!userId) {
        navigate('/');
        return;
      }

      // If already verified recently, skip API call
      const lastVerified = localStorage.getItem(CONSENT_VERIFIED_KEY);
      const needsVerification = !lastVerified ||
        (Date.now() - parseInt(lastVerified)) > VERIFY_INTERVAL;

      if (cachedConsent && !needsVerification) {
        setLoading(false);
        return;
      }

      try {
        const res = await fetch(`/api/v1/users/${userId}/consent`);
        const data = await res.json();

        if (!res.ok || !data.consented) {
          localStorage.removeItem(CONSENT_CACHE_KEY);
          localStorage.removeItem(CONSENT_VERIFIED_KEY);
          navigate('/consent');
        } else {
          localStorage.setItem(CONSENT_CACHE_KEY, 'true');
          localStorage.setItem(CONSENT_VERIFIED_KEY, Date.now().toString());
          setLoading(false);
        }
      } catch (err) {
        console.error('Consent check failed:', err);
        // If cached consent exists, don't block on network error
        if (cachedConsent) {
          setLoading(false);
        } else {
          navigate('/login');
        }
      }
    };

    checkConsent();
  }, [navigate, cachedConsent]);

  return loading;
};

export default useConsentGuard;
