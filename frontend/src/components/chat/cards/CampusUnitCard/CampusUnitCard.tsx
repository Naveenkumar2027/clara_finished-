import React from 'react';
import { motion } from 'motion/react';
import type { PresentationCardModel } from '../../../../features/chat/presentation/PresentationCardModel';
import { SAMPLE_CONTENT_STATUS, uiText } from '../../../../localization/uiCopy';
import { campusUnitFromLocale } from './campusUnitLocale';

type CampusUnitCardProps = {
  card: PresentationCardModel;
  language?: string;
};

export default function CampusUnitCard({ card, language }: CampusUnitCardProps) {
  const locale = campusUnitFromLocale(card.unitId, language);
  const title = (locale?.title || card.title || card.unitId).trim();
  const body = (locale?.body || card.content || '').trim();
  const points = Array.isArray(locale?.points) ? locale!.points!.filter(Boolean) : [];
  const sample = (locale?.content_status || '').trim();
  const showStatus = Boolean(sample && sample !== SAMPLE_CONTENT_STATUS);
  const showTypeChip = !['faculty', 'location', 'global_placements', 'admissions'].includes(card.cardType);
  const typeChip = ['hostel', 'canteen', 'event'].includes(card.cardType)
    ? uiText(language, `cards.${card.cardType}`)
    : card.cardType;

  return (
    <div
      className="premium-stage-container"
      data-testid="campus-unit-card"
      data-unit-id={card.unitId}
      data-card-type={card.cardType}
      data-card-language={language || ''}
      data-content-status={sample}
    >
      <div className="premium-stage-border-outer" />
      <div className="premium-stage-border-inner" />
      <motion.div
        key={card.unitId}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -16 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 flex flex-col items-start w-full"
      >
        {showTypeChip ? <div className="premium-stage-chip">{typeChip}</div> : null}
        {showStatus ? <div className="premium-stage-chip mt-2">{sample}</div> : null}
        <h2 className="premium-stage-title" style={{ fontSize: '2.4rem' }}>
          {title}
        </h2>
        {body ? <p className="premium-stage-body">{body}</p> : null}
        {points.length > 0 ? (
          <ul className="premium-stage-body mt-3 list-disc pl-6">
            {points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        ) : null}
      </motion.div>
    </div>
  );
}
