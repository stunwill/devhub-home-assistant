import '@testing-library/jest-dom/vitest';
import React from 'react';
import {render, screen} from '@testing-library/react';
import {describe, it, expect, vi} from 'vitest';
import {relativeTime, sortPortfolioProjects} from './portfolioUtils';

globalThis.fetch = vi.fn(async (url: RequestInfo | URL) => ({
  ok: true,
  text: async () => JSON.stringify(String(url).includes('/api/projects') ? [] : String(url).includes('/api/register') ? [] : String(url).includes('/api/releases') ? [] : {}),
})) as unknown as typeof fetch;

vi.mock('./main.tsx', () => ({}));

describe('DevHub frontend contract', () => {
  it('keeps Portfolio corrections and assisted requirements wording available', async () => {
    const source = await import('./uiContract');
    render(<div>{source.navigation.join(' ')} {source.feedbackLabel} {source.portfolioLabels.join(' ')} {source.roadmapIntelligenceLabels.join(' ')} {source.reconciliationLabels.join(' ')} {source.assistedRequirementsLabels.join(' ')}</div>);
    expect(screen.getByText(/Portfolio/)).toBeInTheDocument();
    expect(screen.getByText(/Refresh all projects/)).toBeInTheDocument();
    expect(screen.getByText(/Refreshing projects/)).toBeInTheDocument();
    expect(screen.getByText(/Updated just now/)).toBeInTheDocument();
    expect(screen.getByText(/OPEN PR/)).toBeInTheDocument();
    expect(screen.getByText(/Open pull request/)).toBeInTheDocument();
    expect(screen.getByText(/Edit name/)).toBeInTheDocument();
    expect(screen.getByText(/Project logo/)).toBeInTheDocument();
    expect(screen.getByText(/Upload logo/)).toBeInTheDocument();
    expect(screen.getByText(/Remove logo/)).toBeInTheDocument();
    expect(screen.getByText(/Version evidence/)).toBeInTheDocument();
    expect(screen.getByText(/Roadmap Intelligence/)).toBeInTheDocument();
    expect(screen.getByText(/Analyse & Draft Requirement/)).toBeInTheDocument();
  });

  it('parses UTC and offset-aware timestamps without local-time drift', () => {
    const now=Date.parse('2026-08-30T00:25:30Z');
    expect(relativeTime('2026-08-30T00:25:00Z',now)).toBe('just now');
    expect(relativeTime('2026-08-30T10:23:00+10:00',now)).toBe('2 min ago');
    expect(relativeTime('2026-08-29T23:25:00Z',now)).toBe('1 hour ago');
    expect(relativeTime('2026-08-29T00:25:00Z',now)).toBe('yesterday');
  });

  it('prioritises open PR projects then oldest PR or merged activity', () => {
    const project=(id:number,name:string,cache:any)=>({id,name,github_cache_json:JSON.stringify(cache)});
    const rows=[
      project(1,'No PR recent',{open_pr_count:0,last_merged_pr:{merged_at:'2026-08-29T10:00:00Z'}}),
      project(2,'Open newer',{open_pr_count:1,open_prs:[{updated_at:'2026-08-29T09:00:00Z'}]}),
      project(3,'Open older',{open_pr_count:1,open_prs:[{updated_at:'2026-08-28T09:00:00Z'}]}),
      project(4,'No PR older',{open_pr_count:0,last_merged_pr:{merged_at:'2026-08-27T10:00:00Z'}}),
      project(5,'No history',{open_pr_count:0}),
    ];
    expect(sortPortfolioProjects(rows).map(x=>x.id)).toEqual([3,2,4,1,5]);
  });
});
