import {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {EvidenceError, getEvidence, type Citation, type EvidenceBundle, type ResearchRun, type PublicSourceAttribution} from '@issuedigest/api-client';
import {SavedEvidence} from './evidence/reader';
import {sourceKind} from './evidence/presentation';

type Loaded = {snapshotId:string; data:EvidenceBundle; title:string};
export type EvidenceReaderState = Loaded & {identity:string; citationId:string; origin:HTMLElement | null; attribution?:PublicSourceAttribution};
type Reader = EvidenceReaderState;
const titleFor = (data:EvidenceBundle, titles:Record<string,string>) => titles[data.document.document_id] ?? `${sourceKind(data.document.source_kind)} 원문`;

function selectorKey(selector:Citation['selector']) {
  if(selector.kind==='table_cell')return JSON.stringify([selector.kind,selector.table_id,selector.cell_id,selector.quote]);
  const position=[selector.kind,selector.start,selector.end,selector.quote,selector.prefix,selector.suffix];
  return JSON.stringify(selector.kind==='pdf'?[...position,selector.page_number,selector.regions.map(box=>[box.x0,box.y0,box.x1,box.y1])]:position);
}

/** Only an exact result citation opens a freshly authorized canonical original. */
export function useResearchEvidence(workspaceId:string, run:ResearchRun|null, hidden = false, onAuthorityLost: (error:EvidenceError) => void) {
  const identity=`${workspaceId}/${run?.run_id??'new'}`;
  const [reader,setReader]=useState<Reader|null>(null);
  const [lookup,setLookup]=useState<{identity:string; kind:'loading'|'failure'}|null>(null);
  const pending=useRef<AbortController|null>(null);
  const titles=run?.result?.source_titles??{};
  const identityRef=useRef(identity);identityRef.current=identity;
  const deniedRef=useRef<string|null>(null);
  const onAuthorityLostRef=useRef(onAuthorityLost);onAuthorityLostRef.current=onAuthorityLost;
  function deny(error:EvidenceError) {
    if(identityRef.current!==identity)return;
    deniedRef.current=identity;
    pending.current?.abort();setReader(null);setLookup(null);
    onAuthorityLostRef.current(error);
  }
  useEffect(()=>{
    pending.current?.abort();setReader(null);setLookup(null);deniedRef.current=null;
    return()=>pending.current?.abort();
  },[identity,hidden]);
  function cancelLookup() {
    const controller=pending.current;pending.current=null;controller?.abort();setLookup(null);
  }
  function closeReader() {cancelLookup();setReader(null);}
  function show(item:Loaded,citationId:string,origin:HTMLElement|null) {
    cancelLookup();
    setReader({...item,identity,citationId,origin});
  }
  async function openCitation(citationId:string) {
    if(!run?.result || hidden || deniedRef.current===identity)return;
    const proof=run.result.canvas.research.evidence.find(item=>item.citations.some(citation=>citation.citation_id===citationId));
    const canonical=proof?.citations.find(citation=>citation.citation_id===citationId);
    if(!proof || !canonical)return;
    const origin=document.activeElement instanceof HTMLElement?document.activeElement:null;
    pending.current?.abort();const controller=new AbortController();pending.current=controller;
    setLookup({identity,kind:'loading'});
    const candidates=run.snapshot_ids;
    for(const snapshotId of candidates) {
      try {
        const {data}=await getEvidence(workspaceId,snapshotId,{signal:controller.signal});
        if(controller.signal.aborted || pending.current!==controller || identityRef.current!==identity)return;
        const citation=data.citations.find(item=>item.citation_id===citationId);
        if(data.document.document_id!==proof.document.document_id || data.version.version_id!==proof.version.version_id || !citation || citation.representation_id!==canonical.representation_id || selectorKey(citation.selector)!==selectorKey(canonical.selector))continue;
        show({snapshotId,data,title:titleFor(data,titles)},citationId,origin);return;
      } catch(error) {
        if(controller.signal.aborted || pending.current!==controller || identityRef.current!==identity)return;
        if(error instanceof EvidenceError && ['authentication','not-found'].includes(error.kind)){deny(error);return;}
      }
    }
    if(!controller.signal.aborted && pending.current===controller){pending.current=null;setLookup({identity,kind:'failure'});}
  }
  const currentReader=!hidden && reader?.identity===identity?reader:null;
  return {
    openCitation,
    drawer:<>
      {!hidden && lookup?.identity===identity && <p role={lookup.kind==='failure'?'alert':'status'} className="research-feedback">{lookup.kind==='loading'?'인용의 저장 원문을 여는 중…':'인용의 저장 원문을 열 수 없습니다. 자료를 다시 확인해 주세요.'}</p>}
      {currentReader && <EvidenceDrawer key={`${identity}/${currentReader.snapshotId}/${currentReader.citationId}`} reader={currentReader} workspaceId={workspaceId} onClose={closeReader}/>}
    </>,
  };
}
export function EvidenceDrawer({reader,workspaceId,onClose,onCitation}:{reader:Reader;workspaceId:string;onClose:()=>void;onCitation?:(id:string)=>void}) {
  const modal=useRef<HTMLDialogElement>(null);
  const searchState=useRef({kind:'research-citation',citationId:reader.citationId});
  useLayoutEffect(()=>{
    const element=modal.current; element?.showModal();
    return()=>{element?.close();if(reader.origin?.isConnected)reader.origin.focus({preventScroll:true});};
  },[reader.origin]);
  return <dialog ref={modal} className="research-evidence-drawer" aria-label="원문과 인용 읽기" onCancel={event=>{event.preventDefault();onClose();}} onClose={onClose}>
    <div className="research-drawer-heading"><span>선택한 근거</span><button type="button" onClick={onClose} autoFocus>닫기</button></div>
    <div className="research-drawer-body">{reader.attribution && <p className="reader-note">{reader.attribution.attribution} · 공공누리 제1유형 · 사진 및 외부 저작물 제외</p>}<SavedEvidence onCitationSelect={onCitation} publisher={reader.attribution?.publisher} publicCopy={Boolean(reader.attribution)} data={reader.data} workspaceId={workspaceId} snapshotId={reader.snapshotId} title={reader.title} searchState={searchState.current}/></div>
  </dialog>;
}
