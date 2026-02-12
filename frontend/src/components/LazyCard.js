import { useState, useEffect, useRef } from 'react';

export default function LazyCard({ card }) {
  const [isVisible, setIsVisible] = useState(false);
  const cardRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(entry.target);
        }
      },
      { rootMargin: '200px' }
    );

    if (cardRef.current) observer.observe(cardRef.current);
    return () => {
      if (cardRef.current) observer.unobserve(cardRef.current);
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
        backgroundImage: isVisible && card.image_url ? `url(${card.image_url})` : 'none',
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
