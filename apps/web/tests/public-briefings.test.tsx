import {act, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {createMemoryRouter, RouterProvider} from 'react-router';
import {afterEach, expect, it, vi} from 'vitest';
import App from '../app/root';
import Home from '../app/routes/home';
import Login from '../app/routes/login';
import PublicBriefing from '../app/routes/briefing';
import first from '../../../tests/fixtures/public-briefing-v1.json';
import second from '../../../tests/fixtures/public-briefing-v2.json';
import {response, session, workspace} from './workspace-data';
const summary = () => ({slug:first.slug,public_id:first.public_id,version:first.version,title:first.title,description:first.description,as_of:first.as_of,published_at:first.published_at,content_sha256:first.content_sha256});
function mount(entry='/') {
 const router=createMemoryRouter([{path:'/',Component:App,children:[{index:true,Component:Home},{path:'login',Component:Login},{path:'briefings/:slug',Component:PublicBriefing},{path:'briefings/:slug/versions/:version',Component:PublicBriefing}]}],{initialEntries:[entry]});
 const result=render(<RouterProvider router={router}/>);return {router,...result};
}
afterEach(()=>{sessionStorage.clear();});
function api(options:{withdrawn?:boolean; latest?:boolean; offline?:boolean; member?:boolean}={}) {
 const fetch=vi.fn(async(path:string, init?:RequestInit)=>{
  void init;
  if(path.endsWith('/session'))return response(options.member?{...session(),memberships:[{workspace_id:workspace,role:'editor'}]}:{},options.member?200:401);
  if(path.endsWith('/research'))return response({workspace_id:workspace,items:[]});
  if(path==='/api/v1/briefings')return response({items:[summary()]});
  if(options.offline)throw Error('offline');
  if(path.endsWith('/versions/1'))return response(options.withdrawn?{}:first,options.withdrawn?404:200);
  if(path.endsWith('/versions/2'))return response(second);
  if(path==='/api/v1/briefings/synthetic-policy')return response(options.latest?second:first);
  return response({},404);
 });vi.stubGlobal('fetch',fetch);return fetch;
}
it('guest discovers a real publication, reads without a session, checks exact citation and returns focus',async()=>{
 const fetch=api();const {router}=mount();const user=userEvent.setup();
 await screen.findByRole('textbox',{name:'무엇이 궁금한가요?'});
 await user.click(await screen.findByRole('link',{name:first.title}));
 expect(await screen.findByRole('heading',{name:first.title})).toBeInTheDocument();
 expect(router.state.location.pathname).toBe('/briefings/synthetic-policy');
 expect(screen.getByText('2026.01.01 00:00 UTC')).toHaveAttribute('dateTime',first.as_of);
 const sessionCalls=fetch.mock.calls.filter(([path])=>path.endsWith('/session')).length;
 const trigger=(await screen.findAllByRole('button',{name:/근거 열기: 합성 정책 자료/}))[0];await user.click(trigger);
 const drawer=await screen.findByRole('dialog',{name:'원문과 인용 읽기'});
 expect(drawer.querySelector('mark')).toHaveTextContent('합성 테스트 전용');
 expect(within(drawer).getByText('합성 발행처')).toBeInTheDocument();
 expect(within(drawer).getByRole('link',{name:/원문 출처 열기/})).toHaveAttribute('href',first.sources[0].official_url);
 fireEvent(drawer,new Event('cancel',{cancelable:true}));
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(trigger).toHaveFocus();
 expect(fetch.mock.calls.filter(([path])=>path.endsWith('/session'))).toHaveLength(sessionCalls);
 expect(fetch.mock.calls.some(([path])=>path.endsWith('/versions/1'))).toBe(true);
 expect(fetch.mock.calls.every(([path])=>!path.includes('/evidence/'))).toBe(true);
});
it('keeps v1 immutable while v2 is available and links to its exact newer version',async()=>{
 api({latest:true});mount('/briefings/synthetic-policy/versions/1');
 await screen.findByRole('heading',{name:first.title});
 expect(screen.getByRole('link',{name:'이 버전 링크'})).toHaveAttribute('href','/briefings/synthetic-policy/versions/1');
 expect(await screen.findByRole('link',{name:'새 버전 읽기'})).toHaveAttribute('href','/briefings/synthetic-policy/versions/2');
 expect(screen.getByText('버전 1')).toBeInTheDocument();
});
it.each(['focus','visibility','pageshow','citation'])('withdrawal on %s clears both briefing and open original',async event=>{
 const options={withdrawn:false};api(options);mount('/briefings/synthetic-policy/versions/1');const user=userEvent.setup();
 await user.click((await screen.findAllByRole('button',{name:/근거 열기: 합성 정책 자료/}))[0]);await screen.findByRole('dialog');
 options.withdrawn=true;
 if(event==='citation'){fireEvent(screen.getByRole('dialog'),new Event('cancel',{cancelable:true}));await user.click(screen.getAllByRole('button',{name:/근거 열기: 합성 정책 자료/})[0]);}
 else if(event==='visibility')fireEvent(document,new Event('visibilitychange'));
 else fireEvent(window,new Event(event));
 await screen.findByText('이 브리핑은 현재 읽을 수 없습니다.');
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(screen.queryByRole('article',{name:'브리핑 화면'})).not.toBeInTheDocument();
});
it('temporary failure keeps its meaning separate from withdrawal and recovers on retry',async()=>{
 const options={offline:true};api(options);mount('/briefings/synthetic-policy');
 await screen.findByText('브리핑을 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.');
 options.offline=false;await userEvent.setup().click(screen.getByRole('button',{name:'다시 읽기'}));
 await screen.findByRole('heading',{name:first.title});
 options.offline=true;fireEvent(window,new Event('focus'));
 await screen.findByText('현재 게시 상태를 확인하지 못했습니다. 다시 확인해 주세요.');
 expect(screen.getByRole('heading',{name:first.title})).toBeInTheDocument();
 options.offline=false;await userEvent.setup().click(screen.getByRole('button',{name:'다시 확인'}));
 await waitFor(()=>expect(screen.queryByText('현재 게시 상태를 확인하지 못했습니다. 다시 확인해 주세요.')).not.toBeInTheDocument());
});
it('ignores an old route response after navigation and aborts its request',async()=>{
 let release!:(value:Response)=>void;let signal:AbortSignal|null|undefined;
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/versions/1')){signal=options.signal;return new Promise<Response>(resolve=>{release=resolve;});}
  return response(second);
 });const {router}=mount('/briefings/synthetic-policy/versions/1');await waitFor(()=>expect(release).toBeTypeOf('function'));
 await act(async()=>{await router.navigate('/briefings/synthetic-policy/versions/2');});
 await screen.findByText('버전 2');expect(signal?.aborted).toBe(true);
 await act(async()=>release(response(first)));expect(screen.queryByText('버전 1')).not.toBeInTheDocument();
});
it('closing an in-flight citation cannot reopen its original when the response arrives',async()=>{
 let release!:(value:Response)=>void;let reads=0;const fallback=api();
 vi.stubGlobal('fetch',async(path:string)=>path.endsWith('/versions/1') && ++reads>1 ? new Promise<Response>(resolve=>{release=resolve;}) : fallback(path));
 mount('/briefings/synthetic-policy/versions/1');await userEvent.setup().click((await screen.findAllByRole('button',{name:/근거 열기: 합성 정책 자료/}))[0]);
 await waitFor(()=>expect(release).toBeTypeOf('function'));await userEvent.setup().click(screen.getByRole('button',{name:'원문 열기 취소'}));
 await act(async()=>release(response(first)));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
it.each([false,true])('question handoff restores editable home input without a parent, URL data or automatic paid request (member %s)',async member=>{
 const fetch=api({member});const {router}=mount('/briefings/synthetic-policy');const user=userEvent.setup();await screen.findByRole('heading',{name:first.title});
 const input=screen.getByRole('textbox',{name:'이 브리핑에서 이어갈 질문'});await user.clear(input);await user.type(input,'이 정책의 적용 대상은?');await user.click(screen.getByRole('button',{name:'질문 이어가기'}));
 expect(router.state.location.pathname).toBe('/');expect(router.state.location.search).toBe('');
 const home=await screen.findByRole('textbox',{name:member?'무엇을 알아볼까요?':'무엇이 궁금한가요?'});expect(home).toHaveValue('이 정책의 적용 대상은?');
 if(!member){await user.click(screen.getByRole('button',{name:'질문하기'}));expect(router.state.location.pathname).toBe('/login');expect(screen.getByLabelText('이어갈 질문')).toHaveTextContent('이 정책의 적용 대상은?');}
 expect(fetch.mock.calls.every(([,options])=>!options || (options as RequestInit).method!=='POST')).toBe(true);
});
it('omits an empty publication list and lets a failed list retry independently of login',async()=>{
 let fail=true;vi.stubGlobal('fetch',async(path:string)=>path.endsWith('/session')?response({},401):fail?response({},503):response({items:[]}));mount();
 await userEvent.setup().click(await screen.findByRole('button',{name:'브리핑 목록 다시 읽기'}));
 fail=false;await userEvent.setup().click(screen.getByRole('button',{name:'브리핑 목록 다시 읽기'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'브리핑 목록 다시 읽기'})).not.toBeInTheDocument());expect(screen.queryByRole('heading',{name:'공개 브리핑'})).not.toBeInTheDocument();
});
it('public route renders while authentication is unavailable without ever checking a session',async()=>{
 const fetch=vi.fn(async(path:string)=>path.includes('/briefings/')?response(first):new Promise<Response>(()=>{}));vi.stubGlobal('fetch',fetch);
 mount('/briefings/synthetic-policy');await screen.findByRole('heading',{name:first.title});
 expect(fetch.mock.calls.map(([path])=>path)).toEqual(['/api/v1/briefings/synthetic-policy']);
});
it('rejects changed immutable content during citation recheck and opens only after recovery',async()=>{
 let changed=false;const fallback=api();
 vi.stubGlobal('fetch',async(path:string)=>{
  if(path.endsWith('/versions/1') && changed)return response({...first,content_sha256:'f'.repeat(64)});
  return fallback(path);
 });mount('/briefings/synthetic-policy');const user=userEvent.setup();
 const trigger=(await screen.findAllByRole('button',{name:/근거 열기: 합성 정책 자료/}))[0];changed=true;await user.click(trigger);
 await screen.findByText('현재 게시 상태를 확인하지 못했습니다. 다시 확인해 주세요.');expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 changed=false;await user.click(trigger);expect(await screen.findByRole('dialog')).toBeInTheDocument();
});
it('back navigation rechecks the fixed publication rather than reviving withdrawn content',async()=>{
 const options={withdrawn:false};api(options);const {router}=mount('/briefings/synthetic-policy/versions/1');await screen.findByText('버전 1');
 await act(async()=>{await router.navigate('/');});await screen.findByRole('textbox',{name:'무엇이 궁금한가요?'});options.withdrawn=true;
 await act(async()=>{await router.navigate(-1);});await screen.findByText('이 브리핑은 현재 읽을 수 없습니다.');
 expect(screen.queryByRole('article',{name:'브리핑 화면'})).not.toBeInTheDocument();
});
it('an old citation request cannot reopen after the route switches to a new version',async()=>{
 let resolve!:(value:Response)=>void;let fixed=0;let signal:AbortSignal|null|undefined;const fallback=api();
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(path.endsWith('/versions/1') && ++fixed>1){signal=options.signal;return new Promise<Response>(release=>{resolve=release;});}
  return fallback(path);
 });const {router}=mount('/briefings/synthetic-policy/versions/1');
 await userEvent.setup().click((await screen.findAllByRole('button',{name:/근거 열기: 합성 정책 자료/}))[0]);await waitFor(()=>expect(resolve).toBeTypeOf('function'));
 await act(async()=>{await router.navigate('/briefings/synthetic-policy/versions/2');});await screen.findByText('버전 2');expect(signal?.aborted).toBe(true);
 await act(async()=>resolve(response(first)));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(screen.queryByText('버전 1')).not.toBeInTheDocument();
});
it('never sends a public identity as a private parent when a member explicitly submits the restored question',async()=>{
 const fallback=api({member:true});const submissions:Record<string,unknown>[]=[];
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(options.method==='POST'){submissions.push(JSON.parse(options.body as string) as Record<string,unknown>);return response({},503);}
  return fallback(path);
 });const {router}=mount('/briefings/synthetic-policy');const user=userEvent.setup();await screen.findByRole('heading',{name:first.title});
 await user.click(screen.getByRole('button',{name:'질문 이어가기'}));await screen.findByRole('textbox',{name:'무엇을 알아볼까요?'});
 expect(submissions).toHaveLength(0);await user.click(screen.getByRole('button',{name:'브리핑 만들기'}));await waitFor(()=>expect(submissions).toHaveLength(1));
 expect(submissions[0]).toMatchObject({question:`${first.title}에 대해 더 알고 싶어요.`,parent_run_id:null});
 expect(Object.keys(submissions[0]).sort()).toEqual(['parent_run_id','question','request_id']);expect(router.state.location.search).not.toContain(first.title);
});
it('rechecks publication before a different exact citation in the open original is selected',async()=>{
 const options={withdrawn:false};api(options);mount('/briefings/synthetic-policy/versions/1');const user=userEvent.setup();
 const trigger=(await screen.findAllByRole('button',{name:/근거 열기: 합성 정책 자료/}))[0];await user.click(trigger);const drawer=await screen.findByRole('dialog');
 options.withdrawn=true;await user.click(within(drawer).getByRole('button',{name:/인용 2/}));
 await screen.findByText('이 브리핑은 현재 읽을 수 없습니다.');expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
it.each(['이전에 작성한 질문',''])('explicit public handoff replaces an existing member home draft %j once and preserves later edits without automatic POST',async previous=>{
 const fallback=api({member:true});const submissions:Record<string,unknown>[]=[];
 vi.stubGlobal('fetch',async(path:string,options:RequestInit={})=>{
  if(options.method==='POST'){submissions.push(JSON.parse(options.body as string) as Record<string,unknown>);return response({},503);}
  return fallback(path);
 });const {router}=mount();const user=userEvent.setup();
 const original=await screen.findByRole('textbox',{name:'무엇을 알아볼까요?'});
 await user.type(original,'이전에 작성한 질문');if(!previous)await user.clear(original);
 await user.click(await screen.findByRole('link',{name:first.title}));await screen.findByRole('heading',{name:first.title});
 const publicQuestion=screen.getByRole('textbox',{name:'이 브리핑에서 이어갈 질문'});await user.clear(publicQuestion);await user.type(publicQuestion,'새로 이어갈 공개 질문');
 await user.click(screen.getByRole('button',{name:'질문 이어가기'}));
 const restored=await screen.findByRole('textbox',{name:'무엇을 알아볼까요?'});expect(restored).toHaveValue('새로 이어갈 공개 질문');
 expect(submissions).toHaveLength(0);expect(router.state.location.search).toBe('');expect(sessionStorage.getItem('issuedigest.guest-question.v1')).toBeNull();
 await user.type(restored,'을 편집함');
 await user.click(await screen.findByRole('link',{name:first.title}));await screen.findByRole('heading',{name:first.title});
 await user.click(screen.getByRole('link',{name:'질문으로 돌아가기'}));
 expect(await screen.findByRole('textbox',{name:'무엇을 알아볼까요?'})).toHaveValue('새로 이어갈 공개 질문을 편집함');expect(submissions).toHaveLength(0);
 await user.click(screen.getByRole('button',{name:'브리핑 만들기'}));await waitFor(()=>expect(submissions).toHaveLength(1));
 expect(submissions[0]).toMatchObject({question:'새로 이어갈 공개 질문을 편집함',parent_run_id:null});
 expect(Object.keys(submissions[0]).sort()).toEqual(['parent_run_id','question','request_id']);
});
