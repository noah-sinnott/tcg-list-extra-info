import { useState, useMemo } from 'react';

/**
 * Centralised filter / search logic for the card list.
 * Returns filtered + sorted cards and helpers for the filter panel.
 */
export default function useCardFilters(cards) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSets, setSelectedSets] = useState([]);
  const [selectedRarities, setSelectedRarities] = useState([]);
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);

  // --- counts ---

  const countBy = (key) => {
    const counts = {};
    cards.forEach((c) => {
      const val = c[key] || `Unknown ${key}`;
      counts[val] = (counts[val] || 0) + 1;
    });
    return Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]));
  };

  const setCounts = useMemo(() => countBy('set_name'), [cards]);
  const rarityCounts = useMemo(() => countBy('rarity'), [cards]);
  const groupCounts = useMemo(() => countBy('group_name'), [cards]);
  const sourceCounts = useMemo(() => countBy('source_name'), [cards]);

  // --- toggle helpers ---

  const toggle = (setter) => (value) =>
    setter((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );

  const toggleSet = toggle(setSelectedSets);
  const toggleRarity = toggle(setSelectedRarities);
  const toggleGroup = toggle(setSelectedGroups);
  const toggleSource = toggle(setSelectedSources);

  const clearAll = () => {
    setSearchTerm('');
    setSelectedSets([]);
    setSelectedRarities([]);
    setSelectedGroups([]);
    setSelectedSources([]);
  };

  const hasActiveFilters =
    searchTerm ||
    selectedSets.length > 0 ||
    selectedRarities.length > 0 ||
    selectedGroups.length > 0 ||
    selectedSources.length > 0;

  // --- filtered + sorted output ---

  const filteredCards = useMemo(() => {
    const term = searchTerm.toLowerCase();
    return cards
      .filter((card) => {
        if (term && !(card.name || '').toLowerCase().includes(term)) return false;
        if (selectedSets.length && !selectedSets.includes(card.set_name)) return false;
        if (selectedRarities.length && !selectedRarities.includes(card.rarity)) return false;
        if (selectedGroups.length && !selectedGroups.includes(card.group_name || 'Unknown group_name')) return false;
        if (selectedSources.length && !selectedSources.includes(card.source_name || 'Unknown source_name')) return false;
        return true;
      })
      .sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  }, [cards, searchTerm, selectedSets, selectedRarities, selectedGroups, selectedSources]);

  return {
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
    filteredCards,
  };
}
