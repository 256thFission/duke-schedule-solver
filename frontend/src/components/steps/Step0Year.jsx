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
        'Areas of Knowledge (ALP, CZ, NS, QS, SS) and Modes of Inquiry (CCI, EI, STS, R, W, FL). Writing 101 required.',
    },
    {
      value: '2025plus',
      title: 'Fall 2025 or Later',
      subtitle: 'New Trinity Curriculum',
      description:
        'Liberal Arts Distribution (CE, HI, IJ, NW, QC, SB) with 2 courses each. Writing 120 required.',
    },
  ];

  const prattDescription = selectedYear === '2025plus'
    ? '5 courses from Liberal Arts codes (CE, HI, IJ, SB, LG). Must cover 4 of 5 categories.'
    : '5 courses from SS/H codes (ALP, CZ, SS, FL). Depth requirement: 2 courses in one subject.';

  const trinityDescription = selectedYear === '2025plus'
    ? 'Full  (CE, HI, IJ, NW, QC, SB) with 2 courses each, plus W and FL.'
    : 'Full Areas of Knowledge and Modes of Inquiry.';

  const canContinue = selectedYear !== null && selectedSchool !== null;

  return (
    <div style={{ maxWidth: 660, margin: '0 auto' }}>
      <h2>When did you start at Duke?</h2>
      <p style={{ fontSize: 13, color: '#9ca3af', marginBottom: 24 }}>
        This cannot be changed later without restarting ;-;.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {yearOptions.map((opt) => {
          const isSelected = selectedYear === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => setMatriculationYear(opt.value)}
              style={{
                padding: '20px 24px',
                textAlign: 'left',
                border: isSelected ? '3px solid #3b82f6' : '2px solid #d1d5db',
                backgroundColor: isSelected ? '#eff6ff' : 'white',
                borderRadius: 12,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    border: isSelected ? '6px solid #3b82f6' : '2px solid #d1d5db',
                    backgroundColor: 'white',
                    flexShrink: 0,
                  }}
                />
                <div>
                  <span style={{ fontWeight: 'bold', fontSize: 18 }}>{opt.title}</span>
                  <span
                    style={{
                      marginLeft: 10,
                      fontSize: 13,
                      color: '#6b7280',
                      fontWeight: 'normal',
                    }}
                  >
                    {opt.subtitle}
                  </span>
                </div>
              </div>
              <p style={{ fontSize: 13, color: '#6b7280', margin: '0 0 0 32px' }}>
                {opt.description}
              </p>
            </button>
          );
        })}
      </div>

      {/* School question — appears after year is selected */}
      {selectedYear && (
        <div style={{ marginTop: 32 }}>
          <h2>Which school are you in?</h2>

          <div style={{ display: 'flex', gap: 16 }}>
            {[
              { value: false, title: 'Trinity College', subtitle: trinityDescription },
              { value: true, title: 'Pratt School of Engineering', subtitle: prattDescription },
            ].map((opt) => {
              const isSelected = selectedSchool === opt.value;
              return (
                <button
                  key={String(opt.value)}
                  onClick={() => setPratt(opt.value)}
                  style={{
                    flex: 1,
                    padding: '20px 24px',
                    textAlign: 'left',
                    border: isSelected ? '3px solid #3b82f6' : '2px solid #d1d5db',
                    backgroundColor: isSelected ? '#eff6ff' : 'white',
                    borderRadius: 12,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
                    <div
                      style={{
                        width: 20,
                        height: 20,
                        borderRadius: '50%',
                        border: isSelected ? '6px solid #3b82f6' : '2px solid #d1d5db',
                        backgroundColor: 'white',
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontWeight: 'bold', fontSize: 16 }}>{opt.title}</span>
                  </div>
                  <p style={{ fontSize: 13, color: '#6b7280', margin: '0 0 0 32px' }}>
                    {opt.subtitle}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div style={{ marginTop: 32 }}>
        <button
          onClick={nextStep}
          disabled={!canContinue}
          style={{
            width: '100%',
            padding: '14px',
            fontSize: 16,
            fontWeight: 'bold',
            backgroundColor: canContinue ? '#3b82f6' : '#d1d5db',
            color: canContinue ? 'white' : '#9ca3af',
            border: 'none',
            borderRadius: 8,
            cursor: canContinue ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s',
          }}
        >
          {canContinue ? 'Continue' : 'Select your year and school to continue'}
        </button>
      </div>
    </div>
  );
}
