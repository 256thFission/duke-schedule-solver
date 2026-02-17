/**
 * Duke Schedule Solver - Main App Component
 *
 * Wizard-based interface with 6 steps.
 * Progress bar allows navigation to any previously visited step.
 */

import useConfigStore from './store/configStore';
import Step0Year from './components/steps/Step0Year';
import Step1Upload from './components/steps/Step1Upload';
import Step2MustTakes from './components/steps/Step2MustTakes';
import Step3Requirements from './components/steps/Step3Requirements';
import Step4Preferences from './components/steps/Step4Preferences';
import Step5Logistics from './components/steps/Step5Logistics';
import Step6Results from './components/steps/Step6Results';

function App() {
  const {
    currentStep,
    totalSteps,
    maxStepVisited,
    goToStep,
    config,
    error,
    applyDemoMode,
  } = useConfigStore();

  const steps = [
    { number: 1, title: 'Year', component: Step0Year },
    { number: 2, title: 'Upload', component: Step1Upload },
    { number: 3, title: 'Courses', component: Step2MustTakes },
    { number: 4, title: 'Gen Eds', component: Step3Requirements },
    { number: 5, title: 'Preferences', component: Step4Preferences },
    { number: 6, title: 'Logistics', component: Step5Logistics },
    { number: 7, title: 'Results', component: Step6Results },
  ];

  const CurrentStepComponent = steps[currentStep - 1].component;

  return (
    <div style={{ minHeight: '100vh', padding: '20px', backgroundColor: '#FDF7F1' }}>
      {/* Header */}
      <header style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '36px', marginBottom: '8px' }}>
          Duke Schedule Solver
        </h1>
        <p style={{ fontSize: '16px', color: '#6b7280' }}>
         Mathmatically optimize the liberal arts education :D
        </p>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 10,
            position: 'relative',
          }}
        >
          <button
            onClick={applyDemoMode}
            title="or demo it as me!"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              border: '2px solid #f59e0b',
              backgroundColor: '#fff7ed',
              color: '#9a3412',
              borderRadius: 999,
              padding: '8px 14px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <img
              src="/doodle/star.svg"
              alt=""
              aria-hidden="true"
              style={{ width: 16, height: 16 }}
            />
            Demo Mode
          </button>
          <span style={{ fontSize: 12, color: '#b45309' }}>or demo it as me!</span>
        </div>
      </header>

      {/* Progress Indicator */}
      <div style={{ maxWidth: '900px', margin: '0 auto 40px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            position: 'relative',
          }}
        >
          {/* Progress Line (background) */}
          <div
            style={{
              position: 'absolute',
              top: '16px',
              left: '0',
              right: '0',
              height: '4px',
              backgroundColor: '#e5e7eb',
              zIndex: 0,
            }}
          >
            {/* Filled portion up to current step */}
            <div
              style={{
                height: '100%',
                backgroundColor: '#3b82f6',
                width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%`,
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          {/* Step Circles */}
          {steps.map((step) => {
            const isCurrent = step.number === currentStep;
            const isVisited = step.number <= maxStepVisited;
            const isPast = step.number < currentStep;
            const isClickable = isVisited && !isCurrent;

            return (
              <button
                key={step.number}
                onClick={() => isClickable && goToStep(step.number)}
                disabled={!isVisited}
                style={{
                  position: 'relative',
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  border: '3px solid',
                  borderColor: isCurrent || isPast ? '#3b82f6' : isVisited ? '#93c5fd' : '#d1d5db',
                  backgroundColor: isCurrent || isPast ? '#3b82f6' : isVisited ? '#dbeafe' : 'white',
                  color: isCurrent || isPast ? 'white' : isVisited ? '#3b82f6' : '#9ca3af',
                  fontWeight: 'bold',
                  cursor: isClickable ? 'pointer' : 'default',
                  zIndex: 1,
                  transition: 'all 0.3s ease',
                }}
              >
                {step.number}
              </button>
            );
          })}
        </div>

        {/* Step Labels */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginTop: '8px',
          }}
        >
          {steps.map((step) => {
            const isCurrent = step.number === currentStep;
            const isVisited = step.number <= maxStepVisited;
            return (
              <div
                key={step.number}
                style={{
                  width: '36px',
                  textAlign: 'center',
                  fontSize: '11px',
                  color: isCurrent ? '#3b82f6' : isVisited ? '#6b7280' : '#d1d5db',
                  fontWeight: isCurrent ? 'bold' : 'normal',
                }}
              >
                {step.title}
              </div>
            );
          })}
        </div>
      </div>

      {/* Global Error Display */}
      {error && currentStep !== 7 && (
        <div
          style={{
            maxWidth: '700px',
            margin: '0 auto 20px',
            padding: '12px',
            backgroundColor: '#fef2f2',
            border: '2px solid #fecaca',
            borderRadius: '6px',
            color: '#dc2626',
          }}
        >
          {error}
        </div>
      )}

      {/* Current Step Content */}
      <main>
        <CurrentStepComponent />
      </main>

      {/* Footer */}
      <footer style={{ textAlign: 'center', marginTop: '60px', fontSize: '14px', color: '#9ca3af' }}>
        <p>
          Built for Duke students
        </p>
        {config.completed_courses.length > 0 && (
          <p style={{ marginTop: '8px', fontSize: '12px' }}>
            {config.completed_courses.length} completed courses loaded |{' '}
            {config.required_courses.length} must-takes selected
          </p>
        )}
      </footer>
    </div>
  );
}

export default App;
