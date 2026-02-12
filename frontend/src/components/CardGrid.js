import LazyCard from './LazyCard';

export default function CardGrid({ cards }) {
  if (cards.length === 0) return null;

  return (
    <div className="cards-grid">
      {cards.map((card, index) => (
        <LazyCard key={index} card={card} />
      ))}
    </div>
  );
}
