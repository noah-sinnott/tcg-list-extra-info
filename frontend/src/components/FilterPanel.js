import { useState } from 'react';

function CheckboxList({ label, items, selected, onToggle }) {
  return (
    <div className="filter-group">
      <label className="filter-label">{label}</label>
      <div className="checkbox-group">
        {items.map(([value, count]) => (
          <label key={value} className="checkbox-label">
            <input
              type="checkbox"
              checked={selected.includes(value)}
              onChange={() => onToggle(value)}
            />
            <span>
              {value} ({count})
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

export default function FilterPanel({
  searchTerm,
  setSearchTerm,
  selectedSets,
  selectedRarities,
  selectedGroups,
  selectedSources,
  toggleSet,
  toggleRarity,
  toggleGroup,
  toggleSource,
  clearAll,
  hasActiveFilters,
  setCounts,
  rarityCounts,
  groupCounts,
  sourceCounts,
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <div className="search-container">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by name..."
          className="filter-input"
        />
        <button className="filters-toggle" onClick={() => setExpanded(!expanded)}>
          {expanded ? '▼' : '▶'} Filters
        </button>
      </div>

      {expanded && (
        <div className="filters-container">
          <div className="filters">
            <CheckboxList label={`Sets (${setCounts.length})`} items={setCounts} selected={selectedSets} onToggle={toggleSet} />
            <CheckboxList label="Rarities" items={rarityCounts} selected={selectedRarities} onToggle={toggleRarity} />
            <CheckboxList label={`Groups (${groupCounts.length})`} items={groupCounts} selected={selectedGroups} onToggle={toggleGroup} />

            {sourceCounts.length > 1 && (
              <CheckboxList label={`Sources (${sourceCounts.length})`} items={sourceCounts} selected={selectedSources} onToggle={toggleSource} />
            )}

            {hasActiveFilters && (
              <button onClick={clearAll} className="clear-filters-btn">
                Clear Filters
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
