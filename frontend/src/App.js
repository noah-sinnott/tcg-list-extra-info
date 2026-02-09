import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const API_URL = 'https://backend-tcg-912009530954.europe-west2.run.app/api';
// const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api';

function LazyCard({ card }) {
  const [isVisible, setIsVisible] = useState(false);
  const cardRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.unobserve(entry.target);
          }
        });
      },
      {
        rootMargin: '200px', // Start loading 200px before the card is visible
      }
    );

    if (cardRef.current) {
      observer.observe(cardRef.current);
    }

    return () => {
      if (cardRef.current) {
        observer.unobserve(cardRef.current);
      }
    };
  }, []);

  return (
    <a
      ref={cardRef}
      href={card.card_url}
      target="_blank"
      rel="noopener noreferrer"
      className="card-item"
      style={{
        backgroundImage: isVisible && card.image_url ? `url(${card.image_url})` : 'none'
      }}
    >
      <div className="card-info">
        <div className="card-name">{card.name || 'Unknown'}</div>
        <div className="card-details">
          {card.source_name && <div className="card-source">{card.source_name}</div>}
          <div className="card-set">{card.set_name || ''}</div>
          <div className="card-group">{card.group_name || ''}</div>
          {card.rarity && <div className="card-rarity">{card.rarity}</div>}
        </div>
      </div>
    </a>
  );
}

function App() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchTerm, setSearchTerm] = useState('');

  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [selectedSets, setSelectedSets] = useState([]);
  const [selectedRarities, setSelectedRarities] = useState([]);
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  // State for managing multiple URL sources
  const [sources, setSources] = useState([]);
  const [currentUrl, setCurrentUrl] = useState('');
  const [currentName, setCurrentName] = useState('');

  // Load sources from URL params on mount
  useEffect(() => {
    const sourcesParam = searchParams.get('sources');
    if (sourcesParam) {
      try {
        const decodedSources = JSON.parse(decodeURIComponent(sourcesParam));
        setSources(decodedSources);
      } catch (err) {
        console.error('Failed to parse sources from URL', err);
      }
    }
  }, []);

  // Update URL params when sources change
  const updateSourcesInUrl = (newSources) => {
    if (newSources.length > 0) {
      setSearchParams({ sources: encodeURIComponent(JSON.stringify(newSources)) });
    } else {
      setSearchParams({});
    }
  };

  const addSource = () => {
    if (!currentUrl) {
      setError('Please enter a URL');
      return;
    }
    if (!currentUrl.startsWith("https://mytcgcollection.com/")) {
      setError('Invalid URL. Must be a mytcgcollection.com list URL');
      return;
    }
    
    const newSource = {
      url: currentUrl,
      name: currentName || `List ${sources.length + 1}`
    };
    
    const newSources = [...sources, newSource];
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

  const scrapeLists = async () => {
    if (sources.length === 0) {
      setError('Please add at least one URL to scrape');
      return;
    }

    setError('');
    setCards([]);
    setSelectedSets([]);
    setSelectedRarities([]);
    setSelectedGroups([]);
    setSelectedSources([]);
    setSearchTerm('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/scrape`, { sources });
      setCards(response.data.cards);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to scrape lists. Please try again.');
    } finally {
      setLoading(false);
    }
  };


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

  const getGroupCounts = () => {
    const counts = {};
    cards.forEach(card => {
      const groupName = card.group_name || 'Unknown Group';
      counts[groupName] = (counts[groupName] || 0) + 1;
    });
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]));
  };

  const getSourceCounts = () => {
    const counts = {};
    cards.forEach(card => {
      const sourceName = card.source_name || 'Unknown Source';
      counts[sourceName] = (counts[sourceName] || 0) + 1;
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

  const toggleGroup = (group) => {
    setSelectedGroups(prev => 
      prev.includes(group) ? prev.filter(g => g !== group) : [...prev, group]
    );
  };

  const toggleSource = (source) => {
    setSelectedSources(prev => 
      prev.includes(source) ? prev.filter(s => s !== source) : [...prev, source]
    );
  };

  const setCounts = getSetCounts();
  const rarityCounts = getRarityCounts();
  const groupCounts = getGroupCounts();
  const sourceCounts = getSourceCounts();

  return (
    <div className="App">
      <div className="container">
        <h1>TCG List Extra</h1>
        
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
              <button 
                onClick={scrapeLists} 
                disabled={loading} 
                className="scrape-all-btn"
              >
                {loading ? 'Scraping...' : `Scrape ${sources.length} List${sources.length > 1 ? 's' : ''}`}
              </button>
            </div>
          )}
        </div>

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

            <div className="search-container">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by name..."
                className="filter-input"
              />
              <button 
                className="filters-toggle"
                onClick={() => setFiltersExpanded(!filtersExpanded)}
              >
                {filtersExpanded ? '▼' : '▶'} Filters
              </button>
            </div>

            {filtersExpanded && (
              <div className="filters-container">
                <div className="filters">
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

                  <div className="filter-group">
                    <label className="filter-label">Groups ({groupCounts.length})</label>
                    <div className="checkbox-group">
                      {groupCounts.map(([group, count]) => (
                        <label key={group} className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={selectedGroups.includes(group)}
                            onChange={() => toggleGroup(group)}
                          />
                          <span>{group} ({count})</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {sourceCounts.length > 1 && (
                    <div className="filter-group">
                      <label className="filter-label">Sources ({sourceCounts.length})</label>
                      <div className="checkbox-group">
                        {sourceCounts.map(([source, count]) => (
                          <label key={source} className="checkbox-label">
                            <input
                              type="checkbox"
                              checked={selectedSources.includes(source)}
                              onChange={() => toggleSource(source)}
                            />
                            <span>{source} ({count})</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  {(searchTerm || selectedSets.length > 0 || selectedRarities.length > 0 || selectedGroups.length > 0 || selectedSources.length > 0) && (
                    <button 
                      onClick={() => {
                        setSearchTerm('');
                        setSelectedSets([]);
                        setSelectedRarities([]);
                        setSelectedGroups([]);
                        setSelectedSources([]);
                      }}
                      className="clear-filters-btn"
                    >
                      Clear Filters
                    </button>
                  )}
                </div>
              </div>
            )}

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
      const matchesGroup = selectedGroups.length === 0 || selectedGroups.includes(card.group_name || 'Unknown Group');
      const matchesSource = selectedSources.length === 0 || selectedSources.includes(card.source_name || 'Unknown Source');
      
      return matchesSearch && matchesSet && matchesRarity && matchesGroup && matchesSource;
    }).map((card, index) => (
                <LazyCard key={index} card={card} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
