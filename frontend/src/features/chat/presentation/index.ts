export type {
  PresentationEngineState,
  PresentationScene,
  PresentationSnapshot,
  NarrationPlanInput,
  PresentationPlaybackEvent,
} from './types';

export {
  planToScenes,
  cardsToScenes,
  singleScenePresentation,
  mintPresentationId,
  mintAudioToken,
  mapSceneToComparisonSection,
} from './planToScenes';

export {
  unitIdsFromSegments,
  loadedSceneUnitIds,
  shouldLoadUnitPlan,
  shouldAllowLegacySingle,
  unitSequencesEqual,
} from './presentationOwnership';

export {
  presentationCardsFromNarrationSegments,
  departmentIdFromUnitId,
  cardTypeFromUnitId,
  cardTypeFromCanonicalCardId,
  selectedUnitIds,
} from './PresentationCardModel';
export type { PresentationCardModel, PresentationCardType } from './PresentationCardModel';
export { parseCardNavigationCommand } from './cardNavigation';
export type { CardNavigationDirection } from './cardNavigation';

export {
  buildTimelineFromPlan,
  validateTimeline,
} from './presentationTimeline';
export type { PresentationTimeline, TimelineEntry } from './presentationTimeline';

export { PresentationEngine, type LoadPresentationArgs } from './PresentationEngine';
export { PresentationAudioManager } from './PresentationAudioManager';
export {
  usePresentationController,
  type PresentationControllerApi,
} from './PresentationController';
