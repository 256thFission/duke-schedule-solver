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

  return (
    <div style={{ maxWidth: '700px', margin: '0 auto', padding: '0 16px' }}>
      <h2 style={{ fontSize: 'clamp(1.5rem, 4vw, 2rem)', marginBottom: '0.5rem' }}>What kind of semester do you want?</h2>
      <p style={{ fontSize: 'clamp(0.9rem, 2.5vw, 1rem)', color: '#6b7280' }}>Choose a preset or customize your preferences with the sliders below.</p>

      {/* Preset Buttons */}
      <fieldset>
        <legend>Quick Presets</legend>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '12px',
            marginBottom: '20px',
          }}
        >
          {[
            { key: 'chill', label: 'Chill' },
            { key: 'balanced', label: 'Balanced' },
            { key: 'best_profs', label: 'Best Profs' },
            { key: 'grindset', label: 'Grindset' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handlePresetClick(key)}
              style={{
                padding: 'clamp(12px, 3vw, 16px)',
                fontSize: 'clamp(14px, 3vw, 16px)',
                border: activePreset === key ? '4px solid #10b981' : '2px solid #d1d5db',
                backgroundColor: activePreset === key ? '#d1fae5' : 'white',
                borderRadius: '8px',
                cursor: 'pointer',
                minHeight: '100px',
              }}
            >
              <strong style={{ fontSize: 'clamp(14px, 3vw, 16px)' }}>{label}</strong>
            </button>
          ))}
        </div>
      </fieldset>

      {/* Custom Sliders */}
      <fieldset>
        <legend>Custom Preferences</legend>

        {activePreset && (
          <p style={{ fontSize: 'clamp(12px, 2.5vw, 13px)', color: '#6b7280', marginBottom: '16px' }}>
            Preset active: <strong>{activePreset}</strong>. Move any slider to customize.
          </p>
        )}

        {/* Difficulty Slider */}
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="difficulty" style={{ fontSize: 'clamp(14px, 3vw, 16px)', display: 'block', marginBottom: '8px' }}>
            Difficulty: <strong>{config.weights.difficulty_target}</strong>/10
          </label>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 'clamp(11px, 2.5vw, 12px)', color: '#6b7280', minWidth: 'clamp(60px, 15vw, 80px)' }}>Easy A</span>
            <input
              id="difficulty"
              type="range"
              min="1"
              max="10"
              value={config.weights.difficulty_target}
              onChange={(e) => handleSliderChange('difficulty_target', e.target.value)}
              style={{ flex: '1', minWidth: '120px' }}
            />
            <span style={{ fontSize: 'clamp(11px, 2.5vw, 12px)', color: '#6b7280', minWidth: 'clamp(80px, 20vw, 100px)', textAlign: 'right' }}>
              Challenge Me
            </span>
          </div>
        </div>

        {/* Workload Slider */}
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="workload" style={{ fontSize: 'clamp(14px, 3vw, 16px)', display: 'block', marginBottom: '8px' }}>
            Workload: <strong>{config.weights.workload_target}</strong>/10
          </label>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 'clamp(11px, 2.5vw, 12px)', color: '#6b7280', minWidth: 'clamp(60px, 15vw, 80px)' }}>Light</span>
            <input
              id="workload"
              type="range"
              min="1"
              max="10"
              value={config.weights.workload_target}
              onChange={(e) => handleSliderChange('workload_target', e.target.value)}
              style={{ flex: '1', minWidth: '120px' }}
            />
            <span style={{ fontSize: 'clamp(11px, 2.5vw, 12px)', color: '#6b7280', minWidth: 'clamp(80px, 20vw, 100px)', textAlign: 'right' }}>
              Heavy
            </span>
          </div>
        </div>

        {/* Instructor Quality Slider */}
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="instructor" style={{ fontSize: 'clamp(14px, 3vw, 16px)', display: 'block', marginBottom: '8px' }}>
            Instructor Quality: <strong>{config.weights.instructor_priority}</strong>/10
          </label>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 'clamp(11px, 2.5vw, 12px)', color: '#6b7280', minWidth: 'clamp(60px, 15vw, 80px)' }}>Flexible</span>
            <input
              id="instructor"
              type="range"
              min="1"
              max="10"
              value={config.weights.instructor_priority}
              onChange={(e) => handleSliderChange('instructor_priority', e.target.value)}
              style={{ flex: '1', minWidth: '120px' }}
            />
            <span style={{ fontSize: 'clamp(11px, 2.5vw, 12px)', color: '#6b7280', minWidth: 'clamp(80px, 20vw, 100px)', textAlign: 'right' }}>
              Top Tier Only
            </span>
          </div>
        </div>

        {/* Course Quality Slider */}
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="quality" style={{ fontSize: 'clamp(14px, 3vw, 16px)', display: 'block', marginBottom: '8px' }}>
            Course Quality: <strong>{config.weights.quality_priority}</strong>/10
          </label>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 'clamp(11px, 2.5vw, 12px)', color: '#6b7280', minWidth: 'clamp(60px, 15vw, 80px)' }}>Flexible</span>
            <input
              id="quality"
              type="range"
              min="1"
              max="10"
              value={config.weights.quality_priority}
              onChange={(e) => handleSliderChange('quality_priority', e.target.value)}
              style={{ flex: '1', minWidth: '120px' }}
            />
            <span style={{ fontSize: 'clamp(11px, 2.5vw, 12px)', color: '#6b7280', minWidth: 'clamp(80px, 20vw, 100px)', textAlign: 'right' }}>
              Top Tier Only
            </span>
          </div>
        </div>
      </fieldset>

      <div style={{ display: 'flex', gap: '12px', marginTop: '24px', flexWrap: 'wrap' }}>
        <button 
          onClick={prevStep} 
          style={{ 
            flex: '1',
            minWidth: '120px',
            padding: '12px 16px',
            fontSize: 'clamp(14px, 3vw, 16px)'
          }}
        >
          ← Back
        </button>
        <button 
          onClick={nextStep} 
          style={{ 
            flex: '2',
            minWidth: '150px',
            padding: '12px 16px',
            fontSize: 'clamp(14px, 3vw, 16px)'
          }}
        >
          Next: Logistics →
        </button>
      </div>
    </div>
  );
}
