/**
 * PresentationCardModel — thin consumer of already-selected ContentUnits (M5.2).
 *
 * AUTHORITATIVE selection remains backend UnitSelector → PresentationPlan.
 * This module must NOT invent, expand, collapse, or reorder units.
 *
 * Identity rules:
 * - unitId = content identity
 * - departmentId derived from unitId (never global active department when multi-unit)
 * - cardType from unitId shape (never CI topic strings like "fees")
 *
 * Out of scope (must not map to department renderers):
 * - fees.overview
 * - documents.overview
 * - admission.documents_required
 */

export type PresentationCardType =
  | 'overview'
  | 'hod'
  | 'achievements'
  | 'placements'
  | 'department_fees'
  | 'principal'
  | 'vice_principal'
  | 'trustees'
  | 'hostel'
  | 'canteen'
  | 'event'
  | 'faculty'
  | 'location'
  | 'global_placements'
  | 'admissions'
  | 'unsupported';

export type PresentationCardModel = {
  cardId: string;
  unitId: string;
  sectionId: string | null;
  cardType: PresentationCardType;
  departmentId: string;
  title: string;
  content: string;
  cardIndex: number;
  /** Visual template slot for department overview slides (0..4). */
  slotIndex: number | null;
};

export type NarrationSegmentLike = {
  canonicalCardId?: string | null;
  unitId?: string | null;
  sectionId?: string | null;
  displayText?: string | null;
  ttsText?: string | null;
  cardIndex?: number | null;
};

/** Canonical backend card ID → the one existing renderer configuration. */
export function cardTypeFromCanonicalCardId(cardId: string): PresentationCardType {
  switch ((cardId || '').trim().toLowerCase()) {
    case 'department_overview': return 'overview';
    case 'hod_profile': return 'hod';
    case 'achievements': return 'achievements';
    case 'placements': return 'placements';
    case 'fees': return 'department_fees';
    case 'principal_profile': return 'principal';
    case 'vice_principal_profile': return 'vice_principal';
    case 'trustees': return 'trustees';
    case 'hostel': return 'hostel';
    case 'canteen': return 'canteen';
    case 'event': return 'event';
    case 'faculty_list': return 'faculty';
    case 'location': return 'location';
    case 'admissions': return 'admissions';
    default: return 'unsupported';
  }
}

/** Entity id from unit identity: `hostel.girls.rooms` → `hostel.girls`, `cse_aiml.hod` → `cse_aiml`. */
export function departmentIdFromUnitId(unitId: string): string {
  const uid = (unitId || '').trim();
  if (!uid) return '';
  if (uid.startsWith('college.')) return '';
  if (uid.startsWith('hostel.')) {
    const parts = uid.split('.');
    return parts.length >= 2 ? `${parts[0]}.${parts[1]}` : uid;
  }
  const dot = uid.indexOf('.');
  return dot > 0 ? uid.slice(0, dot) : uid;
}

/**
 * Map unitId → renderer type by unit identity shape only.
 * Never map fees.overview / documents.* here.
 */
export function cardTypeFromUnitId(unitId: string): PresentationCardType {
  const uid = (unitId || '').trim().toLowerCase();
  if (!uid || !uid.includes('.')) return 'unsupported';

  // Protect M5.0 identity: global fees/documents are not department fees cards.
  if (uid === 'fees.overview' || uid.startsWith('fees.')) return 'unsupported';
  if (uid === 'documents.overview' || uid === 'admission.documents_required') return 'unsupported';
  if (uid.startsWith('documents.') || uid.startsWith('admission.')) return 'unsupported';

  if (uid === 'leadership.principal') return 'principal';
  if (uid === 'leadership.vice_principal') return 'vice_principal';
  if (uid === 'leadership.trustees') return 'trustees';
  if (uid.startsWith('hostel.')) return 'hostel';
  if (uid.startsWith('canteen.')) return 'canteen';
  if (uid.startsWith('events.')) return 'event';
  if (uid === 'college.location') return 'location';
  if (uid === 'college.placements') return 'global_placements';
  if (uid === 'college.admissions') return 'admissions';

  const suffix = uid.split('.').slice(1).join('.');
  if (suffix === 'overview') return 'overview';
  if (suffix === 'hod') return 'hod';
  if (suffix === 'achievements') return 'achievements';
  if (suffix === 'placements') return 'placements';
  if (suffix === 'fees') return 'department_fees';
  if (suffix === 'faculty') return 'faculty';
  return 'unsupported';
}

export function slotIndexFromCardType(cardType: PresentationCardType): number | null {
  switch (cardType) {
    case 'overview':
      return 0;
    case 'hod':
      return 1;
    case 'achievements':
      return 2;
    case 'placements':
      return 3;
    case 'department_fees':
      return 4;
    default:
      return null;
  }
}

function splitDisplay(displayText: string | null | undefined): { title: string; content: string } {
  const raw = (displayText || '').trim();
  if (!raw) return { title: '', content: '' };
  const nl = raw.indexOf('\n');
  if (nl < 0) return { title: raw, content: '' };
  return { title: raw.slice(0, nl).trim(), content: raw.slice(nl + 1).trim() };
}

/**
 * Build ordered PresentationCardModel[] from narration_plan segments.
 * One model per unitId; preserve order; no expansion to a fixed five-card deck.
 */
export function presentationCardsFromNarrationSegments(
  segments: NarrationSegmentLike[] | null | undefined,
): PresentationCardModel[] {
  const list = Array.isArray(segments) ? segments : [];
  const out: PresentationCardModel[] = [];
  const seen = new Set<string>();

  list.forEach((seg, i) => {
    const unitId = typeof seg?.unitId === 'string' ? seg.unitId.trim() : '';
    if (!unitId || seen.has(unitId)) return;
    seen.add(unitId);

    const cardId = typeof seg?.canonicalCardId === 'string' ? seg.canonicalCardId.trim() : '';
    const cardType = unitId.startsWith('college.')
      ? cardTypeFromUnitId(unitId)
      : cardId
        ? cardTypeFromCanonicalCardId(cardId)
        : cardTypeFromUnitId(unitId);
    const departmentId = departmentIdFromUnitId(unitId);
    const { title, content } = splitDisplay(seg.displayText);
    const cardIndex =
      typeof seg.cardIndex === 'number' && Number.isFinite(seg.cardIndex)
        ? Math.max(0, Math.floor(seg.cardIndex))
        : out.length;

    out.push({
      cardId: cardId || unitId,
      unitId,
      sectionId:
        typeof seg.sectionId === 'string' && seg.sectionId.trim() ? seg.sectionId.trim() : null,
      cardType,
      departmentId,
      title,
      content: content || (typeof seg.ttsText === 'string' ? seg.ttsText.trim() : ''),
      cardIndex,
      slotIndex: slotIndexFromCardType(cardType),
    });
  });

  // Re-index densely in selection order (UI position, not content identity).
  return out.map((m, idx) => ({ ...m, cardIndex: idx }));
}

export function selectedUnitIds(models: PresentationCardModel[]): string[] {
  return models.map((m) => m.unitId);
}

/** Map json department key → DepartmentCardFactory label (renderer only; not selection). */
export function factoryDepartmentLabelFromJsonKey(jsonKey: string): string {
  const k = (jsonKey || '').trim().toLowerCase();
  const map: Record<string, string> = {
    cse: 'CSE',
    ise: 'ISE',
    cse_aiml: 'CSE (AI & ML)',
    cse_ds: 'CSE (Data Science)',
    cse_cysec: 'CSE (Cyber Security)',
    cse_bs: 'CSE (Business Systems)',
    ece: 'ECE',
    civil: 'Civil',
    mechanical: 'Mechanical',
    mba: 'MBA',
    mathematics: 'Mathematics',
    physics: 'Physics',
    chemistry: 'Chemistry',
    basic_sciences: 'Basic Sciences',
  };
  return map[k] || jsonKey;
}

/** True when UnitSelector selected a department `{dept}.placements` unit. */
export function hasDepartmentPlacementUnit(models: PresentationCardModel[]): boolean {
  return models.some(
    (m) => m.cardType === 'placements' && Boolean(m.departmentId) && m.departmentId !== 'placements',
  );
}

/**
 * College-wide placement slides are a legacy `showCard=placements` surface.
 * They must not replace a selected `{dept}.placements` unit.
 */
export function shouldUseCollegeWidePlacementDeck(
  cardTrigger: string | null | undefined,
  models: PresentationCardModel[],
): boolean {
  if ((cardTrigger || '').trim() !== 'placements') return false;
  return !hasDepartmentPlacementUnit(models);
}
