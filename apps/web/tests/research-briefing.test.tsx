import {act, render, screen, waitFor, within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {createMemoryRouter, RouterProvider} from 'react-router';
import {expect, it, vi} from 'vitest';
import Home from '../app/routes/home';
import {completedRun, queuedRun, runId, session, source, secondSource} from './research-data';
import {response, snapshot, workspace} from './workspace-data';

function start(run = false) {
 const router = createMemoryRouter([{path:'/', Component:Home}], {initialEntries:[run ? `/?view=research&run=${runId}` : '/?view=research']});
 render(<RouterProvider router={router}/>); return router;
}
it('suggests only matching catalog sources, keeps the question and POSTs zero for unrelated questions', async () => {
 const posts: Record<string, unknown>[]=[];
 vi.stubGlobal('fetch', async(path:string, options:RequestInit={})=> {
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source,secondSource]});
  if(options.method==='POST'){posts.push(JSON.parse(options.body as string));return response({},429);}
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  throw Error(path);
 });
 start(); const user=userEvent.setup();
 await screen.findByText(source.title);
 await user.type(screen.getByLabelText('무엇을 알아볼까요?'),'우주 탐사 현황');
 await user.click(screen.getByRole('button',{name:'AI 조사 시작'}));
 expect(posts).toHaveLength(0);expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('우주 탐사 현황');
 expect(screen.getByRole('alert')).toHaveTextContent('자료를 선택');
 await user.clear(screen.getByLabelText('무엇을 알아볼까요?'));
 await user.type(screen.getByLabelText('무엇을 알아볼까요?'),'2201234 제안 이유');
 expect(screen.getByLabelText('질문과 겹치는 연결 자료 후보')).toHaveTextContent(source.title);
 await user.click(screen.getByRole('button',{name:'AI 조사 시작'}));
 await waitFor(()=>expect(posts).toHaveLength(1));expect(posts[0].snapshot_ids).toEqual([snapshot]);
});
it.each(['failed','cancelled'] as const)('shows current exact raw citations before AI results and keeps them after %s',async(status)=> {
 let resolveRun!:(value:Response)=>void; const methods:string[]=[];
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  methods.push(options.method??'GET');
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return new Promise<Response>(resolve=>{resolveRun=resolve;});
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);
  throw Error(path);
 });
 const router=start();
 // Accept a queued run through GET and keep its following poll pending.
 let count=0; const original=globalThis.fetch;
 vi.stubGlobal('fetch',async(path:string,options?:RequestInit)=>path.endsWith(`/research/${runId}`)&&count++===0?response(queuedRun({request_id:completedRun().request_id,question:'법안 질문',snapshot_ids:[snapshot],parent_run_id:null})):original(path,options));
 await act(async()=>{await router.navigate(`/?view=research&run=${runId}`);});
 const preview=await screen.findByRole('region',{name:'선택한 원문에서 먼저 읽기'});
 await waitFor(()=>expect(within(preview).getByRole('blockquote')).toHaveTextContent('합성 테스트 전용'));
 expect(screen.queryByText('합성 근거에 맞춘 AI 해석')).not.toBeInTheDocument();
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1650));});
 await act(async()=>resolveRun(response({...queuedRun({request_id:completedRun().request_id,question:'법안 질문',snapshot_ids:[snapshot],parent_run_id:null}),status,error_code:status==='failed'?'generation_failed':'cancelled',events:[{sequence:1,status:'queued',created_at:completedRun().created_at},{sequence:2,status,created_at:completedRun().created_at}]})));
 expect(within(preview).getByRole('blockquote')).toHaveTextContent('합성 테스트 전용');
 expect(methods.every(method=>method==='GET')).toBe(true);
});
it('opens the exact citation in a stable native drawer, closes on Escape and restores focus',async()=>{
 Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.open=true;}});
 Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.open=false;}});
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[completedRun()]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);
  throw Error(path);
 });
 const router=start(true);const user=userEvent.setup();
 const trigger=(await screen.findAllByRole('button',{name:/근거 열기: 공공기록법/}))[0];await user.click(trigger);
 const drawer=await screen.findByRole('dialog',{name:'원문과 인용 읽기'});
 expect(within(drawer).getByRole('heading',{name:source.title})).toBeInTheDocument();
 expect(drawer.querySelector('mark')).toHaveTextContent('합성 테스트 전용');
 expect(router.state.location.pathname).toBe('/');
 // Native Escape emits cancel; jsdom has no native modal keyboard implementation.
 await act(async()=>{drawer.dispatchEvent(new Event('cancel',{cancelable:true}));});
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(trigger).toHaveFocus();
});

it('honors explicit source choices even when the question matches a different catalog item',async()=>{
 const posts:Record<string,unknown>[]=[];
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source,secondSource]});
  if(options.method==='POST'){posts.push(JSON.parse(options.body as string));return response({},429);}
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});throw Error(path);
 });
 start();const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'조사할 자료 선택'}));
 await user.click(await screen.findByRole('checkbox',{name:secondSource.title}));
 await user.type(screen.getByLabelText('무엇을 알아볼까요?'),'2201234 제안 이유');
 await user.click(screen.getByRole('button',{name:'AI 조사 시작'}));
 await waitFor(()=>expect(posts).toHaveLength(1));expect(posts[0].snapshot_ids).toEqual([secondSource.snapshot_id]);
});

it.each([401,403])('clears already readable originals and ignores pending responses on HTTP %s',async(status)=>{
 let release!:(value:Response)=>void;
 const queued=queuedRun({request_id:completedRun().request_id,question:'법안 질문',snapshot_ids:[snapshot,secondSource.snapshot_id],parent_run_id:null});
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source,secondSource]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(queued);
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);
  if(path.endsWith(`/evidence/${secondSource.snapshot_id}`))return new Promise<Response>(resolve=>{release=resolve;});
  throw Error(path);
 });
 start(true);const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:/전체 원문과 인용 위치 열기/}));
 expect(await screen.findByRole('dialog')).toBeInTheDocument();
 await act(async()=>release(response({},status)));
 await waitFor(()=>expect(screen.queryByRole('blockquote')).not.toBeInTheDocument());
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 expect(screen.getByText('원문 접근 권한을 다시 확인해 주세요.')).toBeInTheDocument();
 expect(screen.getByRole('status',{name:'조사 상태'})).toHaveTextContent('요청 접수');
});

it('keeps the same selected source drawer through a poll and closes it when the run changes',async()=>{
 let reads=0;
 const queued=queuedRun({request_id:completedRun().request_id,question:'법안 질문',snapshot_ids:[snapshot],parent_run_id:null});
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(reads++===0?queued:completedRun());
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);
  throw Error(path);
 });
 const router=start(true);const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:/전체 원문과 인용 위치 열기/}));
 const drawer=await screen.findByRole('dialog');
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1650));});
 expect(screen.getByRole('dialog')).toBe(drawer);expect(drawer.querySelector('mark')).toHaveTextContent('합성 테스트 전용');
 expect(reads).toBe(2);
 await act(async()=>{await router.navigate('/?view=research');});
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(screen.queryByRole('blockquote')).not.toBeInTheDocument();
});

it('aborts citation lookup on run navigation so a late exact original cannot reopen the drawer',async()=>{
 let requests=0;let release!:(value:Response)=>void;let lookupSignal:AbortSignal|null|undefined;
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`)) {
   if(requests++===0)return response(completedRun().result!.canvas.research.evidence[0]);
   lookupSignal=options.signal;return new Promise<Response>(resolve=>{release=resolve;});
  }
  throw Error(path);
 });
 const router=start(true);const user=userEvent.setup();
 await screen.findByRole('blockquote');
 await user.click((await screen.findAllByRole('button',{name:/근거 열기: 공공기록법/}))[0]);
 await waitFor(()=>expect(release).toBeTypeOf('function'));
 await act(async()=>{await router.navigate('/?view=research');});
 expect(lookupSignal?.aborted).toBe(true);
 await act(async()=>release(response(completedRun().result!.canvas.research.evidence[0])));
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(screen.queryByRole('blockquote')).not.toBeInTheDocument();
});

it.each([401,403])('aborts a pending original on polling HTTP %s and retries originals only after rechecking the run',async(status)=>{
 const queued=queuedRun({request_id:completedRun().request_id,question:'법안 질문',snapshot_ids:[snapshot],parent_run_id:null});
 let runReads=0;let originalReads=0;let originalSignal:AbortSignal|null|undefined;let release!:(value:Response)=>void;
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return runReads++===1?response({},status):response(queued);
  if(path.endsWith(`/evidence/${snapshot}`)){
   if(originalReads++>0)return response(completedRun().result!.canvas.research.evidence[0]);
   originalSignal=options.signal;return new Promise<Response>(resolve=>{release=resolve;});
  }
  throw Error(path);
 });
 start(true);const user=userEvent.setup();await waitFor(()=>expect(originalReads).toBe(1));
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1650));});
 expect(screen.getByRole('alert')).toHaveTextContent(status===401?'로그인이 필요합니다':'이 작업을 할 권한이 없습니다');
 expect(originalSignal?.aborted).toBe(true);
 await act(async()=>release(response(completedRun().result!.canvas.research.evidence[0])));
 expect(screen.queryByRole('blockquote')).not.toBeInTheDocument();
 await user.click(screen.getByRole('button',{name:'조사 다시 읽기'}));
 await screen.findByRole('blockquote');expect(originalReads).toBe(2);
});

it('rejects a citation whose IDs match but canonical quote differs from the completed result',async()=>{
 let reads=0;
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`)){
   const data=completedRun().result!.canvas.research.evidence[0];
   if(reads++>0){data.representation.text=data.representation.text.replaceAll('합성','변경');data.citations[0].selector.quote=data.citations[0].selector.quote.replaceAll('합성','변경');}
   return response(data);
  }
  throw Error(path);
 });
 start(true);const user=userEvent.setup();await screen.findByRole('blockquote');
 await user.click((await screen.findAllByRole('button',{name:/근거 열기: 공공기록법/}))[0]);
 expect(await screen.findByRole('alert')).toHaveTextContent('인용의 저장 원문을 열 수 없습니다');
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

it('bounds long exact quotes by Unicode code points and makes the omission explicit',async()=>{
 const queued=queuedRun({request_id:completedRun().request_id,question:'법안 질문',snapshot_ids:[snapshot],parent_run_id:null});
 const data=completedRun().result!.canvas.research.evidence[0];
 const quote='원문🙂'.repeat(200);data.representation.text=quote;
 data.citations[0].selector={kind:'text',start:0,end:Array.from(quote).length,quote,prefix:null,suffix:null};
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(queued);
  if(path.endsWith(`/evidence/${snapshot}`))return response(data);throw Error(path);
 });
 start(true);
 const raw=await screen.findByRole('blockquote');expect(Array.from(raw.textContent??'')).toHaveLength(420);
 expect(raw.textContent).toBe(Array.from(quote).slice(0,420).join(''));
 expect(screen.getByText(/앞 420자만 표시/)).toBeInTheDocument();
});

it('clears readable originals when a cancellation POST discovers revoked authority',async()=>{
 const queued=queuedRun({request_id:completedRun().request_id,question:'법안 질문',snapshot_ids:[snapshot],parent_run_id:null});
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(queued);
  if(path.endsWith('/cancel')&&options.method==='POST')return response({},403);
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);throw Error(path);
 });
 start(true);const user=userEvent.setup();await screen.findByRole('blockquote');
 await user.click(screen.getByRole('button',{name:'조사 취소'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('이 작업을 할 권한이 없습니다');
 expect(screen.queryByRole('blockquote')).not.toBeInTheDocument();
});

it('accepts an unchanged canonical citation regardless of JSON property order',async()=>{
 let reads=0;
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research/sources'))return response({workspace_id:workspace,items:[source]});
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`)){
   const data=completedRun().result!.canvas.research.evidence[0];
   if(reads++>0)data.citations[0].selector=Object.fromEntries(Object.entries(data.citations[0].selector).reverse()) as typeof data.citations[0]['selector'];
   return response(data);
  }
  throw Error(path);
 });
 start(true);const user=userEvent.setup();await screen.findByRole('blockquote');
 await user.click((await screen.findAllByRole('button',{name:/근거 열기: 공공기록법/}))[0]);
 expect(await screen.findByRole('dialog')).toBeInTheDocument();
});
