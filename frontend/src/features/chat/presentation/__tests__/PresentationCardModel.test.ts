import { describe, expect, it } from 'vitest';
import {
  cardTypeFromCanonicalCardId,
  cardTypeFromUnitId,
  departmentIdFromUnitId,
  factoryDepartmentLabelFromJsonKey,
  hasDepartmentPlacementUnit,
  presentationCardsFromNarrationSegments,
  selectedUnitIds,
  shouldUseCollegeWidePlacementDeck,
} from '../PresentationCardModel';

describe('PresentationCardModel identity helpers', () => {
  it('maps canonical card IDs independently of localized text and unit shape', () => {
    expect(cardTypeFromCanonicalCardId('department_overview')).toBe('overview');
    expect(cardTypeFromCanonicalCardId('hod_profile')).toBe('hod');
    expect(cardTypeFromCanonicalCardId('fees')).toBe('department_fees');
    expect(cardTypeFromCanonicalCardId('principal_profile')).toBe('principal');
    expect(cardTypeFromCanonicalCardId('faculty_list')).toBe('faculty');
    expect(cardTypeFromCanonicalCardId('location')).toBe('location');
  });

  it('derives departmentId from unitId (never collapses multi-HOD)', () => {
    expect(departmentIdFromUnitId('cse_aiml.hod')).toBe('cse_aiml');
    expect(departmentIdFromUnitId('cse_ds.hod')).toBe('cse_ds');
    expect(departmentIdFromUnitId('cse.fees')).toBe('cse');
    expect(departmentIdFromUnitId('college.location')).toBe('');
  });

  it('maps department unit shapes by unitId, not topic name', () => {
    expect(cardTypeFromUnitId('cse.overview')).toBe('overview');
    expect(cardTypeFromUnitId('cse.hod')).toBe('hod');
    expect(cardTypeFromUnitId('cse.achievements')).toBe('achievements');
    expect(cardTypeFromUnitId('cse.placements')).toBe('placements');
    expect(cardTypeFromUnitId('cse.fees')).toBe('department_fees');
    expect(cardTypeFromUnitId('leadership.principal')).toBe('principal');
    expect(cardTypeFromUnitId('leadership.vice_principal')).toBe('vice_principal');
    expect(cardTypeFromUnitId('leadership.trustees')).toBe('trustees');
    expect(cardTypeFromUnitId('hostel.girls.rooms')).toBe('hostel');
    expect(cardTypeFromUnitId('hostel.boys.fees')).toBe('hostel');
    expect(cardTypeFromUnitId('canteen.hygiene')).toBe('canteen');
    expect(cardTypeFromUnitId('events.techvidya')).toBe('event');
    expect(cardTypeFromUnitId('cse.faculty')).toBe('faculty');
    expect(cardTypeFromUnitId('college.location')).toBe('location');
    expect(cardTypeFromUnitId('college.placements')).toBe('global_placements');
    expect(cardTypeFromUnitId('college.admissions')).toBe('admissions');
    expect(cardTypeFromUnitId('cse_bs.overview')).toBe('overview');
    expect(cardTypeFromUnitId('cse_bs.hod')).toBe('hod');
    expect(cardTypeFromUnitId('cse_bs.achievements')).toBe('achievements');
    expect(cardTypeFromUnitId('cse_bs.placements')).toBe('placements');
    expect(cardTypeFromUnitId('cse_bs.fees')).toBe('department_fees');
  });

  it('never maps fees.overview / documents identities to department fees', () => {
    expect(cardTypeFromUnitId('fees.overview')).toBe('unsupported');
    expect(cardTypeFromUnitId('documents.overview')).toBe('unsupported');
    expect(cardTypeFromUnitId('admission.documents_required')).toBe('unsupported');
  });
});

describe('presentationCardsFromNarrationSegments — no hidden expansion', () => {
  it('builds N models from N unitIds in order', () => {
    const models = presentationCardsFromNarrationSegments([
      { canonicalCardId: 'department_overview', unitId: 'cse.overview', sectionId: 'intro', displayText: 'Overview\nBody', cardIndex: 0 },
      { canonicalCardId: 'hod_profile', unitId: 'cse.hod', sectionId: 'hod_voice', displayText: 'HOD\nBody', cardIndex: 1 },
      { canonicalCardId: 'fees', unitId: 'cse.fees', sectionId: 'fees', displayText: 'Fees\nBody', cardIndex: 2 },
    ]);
    expect(selectedUnitIds(models)).toEqual(['cse.overview', 'cse.hod', 'cse.fees']);
    expect(models.map((model) => model.cardId)).toEqual([
      'department_overview',
      'hod_profile',
      'fees',
    ]);
    expect(models).toHaveLength(3);
  });

  it('builds mixed campus units without collapsing them', () => {
    const models = presentationCardsFromNarrationSegments([
      { unitId: 'hostel.girls.rooms', displayText: 'Rooms\nBody', cardIndex: 0 },
      { unitId: 'canteen.hygiene', displayText: 'Hygiene\nBody', cardIndex: 1 },
      { unitId: 'events.techvidya', displayText: 'TechVidya\nBody', cardIndex: 2 },
    ]);
    expect(selectedUnitIds(models)).toEqual([
      'hostel.girls.rooms',
      'canteen.hygiene',
      'events.techvidya',
    ]);
    expect(models.map((m) => m.cardType)).toEqual(['hostel', 'canteen', 'event']);
    expect(models[0]!.departmentId).toBe('hostel.girls');
  });

  it('builds five models from five unitIds with no expansion', () => {
    const models = presentationCardsFromNarrationSegments([
      { unitId: 'cse.overview', sectionId: 'intro', displayText: 'Overview\nBody', cardIndex: 0 },
      { unitId: 'cse.hod', sectionId: 'hod_voice', displayText: 'HOD\nBody', cardIndex: 1 },
      { unitId: 'cse.achievements', sectionId: 'achievements', displayText: 'Ach\nBody', cardIndex: 2 },
      { unitId: 'cse.placements', sectionId: 'placement', displayText: 'Pl\nBody', cardIndex: 3 },
      { unitId: 'cse.fees', sectionId: 'fees', displayText: 'Fees\nBody', cardIndex: 4 },
    ]);
    expect(selectedUnitIds(models)).toEqual([
      'cse.overview',
      'cse.hod',
      'cse.achievements',
      'cse.placements',
      'cse.fees',
    ]);
    expect(models).toHaveLength(5);
  });

  it('singleton fees does not expand to five siblings', () => {
    const models = presentationCardsFromNarrationSegments([
      { unitId: 'cse.fees', sectionId: 'fees', displayText: 'Fees\nBody', cardIndex: 0 },
    ]);
    expect(models).toHaveLength(1);
    expect(models[0]!.unitId).toBe('cse.fees');
    expect(models[0]!.cardType).toBe('department_fees');
    expect(models[0]!.departmentId).toBe('cse');
    const ids = selectedUnitIds(models);
    for (const sibling of ['cse.overview', 'cse.hod', 'cse.achievements', 'cse.placements']) {
      expect(ids).not.toContain(sibling);
    }
  });

  it('multi-HOD departmentIds come from each unitId', () => {
    const models = presentationCardsFromNarrationSegments([
      {
        unitId: 'cse_aiml.hod',
        sectionId: 'hod_voice',
        displayText: 'AIML HOD\nBody',
        cardIndex: 0,
      },
      {
        unitId: 'cse_ds.hod',
        sectionId: 'hod_voice',
        displayText: 'DS HOD\nBody',
        cardIndex: 1,
      },
    ]);
    expect(models).toHaveLength(2);
    expect(models.map((m) => m.departmentId)).toEqual(['cse_aiml', 'cse_ds']);
    expect(models.every((m) => m.sectionId === 'hod_voice')).toBe(true);
    expect(models.every((m) => m.cardType === 'hod')).toBe(true);
  });

  it('keeps three HOD models when sectionId repeats', () => {
    const models = presentationCardsFromNarrationSegments([
      { unitId: 'cse_aiml.hod', sectionId: 'hod_voice', displayText: 'A\n1', cardIndex: 0 },
      { unitId: 'cse_ds.hod', sectionId: 'hod_voice', displayText: 'B\n2', cardIndex: 1 },
      { unitId: 'cse.hod', sectionId: 'hod_voice', displayText: 'C\n3', cardIndex: 2 },
    ]);
    expect(selectedUnitIds(models)).toEqual(['cse_aiml.hod', 'cse_ds.hod', 'cse.hod']);
    expect(models.every((m) => m.sectionId === 'hod_voice')).toBe(true);
  });

  it('skips segments without unitId and does not invent units', () => {
    const models = presentationCardsFromNarrationSegments([
      { sectionId: 'intro', displayText: 'legacy', cardIndex: 0 },
      { unitId: 'cse.overview', sectionId: 'intro', displayText: 'Overview\nBody', cardIndex: 1 },
    ]);
    expect(selectedUnitIds(models)).toEqual(['cse.overview']);
  });
});

describe('cse_bs factory identity', () => {
  it('maps cse_bs to CSE (Business Systems) and does not collapse to CSE', () => {
    expect(factoryDepartmentLabelFromJsonKey('cse_bs')).toBe('CSE (Business Systems)');
    expect(factoryDepartmentLabelFromJsonKey('cse')).toBe('CSE');
    expect(departmentIdFromUnitId('cse_bs.overview')).toBe('cse_bs');
    expect(departmentIdFromUnitId('cse_bs.hod')).toBe('cse_bs');
    expect(departmentIdFromUnitId('cse_bs.achievements')).toBe('cse_bs');
    expect(departmentIdFromUnitId('cse_bs.placements')).toBe('cse_bs');
    expect(departmentIdFromUnitId('cse_bs.fees')).toBe('cse_bs');
  });
});

describe('department placements vs college-wide deck', () => {
  it('keeps a singleton department placements unit as that department', () => {
    const models = presentationCardsFromNarrationSegments([
      { unitId: 'cse_ds.placements', sectionId: 'placement', displayText: 'Placements\nDS body', cardIndex: 0 },
    ]);
    expect(models).toHaveLength(1);
    expect(models[0]!.unitId).toBe('cse_ds.placements');
    expect(models[0]!.departmentId).toBe('cse_ds');
    expect(hasDepartmentPlacementUnit(models)).toBe(true);
    expect(shouldUseCollegeWidePlacementDeck('department_overview', models)).toBe(false);
    expect(shouldUseCollegeWidePlacementDeck('placements', models)).toBe(false);
  });

  it('preserves college-wide placements when no department unit is selected', () => {
    expect(shouldUseCollegeWidePlacementDeck('placements', [])).toBe(true);
    expect(shouldUseCollegeWidePlacementDeck('department_overview', [])).toBe(false);
  });

  it('keeps placements identity in a multi-unit plan', () => {
    const models = presentationCardsFromNarrationSegments([
      { unitId: 'cse_ds.hod', sectionId: 'hod_voice', displayText: 'HOD\nBody', cardIndex: 0 },
      { unitId: 'cse_ds.placements', sectionId: 'placement', displayText: 'Placements\nDS body', cardIndex: 1 },
    ]);
    expect(selectedUnitIds(models)).toEqual(['cse_ds.hod', 'cse_ds.placements']);
    expect(hasDepartmentPlacementUnit(models)).toBe(true);
    expect(shouldUseCollegeWidePlacementDeck('placements', models)).toBe(false);
  });
});
