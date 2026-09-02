import React from 'react';
import { motion } from 'motion/react';
import { useLanguage } from '../../context/LanguageContext';

export default function CourseMenuComponent({
  options,
  onSelect,
}: {
  options: string[];
  onSelect: (departmentName: string) => void;
}) {
  const { t } = useLanguage();

  const activeOptions = options && options.length > 0
    ? options
    : ['CSE', 'AIML', 'ISE', 'ECE', 'Mechanical', 'Civil', 'MBA', 'Data Science', 'Cyber Security'];

  return (
    <div data-testid="course-menu" className="absolute inset-0 z-50 overflow-y-auto no-scrollbar">
      <div className="w-full max-w-[1240px] mx-auto flex flex-col gap-8 min-h-full py-12 px-6">
        
        {/* Header */}
        <motion.div className="text-center">
          <div className="text-sm font-semibold tracking-widest uppercase text-violet-500 mb-2">{t('menuEngineering') || 'Academic Programs'}</div>
          <h2 className="text-4xl font-display font-bold text-slate-800">{t('menuSelectDept') || 'Select a Department'}</h2>
        </motion.div>

        {/* The Grid */}
        <div className="w-full flex flex-wrap gap-4 justify-center items-start">
          {activeOptions.map((dept, idx) => {
            return (
              <motion.button
                key={dept}
                data-testid={`course-menu-option-${idx}`}
                layoutId={`dept-${dept}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: idx * 0.04, ease: [0.16, 1, 0.3, 1] }}
                onClick={() => onSelect(dept)}
                className="relative flex flex-col justify-center rounded-3xl glass transition-all overflow-hidden border border-white/40 isolation-auto cursor-pointer hover:shadow-lg active:scale-[0.98] bg-white/40"
                style={{ width: 'calc(33.333% - 1rem)', minHeight: '130px', minWidth: '260px' }}
              >
                <div className="p-6 w-full h-full flex flex-col justify-center text-left">
                  <h3 className="font-semibold text-slate-800 tracking-tight text-xl">{t(dept)}</h3>
                  <span className="text-xs text-violet-500 font-medium mt-2 uppercase tracking-widest">{t('menuOverview') || 'Explore Program'}</span>
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
