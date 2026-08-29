import '@testing-library/jest-dom/vitest';
import React from 'react';
import {render, screen} from '@testing-library/react';
import {describe, it, expect, vi} from 'vitest';

globalThis.fetch = vi.fn(async (url: RequestInfo | URL) => ({
  ok: true,
  text: async () => JSON.stringify(String(url).includes('/api/projects') ? [] : String(url).includes('/api/register') ? [] : String(url).includes('/api/releases') ? [] : {}),
})) as unknown as typeof fetch;

vi.mock('./main.tsx', () => ({}));

describe('DevHub frontend contract', () => {
  it('keeps compact portfolio, roadmap intelligence, reconciliation and assisted requirements wording available', async () => {
    const source = await import('./uiContract');
    render(<div>{source.navigation.join(' ')} {source.feedbackLabel} {source.portfolioLabels.join(' ')} {source.roadmapIntelligenceLabels.join(' ')} {source.reconciliationLabels.join(' ')} {source.assistedRequirementsLabels.join(' ')}</div>);
    expect(screen.getByText(/Portfolio/)).toBeInTheDocument();
    expect(screen.getByText(/Refresh all projects/)).toBeInTheDocument();
    expect(screen.getByText(/Create/)).toBeInTheDocument();
    expect(screen.getByText(/CI attention/)).toBeInTheDocument();
    expect(screen.getByText(/Release Unknown/)).toBeInTheDocument();
    expect(screen.getByText(/Roadmap Intelligence/)).toBeInTheDocument();
    expect(screen.getByText(/Raw Markdown/)).toBeInTheDocument();
    expect(screen.getByText(/Use automatic detection/)).toBeInTheDocument();
    expect(screen.getByText(/User confirmed/)).toBeInTheDocument();
    expect(screen.getByText(/Ignore in DevHub planning/)).toBeInTheDocument();
    expect(screen.getByText(/Roadmap reconciliation/)).toBeInTheDocument();
    expect(screen.getByText(/Suggested roadmap reconciliation/)).toBeInTheDocument();
    expect(screen.getByText(/GitHub synchronisation diagnostics/)).toBeInTheDocument();
    expect(screen.getByText(/GitHub rate limit/)).toBeInTheDocument();
    expect(screen.getByText(/Analyse & Draft Requirement/)).toBeInTheDocument();
    expect(screen.getByText(/Suggested requirement/)).toBeInTheDocument();
    expect(screen.getByText(/Possible duplicate/)).toBeInTheDocument();
    expect(screen.getByText(/Create Register Item/)).toBeInTheDocument();
  });
});
