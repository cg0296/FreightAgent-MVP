import { useState } from 'react';
import axios from 'axios';
import './Login.css';

export default function Login({ onLoginSuccess, API_URL }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${API_URL}/api/login`, {
        username,
        password
      });

      if (response.data.success) {
        localStorage.setItem('auth_token', response.data.token);
        localStorage.setItem('username', response.data.username);
        onLoginSuccess(response.data.token, response.data.username);
      } else {
        setError('Login failed');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell">
      <div className="login-stage">
        <section className="login-brand-panel">
          <div className="login-brand-mark">FA</div>
          <p className="login-kicker">Freight Operations</p>
          <h1>Parse shipper emails into quote-ready lane summaries.</h1>
          <p className="login-copy">
            Built for a fast intake workflow: capture customer requests, validate shipment details,
            and generate a carrier quote sheet without leaving the desk.
          </p>

          <div className="login-feature-list">
            <div className="login-feature">
              <span className="feature-index">01</span>
              <div>
                <strong>Email to lane summary</strong>
                <p>Origin, destination, equipment, dates, quantity, and requirements.</p>
              </div>
            </div>
            <div className="login-feature">
              <span className="feature-index">02</span>
              <div>
                <strong>Operator review surface</strong>
                <p>Confidence, notes, and extracted fields presented for validation.</p>
              </div>
            </div>
            <div className="login-feature">
              <span className="feature-index">03</span>
              <div>
                <strong>Quote-sheet output</strong>
                <p>Generate an Excel handoff for carrier pricing without manual re-entry.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="login-form-panel">
          <div className="login-card">
            <div className="login-card-head">
              <p className="login-kicker">Secure Access</p>
              <h2>Sign in to FreightAgent</h2>
              <span>Use your internal credentials to access the intake workspace.</span>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="login-field">
                <label htmlFor="username">Username</label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username"
                  disabled={loading}
                  autoFocus
                />
              </div>

              <div className="login-field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  disabled={loading}
                />
              </div>

              {error && (
                <div className="login-error">
                  <strong>Issue</strong>
                  <span>{error}</span>
                </div>
              )}

              <button className="login-submit" type="submit" disabled={loading}>
                {loading ? 'Signing in...' : 'Enter Workspace'}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
