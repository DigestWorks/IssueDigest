import {act, render, screen, waitFor, within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {createMemoryRouter, RouterProvider} from 'react-router';
import {expect, it, vi} from 'vitest';
import Home from '../app/routes/home';
import App, {HydrateFallback} from '../app/root';
import {completedRun, queuedRun, runId, session, source} from './research-data';
import {response, snapshot, workspace} from './workspace-data';

function start(run = false) {
 const router = createMemoryRouter([{path:'/', Component:Home}], {initialEntries:[run ? `/?view=research&run=${runId}` : '/?view=research']});
 render(<RouterProvider router={router}/>); return router;
}
it('opens the exact citation in a stable native drawer, closes on Escape and restores focus',async()=>{
 Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.open=true;}});
 Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.open=false;}});
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
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

it('aborts citation lookup on run navigation so a late exact original cannot reopen the drawer',async()=>{
 let release!:(value:Response)=>void;let lookupSignal:AbortSignal|null|undefined;
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`)) {
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

it('rejects a citation whose IDs match but canonical quote differs from the completed result',async()=>{
 let reads=0;
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`)){
   const data=completedRun().result!.canvas.research.evidence[0];
   if(reads++===0){data.representation.text=data.representation.text.replaceAll('합성','변경');data.citations[0].selector.quote=data.citations[0].selector.quote.replaceAll('합성','변경');}
   return response(data);
  }
  throw Error(path);
 });
 start(true);const user=userEvent.setup();await screen.findByText('합성 근거에 맞춘 AI 해석');
 await user.click((await screen.findAllByRole('button',{name:/근거 열기: 공공기록법/}))[0]);
 expect(await screen.findByRole('alert')).toHaveTextContent('인용의 저장 원문을 열 수 없습니다');
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

it('accepts an unchanged canonical citation regardless of JSON property order',async()=>{
 let reads=0;
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`)){
   const data=completedRun().result!.canvas.research.evidence[0];
   if(reads++===0)data.citations[0].selector=Object.fromEntries(Object.entries(data.citations[0].selector).reverse()) as typeof data.citations[0]['selector'];
   return response(data);
  }
  throw Error(path);
 });
 start(true);const user=userEvent.setup();await screen.findByText('합성 근거에 맞춘 AI 해석');
 await user.click((await screen.findAllByRole('button',{name:/근거 열기: 공공기록법/}))[0]);
 expect(await screen.findByRole('dialog')).toBeInTheDocument();
});

it.each([401,403,404])('clears a completed-run Canvas and open drawer when the saved list returns HTTP %s',async(status)=>{
 const pendingLists:((value:Response)=>void)[]=[];
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return new Promise<Response>(resolve=>{pendingLists.push(resolve);});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);
  throw Error(path);
 });
 start(true);const user=userEvent.setup();await screen.findByText('합성 근거에 맞춘 AI 해석');
 await waitFor(()=>expect(pendingLists).toHaveLength(2));
 await user.type(screen.getByLabelText('후속 질문'),'지울 후속 질문');
 await user.click(screen.getAllByRole('button',{name:/근거 열기: 공공기록법/})[0]);
 expect(await screen.findByRole('dialog')).toBeInTheDocument();
 await act(async()=>pendingLists.at(-1)!(response({},status)));
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 expect(screen.queryByText('합성 근거에 맞춘 AI 해석')).not.toBeInTheDocument();
 expect(screen.queryByText(source.title)).not.toBeInTheDocument();
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('');
});

it('retains a new question typed after leaving a failed run while its URL transition is still pending',async()=>{
 const queued=queuedRun({request_id:completedRun().request_id,question:'실패한 이전 질문',snapshot_ids:[snapshot],parent_run_id:null});
 const failed={...queued,status:'failed',error_code:'generation_failed',events:[...queued.events,{sequence:2,status:'failed',created_at:queued.created_at}]};
 const methods:string[]=[];let releaseNavigation!:(value:null)=>void;
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  methods.push(options.method??'GET');
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(failed);
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);throw Error(path);
 });
 const router=createMemoryRouter([{path:'/',Component:App,HydrateFallback,children:[{index:true,Component:Home,loader:({request})=>new URL(request.url).searchParams.has('run')?null:new Promise<null>(resolve=>{releaseNavigation=resolve;})}]}],{initialEntries:[`/?view=research&run=${runId}`]});
 render(<RouterProvider router={router}/>);const user=userEvent.setup();
 await waitFor(()=>expect(screen.getByRole('status',{name:'브리핑 상태'})).toHaveTextContent('브리핑을 완료하지 못했습니다'));
 await user.click(screen.getByRole('button',{name:'새 질문'}));
 await waitFor(()=>expect(releaseNavigation).toBeTypeOf('function'));
 await user.type(screen.getByLabelText('무엇을 알아볼까요?'),'새 질문을 유지해 주세요');
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('새 질문을 유지해 주세요');
 await act(async()=>releaseNavigation(null));
 await waitFor(()=>expect(router.state.location.search).toBe('?view=research'));
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('새 질문을 유지해 주세요');
 expect(methods.every(method=>method==='GET')).toBe(true);
});

it.each([401,403,404])('clears current question and stage on polling HTTP %s and resumes only after a fresh run check',async(status)=>{
 const queued=queuedRun({request_id:completedRun().request_id,question:'진행 중 질문',snapshot_ids:[],parent_run_id:null});
 let reads=0;
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return reads++===1?response({},status):response(queued);
  throw Error(path);
 });
 start(true);const user=userEvent.setup();
 expect(await screen.findByRole('status',{name:'브리핑 상태'})).toHaveTextContent('요청 접수');
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('진행 중 질문');
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1650));});
 expect(screen.getByRole('alert')).toHaveTextContent(status===401?'로그인이 필요합니다':status===403?'이 작업을 할 권한이 없습니다':'자료 또는 브리핑을 찾을 수 없습니다');
 expect(screen.queryByRole('status',{name:'브리핑 상태'})).not.toBeInTheDocument();
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('');
 await user.click(screen.getByRole('button',{name:'브리핑 다시 읽기'}));
 expect(await screen.findByRole('status',{name:'브리핑 상태'})).toHaveTextContent('요청 접수');
 expect(reads).toBe(3);
});

it('clears the current question and stage when a cancellation POST discovers revoked authority',async()=>{
 const queued=queuedRun({request_id:completedRun().request_id,question:'진행 중 질문',snapshot_ids:[],parent_run_id:null});
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(queued);
  if(path.endsWith('/cancel')&&options.method==='POST')return response({},403);
  throw Error(path);
 });
 start(true);const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'생성 취소'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('이 작업을 할 권한이 없습니다');
 expect(screen.queryByRole('status',{name:'브리핑 상태'})).not.toBeInTheDocument();
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('');
});

it('opens the added canonical source of a historical seed-plus-expanded-source result',async()=>{
 // Captured from the real PostgreSQL/API legacy fixture: seed A and indexed/cited B.
 const {default:fixture}=await import('./fixtures/historical-expanded-run.json');
 const historical=structuredClone(fixture);
 const [seed,added]=historical.result.canvas.research.evidence;
 const protectedGets:string[]=[];
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response({...session,memberships:[{workspace_id:historical.workspace_id,role:'owner'}]});
  if(path.endsWith('/research'))return response({workspace_id:historical.workspace_id,items:[historical]});
  if(path.endsWith(`/research/${historical.run_id}`))return response(historical);
  if(path.endsWith(`/evidence/${historical.snapshot_ids[0]}`)){protectedGets.push(path);return response(seed);}
  if(path.endsWith(`/evidence/${historical.snapshot_ids[1]}`)){protectedGets.push(path);return response(added);}
  throw Error(path);
 });
 const router=createMemoryRouter([{path:'/',Component:Home}],{initialEntries:[`/?view=research&run=${historical.run_id}`]});
 render(<RouterProvider router={router}/>);
 const user=userEvent.setup();
 const trigger=(await screen.findAllByRole('button',{name:/근거 열기: 합성 자료 1/}))[0];
 expect(protectedGets).toEqual([]);
 await user.click(trigger);
 const drawer=await screen.findByRole('dialog',{name:'원문과 인용 읽기'});
 expect(within(drawer).getByRole('heading',{name:'합성 자료 1'})).toBeInTheDocument();
 expect(drawer.querySelector('mark')).toHaveTextContent('주거지원 추가 발표');
 expect(protectedGets).toEqual(historical.snapshot_ids.map(id=>`/api/v1/workspaces/${historical.workspace_id}/evidence/${id}`));
});

it('reads the completed briefing before reaching the follow-up question in keyboard order', async () => {
 vi.stubGlobal('fetch', async (path: string) => {
  if (path.endsWith('/session')) return response(session);
  if (path.endsWith('/research')) return response({workspace_id: workspace, items: [completedRun()]});
  if (path.endsWith(`/research/${runId}`)) return response(completedRun());
  throw Error(path);
 });
 start(true);
 const briefing = await screen.findByRole('article', {name: '브리핑 화면'});
 const followup = screen.getByRole('textbox', {name: '후속 질문'});
 expect(briefing.compareDocumentPosition(followup) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 // Source actions must be encountered before a new question in the reading order.
 const sourceAction = within(briefing).getAllByRole('button', {name: /근거 열기:/})[0];
 sourceAction.focus();
 await userEvent.setup().tab();
 expect(within(briefing).getByText('근거', {selector: 'summary'})).toHaveFocus();
 expect(screen.getByRole('button', {name: '후속 질문하기'})).toBeDisabled();
});
