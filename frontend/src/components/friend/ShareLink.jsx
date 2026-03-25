/**
 * ShareLink — displays the shareable URL with a copy button.
 */

import { useState } from 'react';

export default function ShareLink({ url }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 14px',
        backgroundColor: 'var(--c-surface)',
        border: '2px solid #76bed0',
        borderRadius: 'var(--r-md)',
        marginBottom: 24,
      }}
    >
      <span style={{ fontWeight: 700, fontSize: 'var(--font-sm)', color: '#76bed0', whiteSpace: 'nowrap' }}>
        Share this link:
      </span>
      <input
        readOnly
        value={url}
        onClick={(e) => e.target.select()}
        style={{
          flex: 1,
          padding: '4px 8px',
          fontSize: 'var(--font-sm)',
          border: '1px solid var(--c-border)',
          borderRadius: 'var(--r-sm)',
          backgroundColor: 'var(--c-surface)',
          minWidth: 0,
        }}
      />
      <button
        onClick={handleCopy}
        style={{
          padding: '4px 12px',
          fontSize: 'var(--font-sm)',
          fontWeight: 600,
          backgroundColor: copied ? 'var(--c-success)' : '#76bed0',
          color: 'white',
          border: 'none',
          borderRadius: 'var(--r-sm)',
          cursor: 'pointer',
          whiteSpace: 'nowrap',
        }}
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  );
}
