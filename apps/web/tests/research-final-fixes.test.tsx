import {StrictMode} from 'react';
import {act, render, screen, waitFor, within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {createMemoryRouter, RouterProvider} from 'react-router';
import {afterEach, expect, it, vi} from 'vitest';
import App from '../app/root';
import Home from '../app/routes/home';
import {completedRun, queuedRun, runId, session} from './research-data';
import {response, snapshot, workspace} from './workspace-data';

const guestKey='issuedigest.guest-question.v1';
afterEach(()=>sessionStorage.removeItem(guestKey));
function mount(entry='/?view=research') {
 const router=createMemoryRouter([{path:'/',Component:App,children:[{index:true,Component:Home}]}],{initialEntries:[entry]});
 render(<StrictMode><RouterProvider router={router}/></StrictMode>);return router;
}
it('retires the restored guest handoff after initialization so reset and navigation return stay empty',async()=>{
 sessionStorage.setItem(guestKey,JSON.stringify({version:1,question:'이미 버린 로그인 전 질문',createdAt:Date.now()}));
 const methods:string[]=[];
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  methods.push(options.method??'GET');
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);throw Error(path);
 });
 const router=mount();const user=userEvent.setup();
 expect(await screen.findByLabelText('무엇을 알아볼까요?')).toHaveValue('이미 버린 로그인 전 질문');
 expect(sessionStorage.getItem(guestKey)).toBeNull();
 await act(async()=>{await router.navigate(`/?view=research&run=${runId}`);});
 await screen.findByText('합성 근거에 맞춘 AI 해석');
 await user.click(screen.getByRole('button',{name:'새 질문'}));
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('');
 expect(await screen.findByLabelText('무엇을 알아볼까요?')).toHaveValue('');
 expect(await screen.findByLabelText('무엇을 알아볼까요?')).toHaveValue('');
 expect(methods.every(method=>method==='GET')).toBe(true);
});

it.each([false,true])('an existing citation reader stays open or closed after an older lookup resolves (dismiss=%s)',async(dismiss)=>{
 let hold=false;let release!:(value:Response)=>void;let signal:AbortSignal|null|undefined;
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`)){
   if(!hold)return response(completedRun().result!.canvas.research.evidence[0]);
   signal=options.signal;return new Promise<Response>(resolve=>{release=resolve;});
  }
  throw Error(path);
 });
 mount(`/?view=research&run=${runId}`);const user=userEvent.setup();
 const triggers=await screen.findAllByRole('button',{name:/근거 열기: 공공기록법/});
 await user.click(triggers[0]);const drawer=await screen.findByRole('dialog');
 hold=true;await user.click(triggers[1]);await waitFor(()=>expect(release).toBeTypeOf('function'));
 if(dismiss)await user.click(within(drawer).getByRole('button',{name:'닫기'}));
 await act(async()=>release(response(completedRun().result!.canvas.research.evidence[0])));
 if(dismiss){expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(signal?.aborted).toBe(true);}
 else expect(screen.getByRole('dialog')).toBeInTheDocument();
});

it.each([403,404,503])('shows selected saved-run loading, HTTP %s failure and GET-only retry',async(status)=>{
 let release!:(value:Response)=>void;let reads=0;const methods:string[]=[];
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  methods.push(options.method??'GET');
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[completedRun()]});
  if(path.endsWith(`/research/${runId}`))return reads++===0?new Promise<Response>(resolve=>{release=resolve;}):response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);throw Error(path);
 });
 mount('/?view=saved');const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:/법안의 핵심은/}));
 expect(screen.getByText('브리핑을 다시 여는 중…')).toHaveAttribute('role','status');
 await act(async()=>release(response({},status)));
 const message=status===403?'이 작업을 할 권한이 없습니다':status===404?'자료 또는 브리핑을 찾을 수 없습니다':'AI 연결을 기다리는 중';
 expect(screen.getByRole('alert')).toHaveTextContent(message);
 await user.click(screen.getByRole('button',{name:'브리핑 다시 읽기'}));
 expect(await screen.findByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();expect(reads).toBe(2);
 expect(methods.every(method=>method==='GET')).toBe(true);
});
it.each(['failed','cancelled'] as const)('shows the actual %s status for a selected saved investigation',async(status)=>{
 const queued=queuedRun({request_id:completedRun().request_id,question:'완료하지 못한 저장 질문',snapshot_ids:[snapshot],parent_run_id:null});
 const run={...queued,status,error_code:status==='failed'?'generation_failed':'cancelled',events:[...queued.events,{sequence:2,status,created_at:queued.created_at}]};
 const methods:string[]=[];
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  methods.push(options.method??'GET');
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[run]});
  if(path.endsWith(`/research/${runId}`))return response(run);
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);throw Error(path);
 });
 mount('/?view=saved');const user=userEvent.setup();
 await user.click(await screen.findByRole('button',{name:/완료하지 못한 저장 질문/}));
 expect(await screen.findByRole('alert')).toHaveTextContent(status==='failed'?'결과를 생성하지 못했습니다':'생성이 취소되었습니다');
 expect(methods.every(method=>method==='GET')).toBe(true);
});
