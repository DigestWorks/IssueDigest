import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {listPublicBriefings, type PublicBriefingSummary} from '@issuedigest/api-client';
import './public-briefings.css';

export function BriefingDate({value,instant=false}: {value:string;instant?:boolean}) {
  return <time dateTime={value}>{value.slice(0,10).replaceAll('-','.')}{instant ? ` ${value.slice(11,16)} UTC` : ''}</time>;
}
export function PublicBriefingList() {
  const [items,setItems]=useState<PublicBriefingSummary[]>([]);
  const [failed,setFailed]=useState(false);
  const [attempt,setAttempt]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();setFailed(false);
    void listPublicBriefings({signal:controller.signal}).then(({data})=>{if(!controller.signal.aborted)setItems(data.items);},()=>{if(!controller.signal.aborted){setItems([]);setFailed(true);}});
    return()=>controller.abort();
  },[attempt]);
  if(failed)return <div className="public-list-feedback"><p role="status">공개 브리핑 목록을 확인하지 못했습니다.</p><button type="button" onClick={()=>setAttempt(value=>value+1)}>브리핑 목록 다시 읽기</button></div>;
  if(!items.length)return null;
  return <section className="public-briefing-list" aria-labelledby="public-list-title"><h2 id="public-list-title">공개 브리핑</h2><ol>{items.map(item=><li key={item.slug}><p className="public-list-date">기준 <BriefingDate value={item.as_of}/></p><h3><Link to={`/briefings/${item.slug}`}><span>{item.title}</span><span className="reading-arrow" aria-hidden="true">↗</span></Link></h3><p>{item.description}</p></li>)}</ol></section>;
}
