import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import './App.css';

import SourceManager from './components/SourceManager';
import FilterPanel from './components/FilterPanel';
import CardGrid from './components/CardGrid';
import useCardFilters from './hooks/useCardFilters';
import { scrapeLists } from './services/api';

function App() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sources, setSources] = useState([]);

  const filters = useCardFilters(cards);

  // Load sources from URL params on mount
  useEffect(() => {
    const param = searchParams.get('sources');
    if (param) {
      try {
        setSources(JSON.parse(decodeURIComponent(param)));
      } catch (err) {
        console.error('Failed to parse sources from URL', err);
      }
    }
  }, []);

  const updateSourcesInUrl = (newSources) => {
    if (newSources.length > 0) {
      setSearchParams({ sources: encodeURIComponent(JSON.stringify(newSources)) });
    } else {
      setSearchParams({});
    }
  };

  const handleScrape = async () => {
    if (sources.length === 0) {
      setError('Please add at least one URL to scrape');
      return;
    }
    setError('');
    setCards([]);
    filters.clearAll();
    setLoading(true);

    try {
      setCards(await scrapeLists(sources));
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to scrape lists. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <div className="container">
        <h1>TCG List Extra</h1>

        <SourceManager
          sources={sources}
          setSources={setSources}
          updateSourcesInUrl={updateSourcesInUrl}
          onScrape={handleScrape}
          loading={loading}
        />

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

            <FilterPanel {...filters} />
            <CardGrid cards={filters.filteredCards} />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
