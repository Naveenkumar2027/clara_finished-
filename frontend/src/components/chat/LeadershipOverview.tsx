import React from 'react';
import { AnimatePresence, motion } from 'motion/react';
import type { CardDataItem } from '../../lib/cardData';
import type { PresentationCardModel } from '../../features/chat/presentation/PresentationCardModel';
import ThreeDVisual from './cards/ThreeDVisual';
import PremiumHODCard from './cards/PremiumHODCard';
import { useCollegeData } from '../../hooks/useCollegeData';
import { useLanguage } from '../../context/LanguageContext';
import { buildDepartmentSlideForUnit } from '../../lib/collegeLocaleUtils';
import hodCseImg from '../../assets/hod_cse.jpg';
import hodAimlImg from '../../assets/hod_aiml.jpg';
import hodEceImg from '../../assets/hod_ece.jpg';
import hodCivilImg from '../../assets/hod_civil.jpg';
import hodMechanicalImg from '../../assets/hod_mechanical.jpg';
import hodDsImg from '../../assets/hod_datascience.png';
import hodChemImg from '../../assets/hod_chemistry.jpg';
import hodPhysicsImg from '../../assets/hod_physics.jpeg';
import hodMathsImg from '../../assets/hod_maths.jpg';
import { collegeLogoMark as placeholderImg } from '../../assets/logo';

const HOD_PORTRAITS: Record<string, string> = {
  cse: hodCseImg,
  cse_aiml: hodAimlImg,
  cse_ds: hodDsImg,
  ece: hodEceImg,
  ise: placeholderImg,
  civil: hodCivilImg,
  mechanical: hodMechanicalImg,
  mba: placeholderImg,
  mathematics: hodMathsImg,
  physics: hodPhysicsImg,
  chemistry: hodChemImg,
};

type HodFallback = { name: string; title: string; bio: string };

const HOD_FALLBACK: Record<string, HodFallback> = {
  cse: {
    name: 'Dr. Shashikumar D R',
    title: 'Professor & HOD, Computer Science & Engineering',
    bio: 'With extensive teaching and research experience in core computer science, Dr. Shashikumar D R leads the CSE department with a strong focus on fundamentals and industry-oriented learning. He has guided multiple student projects, promotes coding culture and hackathons, and actively works on curriculum enhancement aligned with emerging technologies. His areas of interest span algorithms, software engineering, and modern computing practices.',
  },
  cse_aiml: {
    name: 'Dr. T G Manjunatha',
    title: 'Professor & HOD, CSE (Artificial Intelligence & Machine Learning)',
    bio: 'Dr. T G Manjunatha heads the AIML department, emphasizing solid foundations in AI, machine learning, and data-driven problem solving. He has significant academic and research experience, guiding projects that apply AI techniques to real-world applications. Under his leadership, the department conducts workshops, coding events, and hands-on sessions to build strong practical skills.',
  },
  cse_ds: {
    name: 'Dr. Nagashree N',
    title: 'Associate Professor & HOD, CSE (Data Science)',
    bio: 'With 20 years of experience, Dr. Nagashree N holds a Ph.D. from Visvesvaraya Technological University and specializes in Data Science, Machine Learning, and Deep Learning. She has over 35 publications in international journals and conferences, reflecting strong research contributions. As HOD of CSE (Data Science), she leads initiatives that blend theory with practical analytics and AI applications for real-world problems.',
  },
  ise: {
    name: 'Dr. Vrinda Shetty',
    title: 'Professor & HOD, Information Science & Engineering',
    bio: 'Dr. Vrinda Shetty leads the ISE department with a focus on information systems, data management, and modern software technologies. She has rich teaching experience and encourages students to work on industry-relevant projects and internships. Her interests include databases, networking, and emerging trends in information science.',
  },
  ece: {
    name: 'Dr. Venkatesha M',
    title: 'Professor & HOD, Electronics & Communication Engineering',
    bio: 'Dr. Venkatesha M heads the ECE department, focusing on core electronics, communication systems, and embedded technologies. He has many years of academic experience and actively supports student participation in hardware projects and research. His work spans VLSI, communication networks, and applied electronics.',
  },
  civil: {
    name: 'Dr. Ananthayya M B',
    title: 'Professor & HOD, Civil Engineering',
    bio: 'Dr. Ananthayya M B leads the Civil Engineering department with emphasis on structural, environmental, and construction engineering. He has considerable teaching and field experience, encouraging students to engage in practical design and site-related learning. His academic interests cover core civil domains and sustainable infrastructure.',
  },
  mechanical: {
    name: 'Dr. Raghavendra S',
    title: 'Professor & HOD, Mechanical Engineering',
    bio: 'Dr. Raghavendra S heads the Mechanical Engineering department, focusing on design, manufacturing, and thermal engineering. He has strong academic and research exposure and supports project-based learning, labs, and industry interaction. His interests include advanced manufacturing and applied mechanics.',
  },
  mba: {
    name: 'Dr. Jogish D',
    title: 'Professor & HOD, Master of Business Administration (MBA)',
    bio: 'Dr. Jogish D leads the MBA department, integrating management education with practical exposure to industry practices. He has experience in teaching, training, and consultancy, guiding students towards careers in business, analytics, and entrepreneurship. His interests span marketing, strategy, and organizational development.',
  },
  mathematics: {
    name: 'Dr. Arun Kumar R',
    title: 'Professor & HOD, Mathematics',
    bio: 'Dr. Arun Kumar R heads the Mathematics department, ensuring strong mathematical foundations for all engineering disciplines. He has extensive teaching experience and focuses on applied mathematics relevant to engineering and data analysis. His work supports advanced courses and research that rely on rigorous quantitative skills.',
  },
  physics: {
    name: 'Dr. Shankar P',
    title: 'Professor & HOD, Physics',
    bio: 'Dr. Shankar P leads the Physics department, concentrating on engineering physics and fundamental science education. He emphasizes conceptual clarity and experimental skills through well-designed laboratory work. His interests include materials, electronics-related physics, and applied physical sciences.',
  },
  chemistry: {
    name: 'Dr. Bhagya N P',
    title: 'Professor & HOD, Chemistry',
    bio: 'Dr. Bhagya N P heads the Chemistry department, teaching engineering chemistry and its applications in materials and environmental domains. She has strong academic experience and promotes lab-based learning to connect theory with practice. Her interests lie in applied chemistry relevant to engineering and industry processes.',
  },
};

export type HodUnitCopy = {
  unitId: string;
  departmentId: string;
  label: string;
  name: string;
  title: string;
  bio: string;
};

/**
 * Unit-backed HOD text: PresentationCardModel is authoritative.
 * Locale name/title may decorate when present in the *current* language.
 * English HOD_FALLBACK must never replace an available localized body.
 */
export function hodCopyFromUnitCard(
  model: PresentationCardModel,
  localeRow?: { hod_name?: string; hod_title?: string } | null,
): HodUnitCopy {
  const label = (model.title || '').trim() || 'Faculty Spotlight';
  const bio = (model.content || '').trim();
  const localeName = localeRow?.hod_name?.trim() || '';
  const localeTitle = localeRow?.hod_title?.trim() || '';
  return {
    unitId: model.unitId,
    departmentId: model.departmentId,
    label,
    name: localeName || label,
    title: localeTitle,
    bio: bio || localeTitle || label,
  };
}

export function toDepartmentKey(targetDepartment: string | null | undefined): string | null {
  if (!targetDepartment) return null;
  const raw = targetDepartment.trim().toLowerCase();
  if (!raw) return null;
  const canonical = new Set([
    'cse',
    'cse_aiml',
    'cse_ds',
    'cse_cysec',
    'cse_bs',
    'ise',
    'ece',
    'civil',
    'mechanical',
    'mba',
    'mathematics',
    'physics',
    'chemistry',
  ]);
  if (canonical.has(raw)) return raw;
  if (raw.includes('data science') || (raw.includes('cse') && raw.includes('data'))) return 'cse_ds';
  if (
    raw.includes('aiml') ||
    raw.includes('ai & ml') ||
    raw.includes('ai and ml') ||
    (raw.includes('artificial intelligence') && raw.includes('machine learning'))
  ) return 'cse_aiml';
  if (raw === 'ec' || raw.includes('ece') || raw.includes('electronics')) return 'ece';
  if (raw.includes('ise') || raw.includes('information science')) return 'ise';
  if (raw.includes('civil')) return 'civil';
  if (raw.includes('mechanical') || raw === 'mech') return 'mechanical';
  if (raw.includes('mba') || raw.includes('management')) return 'mba';
  if (raw.includes('mathematics') || raw.includes('math')) return 'mathematics';
  if (raw.includes('physics')) return 'physics';
  if (raw.includes('chemistry')) return 'chemistry';
  if (raw.includes('business system') || (raw.includes('cse') && raw.includes('business'))) return 'cse_bs';
  if (raw.includes('cse') || raw.includes('computer')) return 'cse';
  return null;
}

/**
 * Card stack for leadership / HOD overviews (and other static card lists).
 * One card per entry; syncs with `currentCardIdx` from TTS-driven progression.
 */
export default function LeadershipOverview({
  cards,
  currentCardIdx,
  targetDepartment,
  targetDepartments,
  unitCards,
  onCardClick,
}: {
  cards: CardDataItem[];
  currentCardIdx: number;
  targetDepartment?: string | null;
  targetDepartments?: string[] | null;
  unitCards?: PresentationCardModel[] | null;
  onCardClick?: (idx: number) => void;
}) {
  const collegeData = useCollegeData();
  const { language } = useLanguage();

  const hodModels = Array.isArray(unitCards)
    ? unitCards.filter((m) => m.cardType === 'hod' && m.unitId)
    : [];

  if (hodModels.length) {
    const safeIdx = Math.min(Math.max(0, currentCardIdx), hodModels.length - 1);
    const model = hodModels[safeIdx]!;
    const deptKey = toDepartmentKey(model.departmentId) || model.departmentId;
    const row = deptKey ? collegeData.role_holders?.hod_by_department?.[deptKey] : undefined;
    const copy = hodCopyFromUnitCard(model, row);
    return (
      <div
        className="w-full h-full flex items-center justify-center"
        data-testid="hod-card"
        data-unit-id={copy.unitId}
        data-hod-dept={deptKey}
        data-hod-count={hodModels.length}
        data-card-index={safeIdx}
      >
        <PremiumHODCard
          name={copy.name}
          title={copy.title}
          bio={copy.bio}
          label={copy.label}
          portrait={HOD_PORTRAITS[deptKey] ?? placeholderImg}
        />
      </div>
    );
  }

  const resolvedDepartments =
    (Array.isArray(targetDepartments) && targetDepartments.length
      ? targetDepartments
      : targetDepartment
        ? [targetDepartment]
        : []) ?? [];

  // Legacy non-unit HOD path (no PresentationCardModel).
  if (resolvedDepartments.length) {
    const safeIdx = Math.min(
      Math.max(0, currentCardIdx),
      Math.max(0, resolvedDepartments.length - 1),
    );
    const deptId = resolvedDepartments[safeIdx];
    const deptKey = toDepartmentKey(deptId);
    const roleHolders = collegeData.role_holders?.hod_by_department;
    const row = deptKey ? roleHolders?.[deptKey] : undefined;
    const fallback = deptKey ? HOD_FALLBACK[deptKey] : undefined;
    const localizedHod = deptKey
      ? buildDepartmentSlideForUnit(collegeData, `${deptKey}.hod`, language)
      : null;
    const name = row?.hod_name || fallback?.name;
    const title = row?.hod_title || fallback?.title;
    const bio = row?.hod_bio || localizedHod?.content || fallback?.bio;
    if (deptKey && name && title && bio) {
      return (
        <div
          className="w-full h-full flex items-center justify-center"
          data-testid="hod-card"
          data-hod-dept={deptKey}
          data-hod-count={resolvedDepartments.length}
          data-card-index={safeIdx}
        >
          <PremiumHODCard
            name={name}
            title={title}
            bio={bio}
            label={localizedHod?.title}
            portrait={HOD_PORTRAITS[deptKey] ?? placeholderImg}
          />
        </div>
      );
    }
  }

  if (!cards.length) {
    return (
      <div className="cinematic-card">
        <p className="card-body">No overview cards to display.</p>
      </div>
    );
  }

  const safeIdx = Math.min(Math.max(0, currentCardIdx), cards.length - 1);
  const current = cards[safeIdx];

  return (
    <AnimatePresence mode="wait">
      {current && (
        <motion.div
          key={safeIdx}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="cinematic-card"
        >
          <div className="flex-1">
            <h2 className="card-title">{current.title}</h2>
            <p className="card-body">{current.content}</p>
          </div>
          <div className="w-[50%] h-[40%] self-end bg-slate-50 rounded-3xl overflow-hidden mt-6 border border-slate-200 shadow-sm">
            <ThreeDVisual type={current.type} />
          </div>
          <div className="mt-auto flex gap-4 pt-8">
            {cards.map((_, i) => (
              <button
                key={`overview-progress-${i}`}
                onClick={() => onCardClick?.(i)}
                aria-label={`Go to card ${i + 1}`}
                className={`h-2 flex-1 rounded-full cursor-pointer transition-colors ${
                  i === safeIdx ? 'bg-violet-600' : 'bg-slate-200 hover:bg-violet-300'
                }`}
              />
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
