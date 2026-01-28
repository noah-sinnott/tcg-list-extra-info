import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = 'https://backend-tcg-912009530954.europe-west2.run.app/api';
const ITEMS_PER_PAGE = 50;

function App() {
  const [url, setUrl] = useState('');
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [displayedCount, setDisplayedCount] = useState(ITEMS_PER_PAGE);
  const [selectedSets, setSelectedSets] = useState([]);
  const [selectedRarities, setSelectedRarities] = useState([]);
  const observerTarget = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setCards([]);
    setDisplayedCount(ITEMS_PER_PAGE);
    setSelectedSets([]);
    setSelectedRarities([]);
    setSearchTerm('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/scrape`, { url });
      setCards(response.data.cards);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to scrape list. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Intersection Observer for lazy loading
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && displayedCount < filteredCards.length) {
          setDisplayedCount(prev => Math.min(prev + ITEMS_PER_PAGE, filteredCards.length));
        }
      },
      { threshold: 1 }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [displayedCount]);

  // Reset displayed count when filters change
  useEffect(() => {
    setDisplayedCount(ITEMS_PER_PAGE);
  }, [searchTerm, sortConfig, selectedSets, selectedRarities]);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortedCards = () => {
    let sortedCards = [...cards];

    if (sortConfig.key) {
      sortedCards.sort((a, b) => {
        const aValue = (a[sortConfig.key] || '').toString().toLowerCase();
        const bValue = (b[sortConfig.key] || '').toString().toLowerCase();

        if (aValue < bValue) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }

    return sortedCards;
  };

  const getFilteredCards = () => {
    const sortedCards = getSortedCards();
    
    return sortedCards.filter(card => {
      const term = searchTerm.toLowerCase();
      const matchesSearch = !searchTerm || 
        (card.name || '').toLowerCase().includes(term)
      
      const matchesSet = selectedSets.length === 0 || selectedSets.includes(card.set_name);
      const matchesRarity = selectedRarities.length === 0 || selectedRarities.includes(card.rarity);
      
      return matchesSearch && matchesSet && matchesRarity;
    });
  };

  // Get unique sets and rarities with counts
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

  const getSortIcon = (columnKey) => {
    if (sortConfig.key !== columnKey) {
      return ' ↕';
    }
    return sortConfig.direction === 'asc' ? ' ↑' : ' ↓';
  };

  const filteredCards = getFilteredCards();
  const visibleCards = filteredCards.slice(0, displayedCount);
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

            <div className="table-container">
              <table className="cards-table">
                <thead>
                  <tr>
                    <th onClick={() => handleSort('name')} className="sortable">
                      Name{getSortIcon('name')}
                    </th>
                    <th onClick={() => handleSort('rarity')} className="sortable">
                      Rarity{getSortIcon('rarity')}
                    </th>
                    <th>Image</th>
                    <th>View</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleCards.map((card, index) => (
                    <tr key={index}>
                      <td>
                        <div className="card-name">{card.name || ''}</div>
                        <div className="card-set">{card.set_name || ''}</div>
                        {card.group_name && card.group_name !== card.set_name && (
                          <div className="card-group">{card.group_name}</div>
                        )}
                      </td>
                      <td>{card.rarity || ''}</td>
                      <td>
                        {card.image_url ? (
                          <img 
                            src={card.image_url} 
                            alt={card.name}
                            className="card-image"
                            loading="lazy"
                          />
                        ) : null}
                      </td>
                      <td>
                        {card.card_url ? (
                          <a 
                            href={card.card_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="view-card-link"
                          >
                            View Card
                          </a>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {displayedCount < filteredCards.length && (
                <div ref={observerTarget} className="loading-trigger">
                  <div className="spinner-small"></div>
                  <p>Loading more cards...</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
