import {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {EvidenceError, getEvidence, type Citation, type EvidenceBundle, type ResearchRun, type ResearchSourceCatalog} from '@issuedigest/api-client';
import {SavedEvidence} from './evidence/reader';
import {sourceKind} from './evidence/presentation';

type Source = ResearchSourceCatalog['items'][number];
type Loaded = {snapshotId:string; data:EvidenceBundle; title:string};
type Reader = Loaded & {identity:string; citationId:string; origin:HTMLElement | null};
type Preview = {identity:string; items:Loaded[]; failures:number; denied:boolean};
const idle = (identity:string):Preview => ({identity, items:[], failures:0, denied:false});
const titleFor = (data:EvidenceBundle, snapshotId:string, sources:Source[]) => sources.find(source=>source.snapshot_id===snapshotId && source.document_id===data.document.document_id)?.title ?? `${sourceKind(data.document.source_kind)} 원문`;

function selectorKey(selector:Citation['selector']) {
  if(selector.kind==='table_cell')return JSON.stringify([selector.kind,selector.table_id,selector.cell_id,selector.quote]);
  const position=[selector.kind,selector.start,selector.end,selector.quote,selector.prefix,selector.suffix];
  return JSON.stringify(selector.kind==='pdf'?[...position,selector.page_number,selector.regions.map(box=>[box.x0,box.y0,box.x1,box.y1])]:position);
}

/** Current-run originals are separate from model output; polling never replaces a mounted reader. */
export function useResearchEvidence(workspaceId:string, run:ResearchRun|null, sources:Source[], hidden = false) {
  const identity=`${workspaceId}/${run?.run_id??'new'}`;
  const snapshots=run?.snapshot_ids.slice(0,3).join(',')??'';
  const [preview,setPreview]=useState<Preview>(()=>idle(identity));
  const [reader,setReader]=useState<Reader|null>(null);
  const [lookup,setLookup]=useState<{identity:string; kind:'loading'|'failure'}|null>(null);
  const pending=useRef<AbortController|null>(null);
  const previewController=useRef<AbortController|null>(null);
  const sourcesRef=useRef(sources);sourcesRef.current=sources;
  const identityRef=useRef(identity);identityRef.current=identity;
  const deniedRef=useRef<string|null>(null);
  function deny() {
    deniedRef.current=identity;
    previewController.current?.abort();pending.current?.abort();setReader(null);setLookup(null);setPreview({...idle(identity),denied:true});
  }
  useEffect(()=>{
    const controller=new AbortController();previewController.current=controller;
    setPreview(idle(identity));setReader(null);setLookup(null);deniedRef.current=null;
    if(hidden) {setPreview({...idle(identity),denied:true});return()=>controller.abort();}
    if(snapshots) for(const snapshotId of snapshots.split(',')) {
      void getEvidence(workspaceId,snapshotId,{signal:controller.signal}).then(({data})=>{
        if(controller.signal.aborted || deniedRef.current===identity) return;
        const source=sourcesRef.current.find(source=>source.snapshot_id===snapshotId);
        if(source && source.document_id!==data.document.document_id) {setPreview(state=>({...state,failures:state.failures+1}));return;}
        setPreview(state=>state.identity===identity?{...state,items:[...state.items,{snapshotId,data,title:titleFor(data,snapshotId,sourcesRef.current)}]}:state);
      },error=>{
        if(controller.signal.aborted || deniedRef.current===identity)return;
        if(error instanceof EvidenceError && error.kind==='authentication') {
          controller.abort();deniedRef.current=identity;pending.current?.abort();setReader(null);setLookup(null);setPreview({...idle(identity),denied:true});
        } else setPreview(state=>state.identity===identity?{...state,failures:state.failures+1}:state);
      });
    }
    return()=>{controller.abort();pending.current?.abort();};
  },[identity,workspaceId,snapshots,hidden]);
  function show(item:Loaded,citationId:string,origin:HTMLElement|null) {
    setReader({...item,identity,citationId,origin});setLookup(null);
  }
  async function openCitation(citationId:string) {
    if(!run?.result || hidden || deniedRef.current===identity)return;
    const proof=run.result.canvas.research.evidence.find(item=>item.citations.some(citation=>citation.citation_id===citationId));
    const canonical=proof?.citations.find(citation=>citation.citation_id===citationId);
    if(!proof || !canonical)return;
    const origin=document.activeElement instanceof HTMLElement?document.activeElement:null;
    pending.current?.abort();const controller=new AbortController();pending.current=controller;
    setLookup({identity,kind:'loading'});
    const candidates=[...new Set([...run.snapshot_ids,...sources.filter(source=>source.document_id===proof.document.document_id).map(source=>source.snapshot_id)])];
    for(const snapshotId of candidates) {
      try {
        const {data}=await getEvidence(workspaceId,snapshotId,{signal:controller.signal});
        if(controller.signal.aborted || identityRef.current!==identity)return;
        const citation=data.citations.find(item=>item.citation_id===citationId);
        if(data.document.document_id!==proof.document.document_id || data.version.version_id!==proof.version.version_id || !citation || citation.representation_id!==canonical.representation_id || selectorKey(citation.selector)!==selectorKey(canonical.selector))continue;
        show({snapshotId,data,title:titleFor(data,snapshotId,sources)},citationId,origin);return;
      } catch(error) {
        if(controller.signal.aborted || identityRef.current!==identity)return;
        if(error instanceof EvidenceError && error.kind==='authentication'){deny();return;}
      }
    }
    if(!controller.signal.aborted)setLookup({identity,kind:'failure'});
  }
  const visible=!hidden && preview.identity===identity?preview:null;
  const currentReader=!hidden && reader?.identity===identity?reader:null;
  return {
    openCitation,
    preview:run && visible && <section className="research-preview" aria-label="선택한 원문에서 먼저 읽기">
      <h3>선택한 원문에서 먼저 읽기</h3><p className="research-help">이번 조사에 선택한 저장 원문의 인용입니다. AI 해석과 별도로 읽을 수 있습니다.</p>
      {visible.denied?<p role="status">원문 접근 권한을 다시 확인해 주세요.</p>:<>
        {visible.items.length===0 && visible.failures===0 && <p role="status">선택한 원문을 읽는 중…</p>}
        {visible.items.map(item=>{
          const citation=item.data.citations[0];const points=Array.from(citation?.selector.quote??'');const shortened=points.length>420;
          return <article key={item.snapshotId}><h4>{item.title}</h4><p className="research-source-meta">{sourceKind(item.data.document.source_kind)} · {item.data.document.provider} · 수집 {item.data.version.collected_at.slice(0,10)}</p>
            {citation?<><blockquote>{shortened?points.slice(0,420).join(''):citation.selector.quote}</blockquote>{shortened && <p className="research-help">긴 인용의 앞 420자만 표시했습니다. 전체 인용과 위치를 열어 확인하세요.</p>}<button type="button" onClick={event=>show(item,citation.citation_id,event.currentTarget)}>전체 원문과 인용 위치 열기 · {item.title}</button></>:<p>저장된 인용이 없습니다.</p>}
          </article>;
        })}
        {visible.failures>0 && <p role="status">일부 원문을 읽지 못했습니다. AI 조사 상태와 별개입니다.</p>}
      </>}
    </section>,
    drawer:<>
      {!hidden && lookup?.identity===identity && <p role={lookup.kind==='failure'?'alert':'status'} className="research-feedback">{lookup.kind==='loading'?'인용의 저장 원문을 여는 중…':'인용의 저장 원문을 열 수 없습니다. 자료를 다시 확인해 주세요.'}</p>}
      {currentReader && <EvidenceDrawer key={`${identity}/${currentReader.snapshotId}/${currentReader.citationId}`} reader={currentReader} workspaceId={workspaceId} onClose={()=>setReader(null)}/>}
    </>,
  };
}
function EvidenceDrawer({reader,workspaceId,onClose}:{reader:Reader;workspaceId:string;onClose:()=>void}) {
  const modal=useRef<HTMLDialogElement>(null);
  const searchState=useRef({kind:'research-citation',citationId:reader.citationId});
  useLayoutEffect(()=>{
    const element=modal.current; element?.showModal();
    return()=>{element?.close();if(reader.origin?.isConnected)reader.origin.focus({preventScroll:true});};
  },[reader.origin]);
  return <dialog ref={modal} className="research-evidence-drawer" aria-label="원문과 인용 읽기" onCancel={event=>{event.preventDefault();onClose();}} onClose={onClose}>
    <div className="research-drawer-heading"><span>선택한 근거</span><button type="button" onClick={onClose} autoFocus>닫기</button></div>
    <div className="research-drawer-body"><SavedEvidence data={reader.data} workspaceId={workspaceId} snapshotId={reader.snapshotId} title={reader.title} searchState={searchState.current}/></div>
  </dialog>;
}
