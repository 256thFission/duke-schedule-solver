/**
 * Step 0: Matriculation Year
 *
 * Mandatory gate — students must indicate when they matriculated
 * because the curriculum changed for Fall 2025+ students.
 */

import useConfigStore from '../../store/configStore';

export default function Step0Year() {
  const { config, setMatriculationYear, setPratt, nextStep } = useConfigStore();

  const selectedYear = config.matriculation_year;
  const selectedSchool = config.is_pratt; // null | true | false

  const yearOptions = [
    {
      value: 'pre2025',
      title: 'Before Fall 2025',
      subtitle: 'Curriculum 2000',
      description:
        'Areas of Knowledge: ALP, CZ, NS, QS, SS and Modes of Inquiry: CCI, EI, STS, R, W, FL.',
    },
    {
      value: '2025plus',
      title: 'Fall 2025 or Later',
      subtitle: 'New Trinity Curriculum',
      description:
        '2 courses each Liberal Arts Reqs: CE, HI, IJ, NW, QC, SB',
    },
  ];

  const prattDescription = selectedYear === '2025plus'
    ? 'Must cover 4 of 5 categories: CE, HI, IJ, SB, LG'
    : '5 courses from SS/H codes (ALP, CZ, SS, FL)';

  const trinityDescription = selectedYear === '2025plus'
    ? 'Full  (CE, HI, IJ, NW, QC, SB) with 2 courses each, plus W and FL'
    : 'Full Areas of Knowledge and Modes of Inquiry';

  const canContinue = selectedYear !== null && selectedSchool !== null;

  return (
    <div className="step-container">
      <h2 className="step-title">When did you start at Duke?</h2>
      <p className="step-subtitle">
        This cannot be changed later without restarting.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-lg)' }}>
        {yearOptions.map((opt) => {
          const isSelected = selectedYear === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => setMatriculationYear(opt.value)}
              className={`select-card ${isSelected ? 'select-card--active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-md)', marginBottom: 6 }}>
                <div className={`radio-dot ${isSelected ? 'radio-dot--active' : ''}`} />
                <div>
                  <span style={{ fontWeight: 'bold', fontSize: 'var(--font-lg)' }}>{opt.title}</span>
                  <span style={{ marginLeft: 10, fontSize: 'var(--font-sm)', color: 'var(--c-text-light)', fontWeight: 'normal' }}>
                    {opt.subtitle}
                  </span>
                </div>
              </div>
              <p style={{ fontSize: 'var(--font-sm)', color: 'var(--c-text-light)', margin: '0 0 0 30px' }}>
                {opt.description}
              </p>
            </button>
          );
        })}
      </div>

      {/* School question — appears after year is selected */}
      {selectedYear && (
        <div style={{ marginTop: 'var(--sp-xxl)' }}>
          <h2 className="step-title">Which school are you in?</h2>

          <div style={{ display: 'flex', gap: 'var(--sp-lg)' }}>
            {[
              { value: false, title: 'Trinity College', subtitle: trinityDescription },
              { value: true, title: 'Pratt School of Engineering', subtitle: prattDescription },
            ].map((opt) => {
              const isSelected = selectedSchool === opt.value;
              return (
                <button
                  key={String(opt.value)}
                  onClick={() => setPratt(opt.value)}
                  className={`select-card ${isSelected ? 'select-card--active' : ''}`}
                  style={{ flex: 1 }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-md)', marginBottom: 6 }}>
                    <div className={`radio-dot ${isSelected ? 'radio-dot--active' : ''}`} />
                    <span style={{ fontWeight: 'bold', fontSize: 'var(--font-base)' }}>{opt.title}</span>
                  </div>
                  <p style={{ fontSize: 'var(--font-sm)', color: 'var(--c-text-light)', margin: '0 0 0 30px' }}>
                    {opt.subtitle}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div className="step-nav" style={{ marginTop: 'var(--sp-xxl)' }}>
        <button
          className="btn-next"
          onClick={nextStep}
          disabled={!canContinue}
        >
          {canContinue ? 'Continue' : 'Select your year and school to continue'}
        </button>
      </div>
    </div>
  );
}
