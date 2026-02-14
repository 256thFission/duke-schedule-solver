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
    user_class_year: null,
    completed_courses: [],
    required_courses: [],
    num_courses: 4,
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

  addRequiredCourse: (courseId) =>
    set((state) => ({
      config: {
        ...state.config,
        required_courses: [...state.config.required_courses, courseId],
      },
    })),

  removeRequiredCourse: (courseId) =>
    set((state) => ({
      config: {
        ...state.config,
        required_courses: state.config.required_courses.filter(
          (id) => id !== courseId
        ),
      },
    })),

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
          difficulty_target: 2,
          workload_target: 2,
          instructor_priority: 5,
          quality_priority: 5,
        },
        balanced: {
          difficulty_target: 5,
          workload_target: 5,
          instructor_priority: 7,
          quality_priority: 7,
        },
        best_profs: {
          difficulty_target: 4,
          workload_target: 4,
          instructor_priority: 10,
          quality_priority: 10,
        },
        grindset: {
          difficulty_target: 9,
          workload_target: 9,
          instructor_priority: 7,
          quality_priority: 9,
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
        user_class_year: null,
        completed_courses: [],
        required_courses: [],
        num_courses: 4,
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
    }),
}));

export default useConfigStore;
