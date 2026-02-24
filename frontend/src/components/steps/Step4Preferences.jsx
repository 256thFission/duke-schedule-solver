/**
 * Step 4: Preferences (Sliders + Presets)
 *
 * Core feature: 4 sliders (1-10 scale) + 3 preset buttons.
 * Moving any slider manually deselects the active preset.
 */

import useConfigStore from '../../store/configStore';

export default function Step4Preferences() {
  const { config, updateWeights, applyPreset, activePreset, nextStep, prevStep } = useConfigStore();

  const handleSliderChange = (key, value) => {
    updateWeights({ [key]: parseInt(value, 10) });
  };

  const handlePresetClick = (presetName) => {
    applyPreset(presetName);
  };

  const sliders = [
    { id: 'difficulty', key: 'difficulty_target', label: 'Difficulty', low: 'Easy A', high: 'Challenge Me' },
    { id: 'workload', key: 'workload_target', label: 'Workload', low: 'Light', high: 'Heavy' },
    { id: 'instructor', key: 'instructor_priority', label: 'Instructor Quality', low: 'Flexible', high: 'Top Tier Only' },
    { id: 'quality', key: 'quality_priority', label: 'Course Quality', low: 'Flexible', high: 'Top Tier Only' },
  ];

  return (
    <div className="step-container">
      <h2 className="step-title">What kind of semester do you want?</h2>
      <p className="step-subtitle">Choose a preset or customize your preferences with the sliders below.</p>

      {/* Preset Buttons */}
      <fieldset>
        <legend>Quick Presets</legend>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 'var(--sp-md)' }}>
          {[
            { key: 'chill', label: 'Light-work' },
            { key: 'balanced', label: 'Balanced' },
            { key: 'best_profs', label: 'BestProfs' },
            { key: 'grindset', label: 'Interesting Topics' },
          ].map(({ key, label }) => {
            const active = activePreset === key;
            return (
              <button
                key={key}
                onClick={() => handlePresetClick(key)}
                className={`select-card ${active ? 'select-card--active' : ''}`}
                style={{
                  textAlign: 'center',
                  padding: 'var(--sp-lg)',
                  borderColor: active ? 'var(--c-success)' : undefined,
                  backgroundColor: active ? 'var(--c-success-light)' : undefined,
                }}
              >
                <strong style={{ fontSize: 'var(--font-base)' }}>{label}</strong>
              </button>
            );
          })}
        </div>
      </fieldset>

      {/* Custom Sliders */}
      <fieldset className="field-gap">
        <legend>Custom Preferences</legend>

        {activePreset && (
          <p className="field-hint">
            Preset active: <strong>{activePreset}</strong>. Move any slider to customize.
          </p>
        )}

        {sliders.map(({ id, key, label, low, high }) => (
          <div key={id} style={{ marginBottom: 20 }}>
            <label htmlFor={id} style={{ fontSize: 'var(--font-base)', display: 'block', marginBottom: 'var(--sp-sm)' }}>
              {label}: <strong>{config.weights[key]}</strong>/10
            </label>
            <div style={{ display: 'flex', gap: 'var(--sp-md)', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-light)', minWidth: 70 }}>{low}</span>
              <input
                id={id}
                type="range"
                min="1"
                max="10"
                value={config.weights[key]}
                onChange={(e) => handleSliderChange(key, e.target.value)}
                style={{ flex: 1 }}
              />
              <span style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-light)', minWidth: 80, textAlign: 'right' }}>
                {high}
              </span>
            </div>
          </div>
        ))}
      </fieldset>

      <div className="step-nav">
        <button className="btn-back" onClick={prevStep}>Back</button>
        <button className="btn-next" onClick={nextStep}>Next: Logistics</button>
      </div>
    </div>
  );
}
