import { useState } from 'react';

export default function SourceManager({ sources, setSources, updateSourcesInUrl, onScrape, loading }) {
  const [currentUrl, setCurrentUrl] = useState('');
  const [currentName, setCurrentName] = useState('');
  const [error, setError] = useState('');

  const addSource = () => {
    if (!currentUrl) {
      setError('Please enter a URL');
      return;
    }
    if (!currentUrl.startsWith('https://mytcgcollection.com/')) {
      setError('Invalid URL. Must be a mytcgcollection.com list URL');
      return;
    }

    const newSources = [
      ...sources,
      { url: currentUrl, name: currentName || `List ${sources.length + 1}` },
    ];
    setSources(newSources);
    updateSourcesInUrl(newSources);
    setCurrentUrl('');
    setCurrentName('');
    setError('');
  };

  const removeSource = (index) => {
    const newSources = sources.filter((_, i) => i !== index);
    setSources(newSources);
    updateSourcesInUrl(newSources);
  };

  return (
    <div className="sources-manager">
      <div className="add-source-form">
        <input
          type="text"
          value={currentUrl}
          onChange={(e) => setCurrentUrl(e.target.value)}
          placeholder="Enter TCG list URL (e.g., https://mytcgcollection.com/p/...)"
          className="url-input"
        />
        <input
          type="text"
          value={currentName}
          onChange={(e) => setCurrentName(e.target.value)}
          placeholder="Name (optional)"
          className="name-input"
        />
        <button onClick={addSource} className="add-btn">
          Add URL
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {sources.length > 0 && (
        <div className="sources-list">
          <h3>URLs to Scrape ({sources.length})</h3>
          {sources.map((source, index) => (
            <div key={index} className="source-item">
              <div className="source-info">
                <span className="source-name">{source.name}</span>
                <span className="source-url">{source.url}</span>
              </div>
              <button onClick={() => removeSource(index)} className="remove-btn">
                ×
              </button>
            </div>
          ))}
          <button onClick={onScrape} disabled={loading} className="scrape-all-btn">
            {loading ? 'Scraping...' : `Scrape ${sources.length} List${sources.length > 1 ? 's' : ''}`}
          </button>
        </div>
      )}
    </div>
  );
}
