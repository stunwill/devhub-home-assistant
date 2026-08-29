import '@testing-library/jest-dom/vitest';
import React from 'react';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {AssistedFeedbackModal} from './assistedRequirements';

const projects=[{id:1,name:'DevHub'}];

afterEach(()=>{
 cleanup();
 vi.restoreAllMocks();
 vi.unstubAllGlobals();
});

const status={enabled:true,configured:true,provider:'openai',model:'test',capabilities:{text:true,images:true,multiple_images:true,direct_video:false,video_frames:true,structured_output:true}};

describe('AssistedFeedbackModal',()=>{
 it('keeps the non-AI path available when AI is not configured',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(url:RequestInfo|URL)=>({ok:true,text:async()=>JSON.stringify(String(url).includes('/status')?{enabled:false,configured:false,provider:'openai'}:{phases:[]})})));
  render(<AssistedFeedbackModal projects={projects} close={()=>{}} saved={()=>{}}/>);
  await screen.findByText(/AI assistance is not configured/);
  fireEvent.change(screen.getByPlaceholderText(/Describe what happened/),{target:{value:'The mobile page scrolls sideways'}});
  fireEvent.click(screen.getByRole('button',{name:'Continue without AI'}));
  expect(screen.getByText('Suggested requirement')).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Create Register Item'})).toBeInTheDocument();
 });

 it('shows evidence analysis separately and does not create until explicitly confirmed',async()=>{
  const fetchMock=vi.fn(async(url:RequestInfo|URL,opts?:RequestInit)=>{
   const path=String(url);
   if(path.includes('/status'))return {ok:true,text:async()=>JSON.stringify(status)};
   if(path.includes('/roadmap/intelligence'))return {ok:true,text:async()=>JSON.stringify({phases:[{id:5,version:'v0.5.x',title:'Assisted Requirements',ignored:false}]})};
   if(path.includes('/assisted-requirements/analyse'))return {ok:true,text:async()=>JSON.stringify({title:'Fix mobile overflow',item_type:'Defect',description:'Mobile page exceeds viewport',actual_behaviour:'Page scrolls sideways',expected_behaviour:'No horizontal scroll',priority:'High',acceptance_criteria:['No horizontal scrolling at 390 px'],testing_instructions:'Test through ingress at 390 px',suggested_roadmap_phase_id:5,evidence:{summary:'The recording shows horizontal page overflow.',analysed_sources:['screen-recording.mp4'],observations:[{source:'screen-recording.mp4',timestamp:'00:04',observation:'Content extends past the right edge.',confidence:'High',evidence_type:'direct'}],warnings:['Root cause cannot be determined from the recording alone.']},duplicate_candidates:[{id:9,item_key:'DH-DEF-0009',title:'Existing overflow',item_type:'Defect',status:'New',priority:'High',score:.5,match_reason:'similar title and similar actual behaviour'}],related_candidates:[],warnings:[]})};
   if(path==='/api/register'&&opts?.method==='POST')return {ok:true,text:async()=>JSON.stringify({id:22})};
   if(path.includes('/attachments')&&opts?.method==='POST')return {ok:true,text:async()=>JSON.stringify([])};
   return {ok:true,text:async()=>JSON.stringify({})};
  });
  vi.stubGlobal('fetch',fetchMock);
  vi.stubGlobal('FileReader',class {result:string|ArrayBuffer|null='data:video/mp4;base64,dGVzdA==';onload:any;onerror:any;readAsDataURL(){this.onload?.()}} as any);
  const saved=vi.fn();
  render(<AssistedFeedbackModal projects={projects} close={()=>{}} saved={saved}/>);
  const feedback=screen.getByPlaceholderText(/Describe what happened/);
  fireEvent.change(feedback,{target:{value:'The mobile page scrolls sideways'}});
  const input=screen.getByLabelText('Evidence') as HTMLInputElement;
  const file=new File(['test'],'screen-recording.mp4',{type:'video/mp4'});
  fireEvent.change(input,{target:{files:[file]}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Analyse & Draft Requirement'})).not.toBeDisabled());
  fireEvent.click(screen.getByRole('button',{name:'Analyse & Draft Requirement'}));
  await screen.findByDisplayValue('Fix mobile overflow');
  expect(screen.getByText('Evidence analysis')).toBeInTheDocument();
  expect(screen.getByText(/recording shows horizontal page overflow/)).toBeInTheDocument();
  expect(screen.getByText('00:04')).toBeInTheDocument();
  expect(screen.getByText(/similar title and similar actual behaviour/)).toBeInTheDocument();
  expect(saved).not.toHaveBeenCalled();
  fireEvent.change(screen.getByDisplayValue('Fix mobile overflow'),{target:{value:'Edited mobile overflow'}});
  fireEvent.click(screen.getByRole('button',{name:'Create Register Item'}));
  await waitFor(()=>expect(saved).toHaveBeenCalledTimes(1));
  const registerCall=fetchMock.mock.calls.find(call=>String(call[0])==='/api/register'&&(call[1] as RequestInit)?.method==='POST');
  expect(registerCall).toBeTruthy();
  expect(String((registerCall?.[1] as RequestInit).body)).toContain('Edited mobile overflow');
 });

 it('shows bounded-frame video capability instead of claiming native video support',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(url:RequestInfo|URL)=>({ok:true,text:async()=>JSON.stringify(String(url).includes('/status')?status:{phases:[]})})));
  render(<AssistedFeedbackModal projects={projects} close={()=>{}} saved={()=>{}}/>);
  expect(await screen.findByText(/analysed from bounded extracted frames/i)).toBeInTheDocument();
 });

 it('keeps feedback after an analysis failure',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(url:RequestInfo|URL)=>{
   const path=String(url);
   if(path.includes('/status'))return {ok:true,text:async()=>JSON.stringify(status)};
   if(path.includes('/roadmap/intelligence'))return {ok:true,text:async()=>JSON.stringify({phases:[]})};
   if(path.includes('/analyse'))return {ok:false,text:async()=>JSON.stringify({detail:'provider offline'})};
   return {ok:true,text:async()=>JSON.stringify({})};
  }));
  render(<AssistedFeedbackModal projects={projects} close={()=>{}} saved={()=>{}}/>);
  const feedback=screen.getByPlaceholderText(/Describe what happened/);
  fireEvent.change(feedback,{target:{value:'Keep this feedback after failure'}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Analyse & Draft Requirement'})).not.toBeDisabled());
  fireEvent.click(screen.getByRole('button',{name:'Analyse & Draft Requirement'}));
  await screen.findByText(/provider offline/);
  expect(feedback).toHaveValue('Keep this feedback after failure');
 });
});
