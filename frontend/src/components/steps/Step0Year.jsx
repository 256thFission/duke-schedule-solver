/**
 * Step 0: Matriculation Year
 *
 * Mandatory gate — students must indicate when they matriculated
 * because the curriculum changed for Fall 2025+ students.
 */

import useConfigStore from '../../store/configStore';

export default function Step0Year() {
  const { config, setMatriculationYear, nextStep } = useConfigStore();

  const selected = config.matriculation_year;

  const handleSelect = (value) => {
    setMatriculationYear(value);
  };

  const options = [
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

  return (
    <div style={{ maxWidth: 660, margin: '0 auto' }}>
      <h2>When did you start at Duke?</h2>
      <p style={{ color: '#6b7280', marginBottom: 8 }}>
        Duke changed the Trinity Arts &amp; Sciences curriculum starting Fall 2025.
        Your matriculation date determines which graduation requirements apply to you.
      </p>
      <p style={{ fontSize: 13, color: '#9ca3af', marginBottom: 24 }}>
        This cannot be changed later without restarting the wizard.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {options.map((opt) => {
          const isSelected = selected === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => handleSelect(opt.value)}
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
                    backgroundColor: isSelected ? 'white' : 'white',
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

      <div style={{ marginTop: 32 }}>
        <button
          onClick={nextStep}
          disabled={!selected}
          style={{
            width: '100%',
            padding: '14px',
            fontSize: 16,
            fontWeight: 'bold',
            backgroundColor: selected ? '#3b82f6' : '#d1d5db',
            color: selected ? 'white' : '#9ca3af',
            border: 'none',
            borderRadius: 8,
            cursor: selected ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s',
          }}
        >
          {selected ? 'Continue' : 'Select your matriculation period to continue'}
        </button>
      </div>
    </div>
  );
}
