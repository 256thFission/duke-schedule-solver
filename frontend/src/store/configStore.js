/**
 * Zustand Store for Duke Schedule Solver
 *
 * This is the Single Source of Truth for all application state.
 * The config object flows through the entire application.
 */

import { create } from 'zustand';

const useConfigStore = create((set) => ({
  // -------------------------------------------------------------------------
  // The Single Config Object (JSON Source of Truth)
  // -------------------------------------------------------------------------
  config: {
    matriculation_year: null,  // 'pre2025' or '2025plus'
    is_pratt: null,              // null = unselected, true = Pratt, false = Trinity
    user_class_year: null,
    completed_courses: [],
    required_courses: [],
    required_course_credits: {},
    total_credits: 4.0,
    weights: {
      difficulty_target: 5,
      workload_target: 5,
      instructor_priority: 8,
      quality_priority: 8,
    },
    constraints: {
      earliest_class_time: '09:00',
      min_days_off: 2,
      weekdays_only: true,
    },
    requirements: {
      attributes: [],
      min_count: 0,
    },
  },

  // -------------------------------------------------------------------------
  // Wizard Navigation State
  // -------------------------------------------------------------------------
  currentStep: 1,
  totalSteps: 7,
  maxStepVisited: 1,

  // -------------------------------------------------------------------------
  // Results State
  // -------------------------------------------------------------------------
  schedules: [],
  currentScheduleIndex: 0,
  isLoading: false,
  error: null,

  // -------------------------------------------------------------------------
  // Graduation Requirements State
  // -------------------------------------------------------------------------
  graduationRequirements: null,
  demoUploadResult: null,

  // -------------------------------------------------------------------------
  // Preset State
  // -------------------------------------------------------------------------
  activePreset: null,

  // -------------------------------------------------------------------------
  // Actions: Config Updates
  // -------------------------------------------------------------------------

  setMatriculationYear: (year) =>
    set((state) => ({
      config: { ...state.config, matriculation_year: year },
    })),

  setPratt: (isPratt) =>
    set((state) => ({
      config: { ...state.config, is_pratt: isPratt },
    })),

  updateConfig: (updates) =>
    set((state) => ({
      config: { ...state.config, ...updates },
    })),

  updateWeights: (weights) =>
    set((state) => ({
      config: {
        ...state.config,
        weights: { ...state.config.weights, ...weights },
      },
      activePreset: null,
    })),

  updateConstraints: (constraints) =>
    set((state) => ({
      config: {
        ...state.config,
        constraints: { ...state.config.constraints, ...constraints },
      },
    })),

  updateRequirements: (requirements) =>
    set((state) => ({
      config: {
        ...state.config,
        requirements: { ...state.config.requirements, ...requirements },
      },
    })),

  setCompletedCourses: (courses, classYear, graduationRequirements = null) =>
    set((state) => ({
      config: {
        ...state.config,
        completed_courses: courses,
        user_class_year: classYear,
      },
      graduationRequirements,
    })),

  addRequiredCourse: (courseId, credits = 1.0) =>
    set((state) => ({
      config: {
        ...state.config,
        required_courses: [...state.config.required_courses, courseId],
        required_course_credits: {
          ...state.config.required_course_credits,
          [courseId]: credits,
        },
      },
    })),

  removeRequiredCourse: (courseId) =>
    set((state) => {
      const { [courseId]: _, ...restCredits } = state.config.required_course_credits;
      return {
        config: {
          ...state.config,
          required_courses: state.config.required_courses.filter(
            (id) => id !== courseId
          ),
          required_course_credits: restCredits,
        },
      };
    }),

  toggleAttribute: (attribute) =>
    set((state) => {
      const currentAttrs = state.config.requirements.attributes;
      const newAttrs = currentAttrs.includes(attribute)
        ? currentAttrs.filter((a) => a !== attribute)
        : [...currentAttrs, attribute];

      return {
        config: {
          ...state.config,
          requirements: {
            ...state.config.requirements,
            attributes: newAttrs,
            min_count: newAttrs.length > 0 ? Math.max(1, state.config.requirements.min_count) : 0,
          },
        },
      };
    }),

  // -------------------------------------------------------------------------
  // Actions: Preset Buttons
  // -------------------------------------------------------------------------

  applyPreset: (presetName) =>
    set((state) => {
      const presets = {
        chill: {
          difficulty_target: 1,
          workload_target: 1,
          instructor_priority: 5,
          quality_priority: 5,
        },
        balanced: {
          difficulty_target: 4,
          workload_target: 4,
          instructor_priority: 7,
          quality_priority: 7,
        },
        best_profs: {
          difficulty_target: 4,
          workload_target: 4,
          instructor_priority: 10,
          quality_priority: 5,
        },
        grindset: {
          difficulty_target: 5,
          workload_target: 5,
          instructor_priority: 7,
          quality_priority: 10,
        },
      };

      return {
        config: {
          ...state.config,
          weights: presets[presetName],
        },
        activePreset: presetName,
      };
    }),

  clearDemoUploadResult: () => set({ demoUploadResult: null }),

  applyDemoMode: () =>
    set((state) => {
      const demoMatchedCourses = [
        'STA-199L', 'CHINESE-101', 'COMPSCI-201', 'MATH-221', 'MATH-212',
        'STA-221L', 'STA-240L', 'MATH-431', 'STA-323L', 'STA-332',
        'AMES-353S', 'CHINESE-102', 'CINE-257S', 'ECS-101', 'STA-402L',
      ];
      const demoUnmatchedCourses = [
        'BIOLOGY 21', 'CHEM 21', 'ENGLISH 22', 'HISTORY 21',
        'MATH 21', 'MATH 22', 'PSY 11', 'WRITING 101',
        'ENVIRON 245', 'GSF 89S', 'STA 671D',
      ];

      const mkReq = (code, name, required, completed, courses) => ({
        code, name, required, completed,
        remaining: Math.max(0, required - completed),
        is_complete: completed >= required,
        progress_percent: required > 0 ? Math.min(100, (completed / required) * 100) : 100,
        courses,
      });

      const graduationRequirements = {
        areas_of_knowledge: {
          ALP: mkReq('ALP', 'Arts, Literature, and Performance', 2, 1, ['CINE-257S']),
          CZ:  mkReq('CZ',  'Civilizations', 2, 1, ['AMES-353S']),
          NS:  mkReq('NS',  'Natural Sciences', 2, 0, []),
          QS:  mkReq('QS',  'Quantitative Studies', 2, 2, ['STA-199L', 'COMPSCI-201']),
          SS:  mkReq('SS',  'Social Sciences', 2, 1, ['ECS-101']),
        },
        modes_of_inquiry: {
          CCI: mkReq('CCI', 'Cross-Cultural Inquiry', 2, 1, ['AMES-353S']),
          EI:  mkReq('EI',  'Ethical Inquiry', 2, 1, ['ECS-101']),
          STS: mkReq('STS', 'Science, Technology, and Society', 2, 0, []),
          R:   mkReq('R',   'Research', 2, 1, ['STA-402L']),
          W:   mkReq('W',   'Writing', 3, 0, []),
          FL:  mkReq('FL',  'Foreign Language', 1, 1, ['CHINESE-102']),
        },
        needed_attributes: ['ALP', 'CZ', 'NS', 'SS', 'CCI', 'EI', 'STS', 'R', 'W'],
        overall_progress_percent: 36,
      };

      const demoUploadResult = {
        success: true,
        completed_courses: demoMatchedCourses,
        class_year: 'sophomore',
        total_extracted: demoMatchedCourses.length + demoUnmatchedCourses.length,
        matched: demoMatchedCourses.length,
        unmatched: demoUnmatchedCourses.length,
        unmatched_courses: demoUnmatchedCourses,
        graduation_requirements: graduationRequirements,
      };

      return {
        config: {
          ...state.config,
          matriculation_year: 'pre2025',
          is_pratt: false,
          user_class_year: 'sophomore',
          completed_courses: demoMatchedCourses,
          required_courses: ['STA-440L'],
          required_course_credits: { 'STA-440L': 1.0 },
          total_credits: 4.0,
          weights: {
            difficulty_target: 1,
            workload_target: 1,
            instructor_priority: 5,
            quality_priority: 5,
          },
          constraints: {
            earliest_class_time: '09:00',
            min_days_off: 1,
            weekdays_only: true,
          },
          requirements: {
            attributes: graduationRequirements.needed_attributes,
            min_count: 1,
          },
        },
        graduationRequirements,
        demoUploadResult,
        activePreset: 'chill',
        currentStep: 2,
        maxStepVisited: state.totalSteps - 1,
        schedules: [],
        currentScheduleIndex: 0,
        error: null,
      };
    }),

  // -------------------------------------------------------------------------
  // Actions: Wizard Navigation
  // -------------------------------------------------------------------------

  nextStep: () =>
    set((state) => {
      const next = Math.min(state.currentStep + 1, state.totalSteps);
      return {
        currentStep: next,
        maxStepVisited: Math.max(state.maxStepVisited, next),
      };
    }),

  prevStep: () =>
    set((state) => ({
      currentStep: Math.max(state.currentStep - 1, 1),
    })),

  goToStep: (step) =>
    set((state) => ({
      currentStep: step,
      maxStepVisited: Math.max(state.maxStepVisited, step),
    })),

  // -------------------------------------------------------------------------
  // Actions: Results Management
  // -------------------------------------------------------------------------

  setSchedules: (schedules) =>
    set({
      schedules,
      currentScheduleIndex: 0,
      currentStep: 7,
      maxStepVisited: 7,
    }),

  nextSchedule: () =>
    set((state) => ({
      currentScheduleIndex:
        (state.currentScheduleIndex + 1) % state.schedules.length,
    })),

  prevSchedule: () =>
    set((state) => ({
      currentScheduleIndex:
        state.currentScheduleIndex > 0
          ? state.currentScheduleIndex - 1
          : state.schedules.length - 1,
    })),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null }),

  // -------------------------------------------------------------------------
  // Actions: Reset
  // -------------------------------------------------------------------------

  reset: () =>
    set({
      config: {
        matriculation_year: null,
        is_pratt: null,
        user_class_year: null,
        completed_courses: [],
        required_courses: [],
        required_course_credits: {},
        total_credits: 4.0,
        weights: {
          difficulty_target: 5,
          workload_target: 5,
          instructor_priority: 8,
          quality_priority: 8,
        },
        constraints: {
          earliest_class_time: '09:00',
          min_days_off: 2,
          weekdays_only: true,
        },
        requirements: {
          attributes: [],
          min_count: 0,
        },
      },
      currentStep: 1,
      maxStepVisited: 1,
      schedules: [],
      currentScheduleIndex: 0,
      isLoading: false,
      error: null,
      activePreset: null,
      graduationRequirements: null,
      demoUploadResult: null,
    }),
}));

export default useConfigStore;
