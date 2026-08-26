import '@testing-library/jest-dom';
import React from 'react';
import {render,screen} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';

global.fetch=vi.fn(async(url:any)=>({ok:true,text:async()=>JSON.stringify(String(url).includes('/api/projects')?[]:String(url).includes('/api/register')?[]:String(url).includes('/api/releases')?[]:{})})) as any;

vi.mock('./main.tsx',()=>({}));

describe('DevHub frontend contract',()=>{
  it('keeps key product wording available to the UI source',async()=>{
    const source=await import('./uiContract');
    render(<div>{source.navigation.join(' ')} {source.feedbackLabel}</div>);
    expect(screen.getByText(/Portfolio/)).toBeInTheDocument();
    expect(screen.getByText(/Feedback/)).toBeInTheDocument();
  });
});
