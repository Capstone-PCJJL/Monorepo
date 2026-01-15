import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Papa from 'papaparse';
import { unzip } from 'unzipit';
import LoadingSpinner from '../LoadingSpinner';
import './ImportCsv.css';

const ImportCsv = () => {
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [imported, setImported] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
    console.log('File selected:', e.target.files[0]?.name);
  };

  const handleImport = async (e) => {
    e.preventDefault();
    console.log('Import button clicked, file:', file?.name);

    if (!file) {
      setError('Please select a ZIP file to import.');
      return;
    }

    const userId = localStorage.getItem('userId');
    console.log('User ID from localStorage:', userId);

    if (!userId) {
      setError('User not logged in.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Unzip the file
      console.log('Unzipping file...');
      const { entries } = await unzip(file);
      console.log('ZIP entries:', Object.keys(entries));

      // Find ratings.csv in the root
      const ratingsEntry = Object.values(entries).find(entry => entry.name.toLowerCase() === 'ratings.csv');
      // Find likes/films.csv (case-insensitive for folder and file)
      const filmsEntry = Object.values(entries).find(entry => {
        const name = entry.name.toLowerCase();
        return name.startsWith('likes/') && name.endsWith('films.csv');
      });

      console.log('Found ratings.csv:', !!ratingsEntry, ratingsEntry?.name);
      console.log('Found likes/films.csv:', !!filmsEntry, filmsEntry?.name);

      if (!ratingsEntry || !filmsEntry) {
        setError('Could not find both "ratings.csv" in the root and "likes/films.csv" in the zip.');
        setLoading(false);
        return;
      }

      // Read and parse both CSVs
      console.log('Reading CSV files...');
      const [ratingsCsv, filmsCsv] = await Promise.all([
        ratingsEntry.text(),
        filmsEntry.text()
      ]);

      const ratingsData = Papa.parse(ratingsCsv, { header: true, skipEmptyLines: true }).data;
      const likesData = Papa.parse(filmsCsv, { header: true, skipEmptyLines: true }).data;

      console.log('Parsed ratings rows:', ratingsData.length);
      console.log('Parsed likes rows:', likesData.length);

      // Send both to backend
      console.log('Sending to backend...');
      const [likesRes, ratingsRes] = await Promise.all([
        fetch(`/api/v1/users/${userId}/import`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ data: likesData, table: 'likes' }),
        }),
        fetch(`/api/v1/users/${userId}/import`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ data: ratingsData, table: 'ratings' }),
        })
      ]);

      console.log('Likes response:', likesRes.status);
      console.log('Ratings response:', ratingsRes.status);

      if (!likesRes.ok || !ratingsRes.ok) {
        const likesErr = await likesRes.text();
        const ratingsErr = await ratingsRes.text();
        console.error('Likes error:', likesErr);
        console.error('Ratings error:', ratingsErr);
        throw new Error('Failed to import one or both CSVs to server.');
      }

      // Set imported = 1 for the user
      console.log('Updating import status...');
      const importRes = await fetch(`/api/v1/users/${userId}/import-status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!importRes.ok) {
        throw new Error('Failed to update imported status.');
      }

      console.log('Import complete!');
      setImported(true);
      setLoading(false);
      setTimeout(() => navigate('/Home'), 1000);
    } catch (err) {
      console.error('Import error:', err);
      setError('Upload failed: ' + err.message);
      setLoading(false);
    }
  };

  return (
    <div className="container_s">
      <div className="form">
        <h1>Import Your Letterboxd ZIP</h1>
        <p>*You are required to import your Letterboxd ZIP (containing ratings.csv and likes/films.csv) before proceeding further.</p>
        <form onSubmit={handleImport}>
          <div className="form-group">
            <input type="file" accept=".zip" onChange={handleFileChange} className="form-control" />
          </div>
          {error && <div className="error">{error}</div>}
          {imported && <div className="success">ZIP imported! Redirecting...</div>}
          {loading && <LoadingSpinner size="small" message="Importing... Please wait." />}
          <button type="submit" className="btn" style={{ marginTop: 16 }} disabled={loading}>
            {loading ? 'Importing...' : 'Import ZIP'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ImportCsv;
