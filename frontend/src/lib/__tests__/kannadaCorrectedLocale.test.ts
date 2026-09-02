import { describe, expect, it } from 'vitest';

import authoritativeKannada from '@college-locales/kn.json';
import { getScriptTypography } from '../../features/chat/typography/scriptTypography';
import { collegeDataForLanguage } from '../../hooks/useCollegeData';
import {
  buildDepartmentSlideForUnit,
  buildPlacementCardsFromLocale,
} from '../collegeLocaleUtils';
import { PRINCIPAL_COPY, VICE_PRINCIPAL_COPY } from '../executiveLeadershipLocale';

type AuthoritativeKannada = {
  departments: Record<string, {
    intro?: string;
    hod_voice?: string;
    achievements?: string;
    fees?: string;
  }>;
  placements_and_training: {
    additional_details: {
      objectives: string[];
      training_programs: string[];
    };
  };
  role_holders: {
    principal: { name: string; title: string; profile: string };
    vice_principal: { name: string; title: string; profile: string };
    trustees: Array<{ designation?: string }>;
    hod_by_department: Record<string, { department_name?: string }>;
  };
};

const authoritative = authoritativeKannada as unknown as AuthoritativeKannada;


describe('approved Kannada V2 locale integration', () => {
  it('uses the authoritative backend locale import', () => {
    const fromRuntimeLoader = collegeDataForLanguage('Kannada');

    expect(fromRuntimeLoader).toBe(authoritativeKannada);
    expect(fromRuntimeLoader.departments?.cse?.intro).toBe(
      authoritative.departments['cse'].intro,
    );
    expect(fromRuntimeLoader.departments?.mba?.hod_voice).toBe(
      authoritative.departments['mba'].hod_voice,
    );
  });

  it('reconstructs department slides from the corrected backend values exactly', () => {
    const locale = collegeDataForLanguage('Kannada');
    const cseOverview = buildDepartmentSlideForUnit(locale, 'cse.overview', 'Kannada');
    const cseHod = buildDepartmentSlideForUnit(locale, 'cse.hod', 'Kannada');
    const eceAchievements = buildDepartmentSlideForUnit(locale, 'ece.achievements', 'Kannada');
    const mbaHod = buildDepartmentSlideForUnit(locale, 'mba.hod', 'Kannada');
    const mbaFees = buildDepartmentSlideForUnit(locale, 'mba.fees', 'Kannada');

    expect(cseOverview?.content).toBe(authoritative.departments['cse'].intro);
    expect(cseHod?.content).toBe(authoritative.departments['cse'].hod_voice);
    expect(eceAchievements?.content).toBe(authoritative.departments['ece'].achievements);
    expect(mbaHod?.content).toBe(authoritative.departments['mba'].hod_voice);
    expect(mbaFees?.content).toBe(authoritative.departments['mba'].fees);
    expect(mbaHod?.content).toContain('ಡಾ. ಜೋಗೀಶ್ ಡಿ');
    expect(mbaHod?.content).toContain('25+');
    expect(mbaHod?.content).toContain('HR');
    expect(mbaHod?.content).toContain('IT');
  });

  it('keeps role-holder display values and placement array authority intact', () => {
    const locale = collegeDataForLanguage('Kannada');
    const holders = locale.role_holders;
    const placement = buildPlacementCardsFromLocale(locale, 'Kannada');
    const details = authoritative.placements_and_training.additional_details;

    expect(holders?.trustees?.[1]?.designation).toBe(
      authoritative.role_holders.trustees[1].designation,
    );
    expect(holders?.trustees?.[3]?.designation).toBe(
      authoritative.role_holders.trustees[3].designation,
    );
    expect(holders?.trustees?.[5]?.designation).toBe(
      authoritative.role_holders.trustees[5].designation,
    );
    expect(holders?.hod_by_department?.mathematics?.department_name).toBe(
      authoritative.role_holders.hod_by_department['mathematics'].department_name,
    );
    expect(holders?.hod_by_department?.physics?.department_name).toBe(
      authoritative.role_holders.hod_by_department['physics'].department_name,
    );
    expect(holders?.hod_by_department?.chemistry?.department_name).toBe(
      authoritative.role_holders.hod_by_department['chemistry'].department_name,
    );

    expect(placement[0]?.content).toBe(details.objectives.join('\n'));
    expect(placement[1]?.content).toBe(details.training_programs.join('\n'));
    expect(placement[2]?.content).not.toContain('…');
    expect(placement[2]?.content).toContain(details.objectives[2]);
    expect(placement[2]?.content).toContain(details.training_programs[4]);
  });

  it('drives Kannada executive cards from the authoritative role-holder locale', () => {
    const holders = authoritative.role_holders;

    expect(PRINCIPAL_COPY.Kannada.name).toBe(holders.principal.name);
    expect(PRINCIPAL_COPY.Kannada.title).toBe(holders.principal.title);
    expect(PRINCIPAL_COPY.Kannada.bio).toBe(holders.principal.profile);
    expect(VICE_PRINCIPAL_COPY.Kannada.name).toBe(holders.vice_principal.name);
    expect(VICE_PRINCIPAL_COPY.Kannada.title).toBe(holders.vice_principal.title);
    expect(VICE_PRINCIPAL_COPY.Kannada.bio).toBe(holders.vice_principal.profile);
  });

  it('selects the explicit Kannada font preset', () => {
    const typography = getScriptTypography('Kannada');

    expect(typography.cssClass).toBe('script-typo-kn');
    expect(typography.fontFamily).toContain('Noto Sans Kannada');
  });
});
