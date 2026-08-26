import '@testing-library/jest-dom/vitest';
import React from 'react';
import {render, screen} from '@testing-library/react';
import {describe, it, expect, vi} from 'vitest';

globalThis.fetch = vi.fn(async (url: RequestInfo | URL) => ({
  ok: true,
  text: async () =>
    JSON.stringify(
      String(url).includes('/api/projects')
        ? []
        : String(url).includes('/api/register')
          ? []
          : String(url).includes('/api/releases')
            ? []
            : {},
    ),
})) as unknown as typeof fetch;

vi.mock('./main.tsx', () => ({}));

describe('DevHub frontend contract', () => {
  it('keeps key product wording available to the UI source', async () => {
    const source = await import('./uiContract');
    render(<div>{source.navigation.join(' ')} {source.feedbackLabel}</div>);
    expect(screen.getByText(/Portfolio/)).toBeInTheDocument();
    expect(screen.getByText(/Feedback/)).toBeInTheDocument();
  });
});
