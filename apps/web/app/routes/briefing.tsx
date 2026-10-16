import {useEffect, useRef, useState, type FormEvent} from 'react';
import {Link, useNavigate, useParams} from 'react-router';
import {CanvasView} from '@issuedigest/ui';
import '@issuedigest/ui/styles.css';
import {getPublicBriefing, PublicBriefingError, type PublicBriefingDetail} from '@issuedigest/api-client';
import BrandHeader from '../brand-header';
import {EvidenceDrawer, type EvidenceReaderState} from '../research-evidence';
import {BriefingDate} from '../public-briefings';
import {writeGuestQuestionDraft} from '../guest-question';
import '../research.css';
import '../public-briefings.css';

export default function PublicBriefing() {
  const {slug='',version}=useParams();
  return <BriefingPage key={`${slug}/${version??''}`} slug={slug} version={version}/>;
}
function BriefingPage({slug,version}:{slug:string;version?:string}) {
  const navigate=useNavigate();
  const [detail,setDetail]=useState<PublicBriefingDetail|null>(null);
  const [status,setStatus]=useState<'loading'|'ready'|'missing'|'failed'>('loading');
  const [latest,setLatest]=useState<PublicBriefingDetail|null>(null);
  const [reader,setReader]=useState<EvidenceReaderState|null>(null);
  const [checking,setChecking]=useState(false);
  const [notice,setNotice]=useState('');
  const [question,setQuestion]=useState('');
  const [questionError,setQuestionError]=useState('');
  const current=useRef<PublicBriefingDetail|null>(null);
  const request=useRef<AbortController|null>(null);
  const latestRequest=useRef<AbortController|null>(null);
  const alive=useRef(false);
  const verification=useRef<AbortController|null>(null);
  const permalink=(value:PublicBriefingDetail)=>`/briefings/${value.slug}/versions/${value.version}`;
  function clearMissing() {
    current.current=null;setDetail(null);setReader(null);setLatest(null);setChecking(false);setNotice('');setStatus('missing');
  }
  function findLatest(value:PublicBriefingDetail) {
    latestRequest.current?.abort();const controller=new AbortController();latestRequest.current=controller;
    void getPublicBriefing(slug,undefined,{signal:controller.signal}).then(({data})=>{
      if(alive.current && !controller.signal.aborted && current.current?.content_sha256===value.content_sha256)setLatest(data.public_id===value.public_id && data.version>value.version?data:null);
    },()=>{if(alive.current && !controller.signal.aborted)setLatest(null);});
  }
  async function load() {
    request.current?.abort();verification.current?.abort();latestRequest.current?.abort();setReader(null);setDetail(null);current.current=null;setLatest(null);setNotice('');setStatus('loading');
    const controller=new AbortController();request.current=controller;
    try {
      const {data}=await getPublicBriefing(slug,version,{signal:controller.signal});
      if(!alive.current || controller.signal.aborted)return;
      current.current=data;setDetail(data);setQuestion(`${data.title}에 대해 더 알고 싶어요.`);setStatus('ready');
      if(version!==undefined)findLatest(data);
    } catch(error) {
      if(!alive.current || controller.signal.aborted)return;
      if(error instanceof PublicBriefingError && error.kind==='not-found')clearMissing();else setStatus('failed');
    }
  }
  async function revalidate(citationId?:string) {
    const original=current.current;if(!original)return;
    verification.current?.abort();const controller=new AbortController();verification.current=controller;
    const origin=reader?.origin ?? (document.activeElement instanceof HTMLElement?document.activeElement:null);
    setNotice('');if(citationId)setChecking(true);
    try {
      const {data}=await getPublicBriefing(slug,original.version,{signal:controller.signal});
      if(!alive.current || controller.signal.aborted || current.current!==original)return;
      if(data.public_id!==original.public_id || data.content_sha256!==original.content_sha256)throw new PublicBriefingError('malformed');
      if(citationId) {
        const proof=data.canvas.research.evidence.find(item=>item.citations.some(citation=>citation.citation_id===citationId));
        const expected=original.canvas.research.evidence.find(item=>item.document.document_id===proof?.document.document_id);
        const source=data.sources.find(item=>item.document_id===proof?.document.document_id);
        if(!proof || !source || JSON.stringify(proof)!==JSON.stringify(expected))throw new PublicBriefingError('malformed');
        setReader({identity:permalink(data),snapshotId:proof.version.version_id,data:proof,title:source.title,citationId,origin,attribution:source});
      }
      setChecking(false);findLatest(original);
    } catch(error) {
      if(!alive.current || controller.signal.aborted)return;
      setChecking(false);
      if(error instanceof PublicBriefingError && error.kind==='not-found')clearMissing();
      else {setReader(null);setNotice('현재 게시 상태를 확인하지 못했습니다. 다시 확인해 주세요.');}
    }
  }
  const revalidateRef=useRef(revalidate);revalidateRef.current=revalidate;
  useEffect(()=>{
    alive.current=true;void load();
    const refresh=()=>{void revalidateRef.current();};
    const visible=()=>{if(document.visibilityState==='visible')refresh();};
    window.addEventListener('focus',refresh);window.addEventListener('pageshow',refresh);document.addEventListener('visibilitychange',visible);
    return()=>{alive.current=false;request.current?.abort();verification.current?.abort();latestRequest.current?.abort();window.removeEventListener('focus',refresh);window.removeEventListener('pageshow',refresh);document.removeEventListener('visibilitychange',visible);};
  },[]);
  function closeReader() {verification.current?.abort();setChecking(false);setReader(null);}
  function continueQuestion(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();if(!question.trim())return;
    if(!writeGuestQuestionDraft(question)){setQuestionError('질문을 임시 보관하지 못했습니다. 이 탭의 저장 설정을 확인해 주세요.');return;}
    void navigate('/');
  }
  return <div className="workspace public-workspace"><BrandHeader caption="근거와 함께 읽는 공개 브리핑"/><main className="public-reading-main">
    <Link to="/" className="action-link">질문으로 돌아가기</Link>
    {status==='loading' && <p role="status">브리핑을 읽는 중…</p>}
    {status==='missing' && <><h1>이 브리핑은 현재 읽을 수 없습니다.</h1><p>게시가 종료되었거나 해당 버전이 없습니다.</p></>}
    {status==='failed' && <><h1>공개 브리핑</h1><p role="status">브리핑을 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.</p><button type="button" onClick={()=>void load()}>다시 읽기</button></>}
    {detail && <>
      <header className="public-briefing-heading"><p className="eyebrow">공개 브리핑</p><h1>{detail.title}</h1><p className="public-briefing-description">{detail.description}</p>
        <div className="public-dates"><span>기준 <BriefingDate value={detail.as_of} instant/></span><span>게시 <BriefingDate value={detail.published_at}/></span><span>버전 {detail.version}</span></div>
        <nav className="public-version-links" aria-label="브리핑 버전"><Link to={permalink(detail)}>이 버전 링크</Link>{latest && <Link to={permalink(latest)}>새 버전 읽기</Link>}</nav>
      </header>
      {notice && <div className="public-read-feedback"><p role="status">{notice}</p><button type="button" onClick={()=>void revalidate()}>다시 확인</button></div>}
      <CanvasView bundle={detail.canvas} sourceTitles={detail.source_titles} presentation="briefing" onAction={action=>{if(action.kind==='open_evidence')void revalidate(action.citation_id);}}/>
      {checking && <div className="public-read-feedback"><p role="status">현재 게시 상태와 인용을 확인하는 중…</p><button type="button" onClick={closeReader}>원문 열기 취소</button></div>}
      <section className="public-attributions" aria-labelledby="public-source-title"><h2 id="public-source-title">출처와 이용 조건</h2><p>AI 해석과 원문을 구분해 읽어 주세요. 인용 위치의 일치는 사실 확인을 뜻하지 않습니다.</p><ul>{detail.sources.map(source=><li key={source.document_id}><h3>{source.title}</h3><p>{source.publisher} · 발행 <BriefingDate value={source.published_on}/></p><p>{source.attribution}</p><p>공공누리 제1유형 · 출처 표시 · 사진 및 외부 저작물 제외</p></li>)}</ul></section>
      <form className="public-question guest-composer" onSubmit={continueQuestion}><label htmlFor="public-question">이 브리핑에서 이어갈 질문</label><textarea id="public-question" rows={3} maxLength={1500} value={question} onChange={event=>{setQuestion(event.target.value);setQuestionError('');}}/><div className="guest-compose-foot"><button type="submit" disabled={!question.trim()}>질문 이어가기</button></div>{questionError && <p role="alert">{questionError}</p>}</form>
    </>}
  </main>{reader && <EvidenceDrawer key={`${reader.identity}/${reader.citationId}`} onCitation={id=>void revalidate(id)} reader={reader} workspaceId={reader.data.document.workspace_id} onClose={closeReader}/>}<footer>DigestWorks <span>자료와 근거를 차분히 살펴보는 곳</span></footer></div>;
}
