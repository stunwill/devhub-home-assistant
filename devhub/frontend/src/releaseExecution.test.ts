import {describe,expect,it} from 'vitest';
import {meaningfulPortfolioState,releaseStatusClass} from './releaseExecution';

describe('Release Execution presentation',()=>{
  it('maps lifecycle states without treating unknown work as success',()=>{
    expect(releaseStatusClass('Complete')).toBe('good');
    expect(releaseStatusClass('Passing')).toBe('good');
    expect(releaseStatusClass('Ready')).toBe('good');
    expect(releaseStatusClass('Failing')).toBe('bad');
    expect(releaseStatusClass('Attention required')).toBe('bad');
    expect(releaseStatusClass('In progress')).toBe('working');
    expect(releaseStatusClass('Waiting')).toBe('waiting');
    expect(releaseStatusClass('Unknown')).toBe('waiting');
  });

  it('only promotes actionable execution states onto compact Portfolio cards',()=>{
    expect(meaningfulPortfolioState('PR Open')).toBe(true);
    expect(meaningfulPortfolioState('CI Running')).toBe(true);
    expect(meaningfulPortfolioState('Ready to Merge')).toBe(true);
    expect(meaningfulPortfolioState('Merged')).toBe(true);
    expect(meaningfulPortfolioState('Attention required')).toBe(true);
    expect(meaningfulPortfolioState('Planning')).toBe(false);
    expect(meaningfulPortfolioState('Ready for Development')).toBe(false);
  });
});
