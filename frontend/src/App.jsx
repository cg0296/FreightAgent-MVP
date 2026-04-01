import { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';
import Login from './Login';

export default function App() {
  const API_URL = import.meta.env.VITE_API_URL || '';

  const [token, setToken] = useState(localStorage.getItem('auth_token'));
  const [username, setUsername] = useState(localStorage.getItem('username'));
  const [formData, setFormData] = useState({
    clientName: '',
    emailText: ''
  });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [generatingExcel, setGeneratingExcel] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const getAuthHeaders = () => ({
    Authorization: `Bearer ${token}`
  });

  const clearSession = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('username');
    setToken(null);
    setUsername(null);
  };

  const handleLoginSuccess = (newToken, newUsername) => {
    setToken(newToken);
    setUsername(newUsername);
  };

  const handleLogout = () => {
    clearSession();
    setFormData({ clientName: '', emailText: '' });
    setResults(null);
    setError(null);
    setDownloadUrl(null);
    setSuccessMessage(null);
  };

  const handleAuthFailure = () => {
    clearSession();
    setError('Your session expired. Please sign in again.');
    setResults(null);
    setDownloadUrl(null);
    setSuccessMessage(null);
  };

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    const validateSession = async () => {
      try {
        await axios.get(`${API_URL}/api/carriers`, {
          headers: getAuthHeaders()
        });
      } catch (err) {
        if (!cancelled && err.response?.status === 401) {
          handleAuthFailure();
        }
      }
    };

    validateSession();

    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!token) {
    return <Login onLoginSuccess={handleLoginSuccess} API_URL={API_URL} />;
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.clientName.trim() || !formData.emailText.trim()) {
      setError('Please fill in both client name and email content');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);
    setDownloadUrl(null);
    setSuccessMessage(null);

    try {
      const response = await axios.post(
        `${API_URL}/api/parse-email`,
        {
          email_text: formData.emailText,
          client_name: formData.clientName
        },
        {
          headers: getAuthHeaders()
        }
      );

      if (response.data.success) {
        setResults(response.data.data);
      } else {
        setError(response.data.error || 'Failed to parse email');
      }
    } catch (err) {
      if (err.response?.status === 401) {
        handleAuthFailure();
        return;
      }

      setError(
        err.response?.data?.detail ||
          err.response?.data?.error ||
          'Error connecting to server. Make sure backend is running on port 8001.'
      );
      console.error('API Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const calculateTransitDays = () => {
    if (!results?.loading_date_start || !results?.delivery_date) return '-';
    const start = new Date(results.loading_date_start);
    const end = new Date(results.delivery_date);
    const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
    return days > 0 ? `${days} days` : '-';
  };

  const getConfidenceTone = (confidence) => {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.75) return 'medium';
    return 'low';
  };

  const getConfidenceLabel = (confidence) => {
    if (confidence >= 0.9) return 'High confidence';
    if (confidence >= 0.75) return 'Review recommended';
    return 'Manual review needed';
  };

  const handleGenerateExcel = async () => {
    if (!results) {
      setError('No parsed data available');
      return;
    }

    setGeneratingExcel(true);
    setError(null);
    setSuccessMessage(null);
    setDownloadUrl(null);

    try {
      const carriersResponse = await axios.get(`${API_URL}/api/carriers`, {
        headers: getAuthHeaders()
      });

      const carriers = carriersResponse.data;
      if (!Array.isArray(carriers) || carriers.length === 0) {
        setError('No carriers are available to generate the quote sheet.');
        return;
      }

      const response = await axios.post(
        `${API_URL}/api/generate-quote-sheet`,
        {
          quote_data: results,
          carriers,
          client_name: formData.clientName
        },
        {
          headers: getAuthHeaders()
        }
      );

      if (response.data.success) {
        setDownloadUrl(`${API_URL}${response.data.file_url}`);
        setSuccessMessage(`Quote sheet ready: ${response.data.filename}`);
      } else {
        setError(response.data.error || 'Failed to generate Excel');
      }
    } catch (err) {
      if (err.response?.status === 401) {
        handleAuthFailure();
        return;
      }

      setError(
        err.response?.data?.detail ||
          err.response?.data?.error ||
          'Error generating Excel. Make sure backend is running.'
      );
      console.error('Excel Generation Error:', err);
    } finally {
      setGeneratingExcel(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">FA</div>
          <div>
            <p className="eyebrow">Freight Operations</p>
            <h1>FreightAgent</h1>
          </div>
        </div>

        <div className="topbar-meta">
          <div className="status-pill">
            <span className="status-dot"></span>
            Live workflow
          </div>
          <div className="user-chip">
            <span className="user-label">Signed in</span>
            <strong>{username}</strong>
          </div>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <main className="workspace">
        <section className="workspace-intro">
          <div>
            <p className="section-kicker">Quote Intake Desk</p>
            <h2>Parse inbound requests and convert them into a quote-ready lane summary.</h2>
          </div>
          <div className="workspace-note">
            Paste the customer email, review the extracted shipment details, then generate the carrier quote sheet.
          </div>
        </section>

        <section className="workspace-grid">
          <div className="panel intake-panel">
            <div className="panel-header">
              <div>
                <p className="section-kicker">Input</p>
                <h3>Inbound Email</h3>
              </div>
              <p className="panel-copy">Use raw customer language. Claude extracts lane, equipment, dates, and requirements.</p>
            </div>

            <form className="intake-form" onSubmit={handleSubmit}>
              <div className="field-group">
                <label htmlFor="clientName">Client Name</label>
                <input
                  id="clientName"
                  type="text"
                  name="clientName"
                  placeholder="Acme Logistics"
                  value={formData.clientName}
                  onChange={handleInputChange}
                  disabled={loading}
                />
              </div>

              <div className="field-group field-group-large">
                <div className="field-row">
                  <label htmlFor="emailText">Email Content</label>
                  <span className="field-hint">Paste the full request</span>
                </div>
                <textarea
                  id="emailText"
                  name="emailText"
                  placeholder="Need 2 dry vans loading in Joliet, IL on 2026-04-03 delivering Dallas, TX on 2026-04-05..."
                  value={formData.emailText}
                  onChange={handleInputChange}
                  disabled={loading}
                />
              </div>

              <div className="form-actions">
                <button className="primary-btn" type="submit" disabled={loading}>
                  {loading ? 'Parsing request...' : 'Parse Email'}
                </button>
                <p className="form-caption">Structured extraction for lane, equipment, dates, quantity, and accessorial notes.</p>
              </div>
            </form>
          </div>

          <div className="panel results-panel">
            <div className="panel-header">
              <div>
                <p className="section-kicker">Output</p>
                <h3>Parsed Quote Review</h3>
              </div>
              <p className="panel-copy">Validate the lane summary before issuing a quote sheet to carriers.</p>
            </div>

            {error && (
              <div className="notice notice-error">
                <strong>Issue</strong>
                <span>{error}</span>
              </div>
            )}

            {successMessage && (
              <div className="notice notice-success">
                <strong>Ready</strong>
                <span>{successMessage}</span>
              </div>
            )}

            {loading && (
              <div className="empty-state loading-state">
                <div className="spinner"></div>
                <p>Parsing inbound request</p>
                <span>Extracting shipment structure and validating required fields.</span>
              </div>
            )}

            {!results && !loading && !error && (
              <div className="empty-state">
                <div className="empty-badge">Awaiting intake</div>
                <p>No parsed quote yet.</p>
                <span>Run the parser to generate a structured lane summary and quote sheet output.</span>
              </div>
            )}

            {results && !loading && (
              <div className="results-stack">
                <div className={`confidence-card tone-${getConfidenceTone(results.confidence)}`}>
                  <div>
                    <p className="section-kicker">AI Confidence</p>
                    <strong>{getConfidenceLabel(results.confidence)}</strong>
                  </div>
                  <div className="confidence-score">{(results.confidence * 100).toFixed(0)}%</div>
                </div>

                <div className="lane-banner">
                  <div>
                    <span className="banner-label">Origin</span>
                    <strong>{results.origin_city}, {results.origin_state}</strong>
                  </div>
                  <div className="lane-divider"></div>
                  <div>
                    <span className="banner-label">Destination</span>
                    <strong>{results.destination_city}, {results.destination_state}</strong>
                  </div>
                </div>

                <div className="data-grid">
                  <article className="data-card">
                    <span className="data-label">Equipment</span>
                    <strong>{results.equipment_type || '-'}</strong>
                  </article>
                  <article className="data-card">
                    <span className="data-label">Quantity</span>
                    <strong>{results.quantity || '-'}</strong>
                  </article>
                  <article className="data-card">
                    <span className="data-label">Driver Type</span>
                    <strong>{results.driver_type || 'Not specified'}</strong>
                  </article>
                  <article className="data-card">
                    <span className="data-label">Transit</span>
                    <strong>{calculateTransitDays()}</strong>
                  </article>
                  <article className="data-card">
                    <span className="data-label">Loading Date</span>
                    <strong>{results.loading_date_start || '-'}</strong>
                  </article>
                  <article className="data-card">
                    <span className="data-label">Delivery Date</span>
                    <strong>{results.delivery_date || '-'}</strong>
                  </article>
                </div>

                {results.special_requirements && results.special_requirements.length > 0 && (
                  <section className="detail-block">
                    <div className="detail-head">
                      <p className="section-kicker">Requirements</p>
                      <h4>Special handling</h4>
                    </div>
                    <div className="tag-row">
                      {results.special_requirements.map((req, idx) => (
                        <span key={idx} className="tag">{req}</span>
                      ))}
                    </div>
                  </section>
                )}

                {results.notes && (
                  <section className="detail-block note-block">
                    <div className="detail-head">
                      <p className="section-kicker">Notes</p>
                      <h4>Parser comments</h4>
                    </div>
                    <p className="notes-text">{results.notes}</p>
                  </section>
                )}

                <div className="action-bar">
                  {!downloadUrl ? (
                    <button
                      className="primary-btn"
                      onClick={handleGenerateExcel}
                      disabled={generatingExcel}
                    >
                      {generatingExcel ? 'Generating quote sheet...' : 'Generate Excel Quote'}
                    </button>
                  ) : (
                    <div className="download-actions">
                      <a href={downloadUrl} className="download-link" download>
                        Download Excel Quote
                      </a>
                      <button
                        className="secondary-btn"
                        onClick={() => {
                          setDownloadUrl(null);
                          setSuccessMessage(null);
                        }}
                      >
                        Generate Another
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
