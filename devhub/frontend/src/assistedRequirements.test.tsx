import '@testing-library/jest-dom/vitest';
import React from 'react';
import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {AssistedFeedbackModal} from './assistedRequirements';

const projects=[{id:1,name:'DevHub'}];

afterEach(()=>vi.restoreAllMocks());

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

 it('shows a structured AI draft and does not create until explicitly confirmed',async()=>{
  const fetchMock=vi.fn(async(url:RequestInfo|URL,opts?:RequestInit)=>{
   const path=String(url);
   if(path.includes('/status'))return {ok:true,text:async()=>JSON.stringify({enabled:true,configured:true,provider:'openai',model:'test'})};
   if(path.includes('/roadmap/intelligence'))return {ok:true,text:async()=>JSON.stringify({phases:[{id:5,version:'v0.5.x',title:'Assisted Requirements',ignored:false}]})};
   if(path.includes('/assisted-requirements/analyse'))return {ok:true,text:async()=>JSON.stringify({title:'Fix mobile overflow',item_type:'Defect',description:'Mobile page exceeds viewport',actual_behaviour:'Page scrolls sideways',expected_behaviour:'No horizontal scroll',priority:'High',acceptance_criteria:['No horizontal scrolling at 390 px'],testing_instructions:'Test through ingress at 390 px',suggested_roadmap_phase_id:5,duplicate_candidates:[{id:9,item_key:'DH-DEF-0009',title:'Existing overflow',item_type:'Defect',status:'New',priority:'High',score:.5}],related_candidates:[],warnings:[]})};
   if(path==='/api/register'&&opts?.method==='POST')return {ok:true,text:async()=>JSON.stringify({id:22})};
   return {ok:true,text:async()=>JSON.stringify({})};
  });
  vi.stubGlobal('fetch',fetchMock);
  const saved=vi.fn();
  render(<AssistedFeedbackModal projects={projects} close={()=>{}} saved={saved}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Analyse & Draft Requirement'})).not.toBeDisabled());
  fireEvent.change(screen.getByPlaceholderText(/Describe what happened/),{target:{value:'The mobile page scrolls sideways'}});
  fireEvent.click(screen.getByRole('button',{name:'Analyse & Draft Requirement'}));
  await screen.findByDisplayValue('Fix mobile overflow');
  expect(screen.getByText('Possible duplicate')).toBeInTheDocument();
  expect(saved).not.toHaveBeenCalled();
  fireEvent.change(screen.getByDisplayValue('Fix mobile overflow'),{target:{value:'Edited mobile overflow'}});
  fireEvent.click(screen.getByRole('button',{name:'Create Register Item'}));
  await waitFor(()=>expect(saved).toHaveBeenCalledTimes(1));
  const registerCall=fetchMock.mock.calls.find(call=>String(call[0])==='/api/register'&&(call[1] as RequestInit)?.method==='POST');
  expect(registerCall).toBeTruthy();
  expect(String((registerCall?.[1] as RequestInit).body)).toContain('Edited mobile overflow');
 });

 it('keeps feedback after an analysis failure',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(url:RequestInfo|URL)=>{
   const path=String(url);
   if(path.includes('/status'))return {ok:true,text:async()=>JSON.stringify({enabled:true,configured:true,provider:'openai',model:'test'})};
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
