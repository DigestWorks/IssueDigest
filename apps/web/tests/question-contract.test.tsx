import {act, render, screen, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {createMemoryRouter, RouterProvider} from 'react-router';
import {expect, it, vi} from 'vitest';
import App from '../app/root';
import Home from '../app/routes/home';
import EvidenceRoute from '../app/routes/evidence';
import {completedRun, queuedRun, runId, session, source} from './research-data';
import {response, snapshot, workspace} from './workspace-data';

function mount(entry = '/') {
 const router = createMemoryRouter([{path:'/', Component:App, children:[{index:true, Component:Home}, {path:'workspaces/:workspaceId/evidence/:snapshotId', Component:EvidenceRoute}]}], {initialEntries:[entry]});
 render(<RouterProvider router={router}/>); return router;
}

it.each(['completed', 'no-hit'] as const)('submits only a question and reads server stages through %s', async outcome => {
 let release!:(value:Response)=>void;
 const posted:Record<string,unknown>[]=[];
 vi.stubGlobal('fetch', async(path:string, options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research') && options.method==='POST') { const input=JSON.parse(options.body as string);posted.push(input);return response(queuedRun(input)); }
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return new Promise<Response>(resolve=>{release=resolve;});
  if(path.endsWith(`/evidence/${snapshot}`))return response(completedRun().result!.canvas.research.evidence[0]);
  throw Error(path);
 });
 mount();const user=userEvent.setup();
 await user.type(await screen.findByLabelText('무엇을 알아볼까요?'),'우주 탐사 현황');
 await user.click(screen.getByRole('button',{name:'브리핑 만들기'}));
 await waitFor(()=>expect(posted).toHaveLength(1));
 expect(posted[0]).toEqual({request_id:expect.any(String), question:'우주 탐사 현황', parent_run_id:null});
 expect(await screen.findByRole('status',{name:'브리핑 상태'})).toHaveTextContent('요청 접수');
 await waitFor(()=>expect(release).toBeTypeOf('function'));
 const queued=queuedRun(posted[0]);
 await act(async()=>release(response(outcome==='completed'?{...completedRun(), request_id:queued.request_id,question:queued.question}:{...queued,status:'failed',error_code:'insufficient_evidence',events:[...queued.events,{sequence:2,status:'failed',created_at:queued.created_at}]})));
 if(outcome==='completed')expect(await screen.findByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();
 else expect(await screen.findByRole('alert')).toHaveTextContent('확인 가능한 자료가 부족합니다.');
});

it.each([401,403,404])('clears current Canvas, titles, reader and question draft on exact-original HTTP %s',async status=>{
 let deny=false;
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`))return response(deny?{}:completedRun().result!.canvas.research.evidence[0],deny?status:200);
  throw Error(path);
 });
 const router=mount(`/?run=${runId}`);const user=userEvent.setup();
 await screen.findByText('합성 근거에 맞춘 AI 해석');
 await user.type(screen.getByLabelText('후속 질문'),'보호된 질문 초안');
 deny=true;await user.click(screen.getAllByRole('button',{name:/근거 열기: 공공기록법/})[0]);
 await waitFor(()=>expect(screen.queryByText('합성 근거에 맞춘 AI 해석')).not.toBeInTheDocument());
 expect(screen.queryByText(source.title)).not.toBeInTheDocument();
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('');
 await act(async()=>router.navigate('/'));
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('');
 deny=false;await act(async()=>router.navigate(`/?run=${runId}`));
 expect(await screen.findByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();
});

it.each([503,'network'] as const)('retains current Canvas and question on transient original %s',async status=>{
 let fail=false;
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/evidence/${snapshot}`)){if(fail && status==='network')throw Error('offline');return response(fail?{}:completedRun().result!.canvas.research.evidence[0],fail?503:200);}
  throw Error(path);
 });
 mount(`/?run=${runId}`);const user=userEvent.setup();
 await screen.findByText('합성 근거에 맞춘 AI 해석');
 await user.type(screen.getByLabelText('후속 질문'),'유지할 질문');
 fail=true;await user.click(screen.getAllByRole('button',{name:/근거 열기: 공공기록법/})[0]);
 await screen.findByText('인용의 저장 원문을 열 수 없습니다. 자료를 다시 확인해 주세요.');
 expect(screen.getByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();
 expect(screen.getByLabelText('후속 질문')).toHaveValue('유지할 질문');
});

it('ignores a late previous-run original denial after navigation to a new completed briefing',async()=>{
 let release!:(value:Response)=>void;let hold=false;
 const nextId='00000000-0000-4000-8000-000000000099';const next=completedRun();next.run_id=nextId;next.result!.canvas.revision.run_id=nextId;next.question='새 질문';
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(completedRun());
  if(path.endsWith(`/research/${nextId}`))return response(next);
  if(path.endsWith(`/evidence/${snapshot}`))return hold?new Promise<Response>(resolve=>{release=resolve;}):response(completedRun().result!.canvas.research.evidence[0]);
  throw Error(path);
 });
 const router=mount(`/?run=${runId}`);const user=userEvent.setup();await screen.findByText('합성 근거에 맞춘 AI 해석');
 hold=true;await user.click(screen.getAllByRole('button',{name:/근거 열기: 공공기록법/})[0]);
 await waitFor(()=>expect(release).toBeTypeOf('function'));const oldRelease=release;hold=false;
 await act(async()=>router.navigate(`/?run=${nextId}`));await screen.findByText('질문 · 새 질문');
 await user.type(screen.getByLabelText('후속 질문'),'새 브리핑 초안');
 await act(async()=>oldRelease(response({},403)));
 expect(screen.getByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();expect(screen.getByLabelText('후속 질문')).toHaveValue('새 브리핑 초안');
});


it('clears the workspace draft after the current protected direct reader confirms no access',async()=>{
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/evidence/${snapshot}`))return response({},404);
  throw Error(path);
 });
 const router=mount();const user=userEvent.setup();
 await user.type(await screen.findByLabelText('무엇을 알아볼까요?'),'권한 상실 뒤 지울 질문');
 await act(async()=>router.navigate(`/workspaces/${workspace}/evidence/${snapshot}`));
 await screen.findByText('자료가 없거나 접근 권한이 없습니다.');
 await act(async()=>router.navigate(-1));
 expect(await screen.findByLabelText('무엇을 알아볼까요?')).toHaveValue('');
});


it('blocks duplicate submits and rechecks an ambiguous POST with the identical question and request ID',async()=>{
 const posted:Record<string,unknown>[]=[];let release!:(value:Response)=>void;
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research') && options.method==='POST') {
   posted.push(JSON.parse(options.body as string));
   return posted.length===1?new Promise<Response>(resolve=>{release=resolve;}):response(queuedRun(posted[0]));
  }
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path.endsWith(`/research/${runId}`))return response(queuedRun(posted[0]));
  throw Error(path);
 });
 mount();const user=userEvent.setup();await user.type(await screen.findByLabelText('무엇을 알아볼까요?'),'다시 확인할 질문');
 await user.dblClick(screen.getByRole('button',{name:'브리핑 만들기'}));
 expect(posted).toHaveLength(1);expect(screen.getByRole('button',{name:'요청 접수 중…'})).toBeDisabled();
 await act(async()=>release(response({},503)));
 await user.click(await screen.findByRole('button',{name:'같은 요청 다시 확인'}));
 expect(posted).toHaveLength(2);expect(posted[1]).toEqual(posted[0]);
 expect(await screen.findByRole('status',{name:'브리핑 상태'})).toHaveTextContent('요청 접수');
});

it.each([401,403,404].flatMap(status=>['owner','viewer'].map(role=>({status,role}))))('shows a standalone history denial and explicitly rechecks restored access (HTTP $status, $role)',async({status,role})=>{
 let allowed=false;let reads=0;
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/session'))return response({...session,memberships:[{workspace_id:workspace,role}]});
  if(path.endsWith('/research')){reads++;return allowed?response({workspace_id:workspace,items:[completedRun()]}):response({},status);}
  throw Error(path);
 });
 const router=mount('/?view=saved');const user=userEvent.setup();
 const message=status===401?'로그인이 필요합니다.':status===403?'이 작업을 할 권한이 없습니다.':'자료 또는 브리핑을 찾을 수 없습니다.';
 expect(await screen.findByRole('alert')).toHaveTextContent(message);
 expect(screen.queryByText('브리핑 기록이 없습니다.')).not.toBeInTheDocument();
 expect(router.state.location.search).toBe('?view=saved');
 allowed=true;await user.click(screen.getByRole('button',{name:'목록 새로고침'}));
 expect(await screen.findByRole('button',{name:/법안의 핵심은/})).toBeInTheDocument();
 expect(reads).toBe(2);expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

it('clears the question on a standalone history denial and ignores an older list after explicit recovery',async()=>{
 let reads=0;let releaseOld!:(value:Response)=>void;let oldSignal:AbortSignal|null|undefined;
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/session'))return response(session);
  if(path.endsWith('/research')){
   reads++;
   if(reads===1){oldSignal=options.signal;return new Promise<Response>(resolve=>{releaseOld=resolve;});}
   if(reads===2)return response({},403);
   return response({workspace_id:workspace,items:[completedRun()]});
  }
  throw Error(path);
 });
 const router=mount();const user=userEvent.setup();
 await user.type(await screen.findByLabelText('무엇을 알아볼까요?'),'권한 오류로 지울 질문');
 await user.click(screen.getByRole('button',{name:'브리핑 기록'}));
 await user.click(screen.getByRole('button',{name:'목록 새로고침'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('이 작업을 할 권한이 없습니다.');
 expect(oldSignal?.aborted).toBe(true);
 await user.click(screen.getByRole('button',{name:'목록 새로고침'}));
 expect(await screen.findByRole('button',{name:/법안의 핵심은/})).toBeInTheDocument();
 const old=completedRun();old.question='늦게 도착한 이전 기록';
 await act(async()=>releaseOld(response({workspace_id:workspace,items:[old]})));
 expect(screen.queryByRole('button',{name:/늦게 도착한 이전 기록/})).not.toBeInTheDocument();
 expect(screen.getByRole('button',{name:/법안의 핵심은/})).toBeInTheDocument();
 await act(async()=>router.navigate('/'));
 expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('');
});
