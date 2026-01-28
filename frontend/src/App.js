import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const API_URL = 'https://backend-tcg-912009530954.europe-west2.run.app/api';
// const API_URL = 'http://127.0.0.1:5000/api';

function App() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [url, setUrl] = useState(searchParams.get('url') || '');
  const [searchTerm, setSearchTerm] = useState('');

  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [selectedSets, setSelectedSets] = useState([]);
  const [selectedRarities, setSelectedRarities] = useState([]);
  const [filtersExpanded, setFiltersExpanded] = useState(true);

  const scrapeUrl = async (urlToScrape) => {
    setError('');
    setCards([]);
    setSelectedSets([]);
    setSelectedRarities([]);
    setSearchTerm('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/scrape`, { url: urlToScrape });
      setCards(response.data.cards);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to scrape list. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSearchParams({ url });
    await scrapeUrl(url);
  };

  useEffect(() => {
    const urlParam = searchParams.get('url');
    if (urlParam) {
      scrapeUrl(urlParam);
    }
  }, []);


  const getSetCounts = () => {
    const counts = {};
    cards.forEach(card => {
      if (card.set_name) {
        counts[card.set_name] = (counts[card.set_name] || 0) + 1;
      }
    });
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]));
  };

  const getRarityCounts = () => {
    const counts = {};
    cards.forEach(card => {
      if (card.rarity) {
        counts[card.rarity] = (counts[card.rarity] || 0) + 1;
      }
    });
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]));
  };

  const toggleSet = (set) => {
    setSelectedSets(prev => 
      prev.includes(set) ? prev.filter(s => s !== set) : [...prev, set]
    );
  };

  const toggleRarity = (rarity) => {
    setSelectedRarities(prev => 
      prev.includes(rarity) ? prev.filter(r => r !== rarity) : [...prev, rarity]
    );
  };

  const setCounts = getSetCounts();
  const rarityCounts = getRarityCounts();

  return (
    <div className="App">
      <div className="container">
        <h1>TCG List Extra</h1>
        
        <form onSubmit={handleSubmit} className="url-form">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter TCG list URL (e.g., https://mytcgcollection.com/p/...)"
            className="url-input"
            required
          />
          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? 'Scraping...' : 'Scrape List'}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Fetching card data... This may take a while.</p>
          </div>
        )}

        {cards.length > 0 && !loading && (
          <div className="results">
            <div className="results-header">
              <h2>Found {cards.length} cards</h2>
            </div>

            <div className="filters-container">
              <button 
                className="filters-toggle"
                onClick={() => setFiltersExpanded(!filtersExpanded)}
              >
                {filtersExpanded ? '▼' : '▶'} Filters
              </button>
              
              {filtersExpanded && (
                <div className="filters">
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search by name..."
                    className="filter-input"
                  />
                  
                  <div className="filter-group">
                    <label className="filter-label">Sets ({setCounts.length})</label>
                    <div className="checkbox-group">
                      {setCounts.map(([set, count]) => (
                        <label key={set} className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={selectedSets.includes(set)}
                            onChange={() => toggleSet(set)}
                          />
                          <span>{set} ({count})</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="filter-group">
                    <label className="filter-label">Rarities</label>
                    <div className="checkbox-group">
                      {rarityCounts.map(([rarity, count]) => (
                        <label key={rarity} className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={selectedRarities.includes(rarity)}
                            onChange={() => toggleRarity(rarity)}
                          />
                          <span>{rarity} ({count})</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {(searchTerm || selectedSets.length > 0 || selectedRarities.length > 0) && (
                    <button 
                      onClick={() => {
                        setSearchTerm('');
                        setSelectedSets([]);
                        setSelectedRarities([]);
                      }}
                      className="clear-filters-btn"
                    >
                      Clear Filters
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="cards-grid">
              {cards.sort((a, b) => {
      const aName = (a.name || '').toLowerCase();
      const bName = (b.name || '').toLowerCase();
      return aName.localeCompare(bName);
    }).filter(card => {
      const term = searchTerm.toLowerCase();
      const matchesSearch = !searchTerm || 
        (card.name || '').toLowerCase().includes(term)
      
      const matchesSet = selectedSets.length === 0 || selectedSets.includes(card.set_name);
      const matchesRarity = selectedRarities.length === 0 || selectedRarities.includes(card.rarity);
      
      return matchesSearch && matchesSet && matchesRarity;
    }).map((card, index) => (
                <a
                  key={index}
                  href={card.card_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="card-item"
                  style={{
                    backgroundImage: card.image_url ? `url(${card.image_url})` : 'none'
                  }}
                >
                  <div className="card-info">
                    <div className="card-name">{card.name || 'Unknown'}</div>
                    <div className="card-details">
                      <div className="card-set">{card.set_name || ''}</div>
                      {card.rarity && <div className="card-rarity">{card.rarity}</div>}
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
