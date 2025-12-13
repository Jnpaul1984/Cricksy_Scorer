export function highlightMitigations(html: string, agentKey: string) {
  if (agentKey !== 'cyber_security_watcher') return html;
  // Highlight 'Recommended actions' section
  return html.replace(/(## Recommended actions[\s\S]*?)(##|$)/g, (m) => `<div style="background:#ffe7c2;padding:0.5em 1em;border-radius:6px;">${m}</div>`);
}
