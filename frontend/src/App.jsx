/**
 * Duke Schedule Solver - Main App Component
 *
 * Wizard-based interface with 7 steps.
 */

import useConfigStore from './store/configStore';
import Step0Year from './components/steps/Step0Year';
import Step1Upload from './components/steps/Step1Upload';
import Step2MustTakes from './components/steps/Step2MustTakes';
import Step3Requirements from './components/steps/Step3Requirements';
import Step4Preferences from './components/steps/Step4Preferences';
import Step5Logistics from './components/steps/Step5Logistics';
import Step6Results from './components/steps/Step6Results';

const steps = [
  { number: 1, title: 'Year', component: Step0Year },
  { number: 2, title: 'Upload', component: Step1Upload },
  { number: 3, title: 'Courses', component: Step2MustTakes },
  { number: 4, title: 'Gen Eds', component: Step3Requirements },
  { number: 5, title: 'Preferences', component: Step4Preferences },
  { number: 6, title: 'Logistics', component: Step5Logistics },
  { number: 7, title: 'Results', component: Step6Results },
];

function App() {
  const { currentStep, config, error, applyDemoMode } = useConfigStore();
  const demoAvailable = config.completed_courses.length === 0;

  const CurrentStepComponent = steps[currentStep - 1].component;

  return (
    <div style={{ minHeight: '100vh', padding: 20, backgroundColor: 'var(--c-bg)' }}>
      {/* Header */}
      <header style={{ textAlign: 'center', marginBottom: 40 }}>
        <h1 style={{ fontSize: 'var(--font-xxl)', marginBottom: 'var(--sp-sm)' }}>
          Duke Schedule Solver
        </h1>
        <p style={{ fontSize: 'var(--font-base)', color: 'var(--c-text-light)' }}>
          Mathematically optimize the liberal arts education :D
        </p>
      </header>

      {/* Global Error Display */}
      {error && currentStep !== 7 && (
        <div
          className="banner banner--error"
          style={{ maxWidth: 'var(--w-narrow)', margin: '0 auto 20px' }}
        >
          {error}
        </div>
      )}

      {/* Current Step Content */}
      <main>
        <CurrentStepComponent />
      </main>

      {/* Footer */}
      <footer style={{ textAlign: 'center', marginTop: 60, fontSize: 'var(--font-sm)', color: 'var(--c-text-muted)' }}>
        <p>Built by <a href="https://philliplin.dev" target="_blank" rel="noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>Phillip Lin</a>. <a href="mailto:thephilliplin@gmail.com" style={{ color: 'inherit', textDecoration: 'underline' }}>Hire me if it helps!</a></p>
        {config.completed_courses.length > 0 && (
          <p style={{ marginTop: 'var(--sp-sm)', fontSize: 'var(--font-xs)' }}>
            {config.completed_courses.length} completed courses loaded |{' '}
            {config.required_courses.length} must-takes selected
          </p>
        )}
        {demoAvailable && (
          <div style={{ marginTop: 'var(--sp-lg)' }}>
            <button
              onClick={applyDemoMode}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 'var(--sp-sm)',
                border: '2px solid var(--c-text-muted)',
                backgroundColor: 'var(--c-surface-dim)',
                color: 'var(--c-text)',
                borderRadius: 'var(--r-pill)',
                padding: 'var(--sp-sm) var(--sp-md)',
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
              Press to Demo With My Schedule!
            </button>
          </div>
        )}
      </footer>
    </div>
  );
}

export default App;

