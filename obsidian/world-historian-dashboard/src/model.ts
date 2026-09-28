import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';

export type Ref = {kind:string; table?:string; id?:string; obsidian_path?:string; path?:string};
export type Scope = {search:string; from:string; to:string; threadId:string; entityId:string; locationId:string; status:string; priority:string; claimState:string};
export type ActivitySeries = {measure:'event_count';aggregation:'week';window:'latest_12_weeks';bins:{start:string;count:number}[]};
export const emptyScope = ():Scope => ({search:'',from:'',to:'',threadId:'',entityId:'',locationId:'',status:'',priority:'',claimState:''});
export type Thread = {thread_id:string;title:string;status:string;priority:string;tracking_since:string;last_meaningful_change_at:string|null;latest_event_summary:string|null;activity_series?:ActivitySeries;recent_change_types?:string[];open_question_count:number;event_count:number;source_count:number;stale:boolean;top_entity_ids:string[];location_ids:string[];attention:{required:boolean;reasons:string[]};canonical_ref:Ref;current_state_excerpt:string|null;latest_event_id:string|null;event_ids?:string[];event_summaries?:Event[];entity_ids?:string[];open_questions?:Question[];current_state?:{text:string|null;provenance:string;updated_at:string|null;revision?:string|null;source_refs?:string[];canonical_ref?:Ref;stale:boolean};annotations?:{text:string;provenance:string;canonical_ref:Ref}[];related_threads?:{thread_id:string;type:string}[]};
export type Question = {question_id:string;question:string;state:string;opened_at:string;last_updated_at:string;answer_event_id:string|null;canonical_ref:Ref};
export type Event = {event_id:string;thread_ids:string[];title:string;summary:string;occurred_at:string|null;reported_at:string|null;first_observed_at:string|null;time_precision:string;confidence:number;state:string;entity_ids:string[];location_ids:string[];claim_count:number;source_count:number;claim_states:string[];canonical_ref:Ref;claims?:Claim[]};
export type Claim = {claim_id:string;statement:string;state:string;canonical_state:string;confidence:number;superseded_by:string|null;source:{source_id:string;title:string;publisher:string|null;source_kind:string;published_at:string|null;relationship:string;url:string;canonical_ref:Ref}|null};
export type Entity = {entity_id:string;name:string;kind:string;aliases:string[];thread_ids:string[];thread_count:number;event_count:number;last_seen_at:string|null;activity_series?:ActivitySeries;canonical_ref:Ref;event_ids?:string[];related_entity_ids?:string[];location_ids?:string[];current_thread_ids?:string[];contextual_questions?:{question_id:string;question:string;state:string;owner_thread_id:string}[]};
export type Location = {location_id:string;name:string;country_code?:string;region?:string;lat:number;lon:number;geo_precision:string;event_ids:string[];thread_ids:string[];canonical_source_ref:Ref};
export type Edge = {id:string;source:string;target:string;type:string;confidence?:number;evidence_refs?:unknown[];canonical_ref?:Ref};
export type Graph = {nodes:Record<string,{type:string;label:string;canonical_ref:Ref;state?:string;confidence?:number;owner_thread_id?:string;owner_event_id?:string;url?:string;publisher?:string}>;edges:Edge[]};
export type GraphNode=Graph['nodes'][string];
export type Manifest = {schema_version:string;generator_version:string;generated_at:string;source_revision:string;thread_count:number;event_count:number;entity_count:number;location_count:number};
export type SearchHit={type:'thread'|'event'|'entity';id:string;label:string;summary:string};

export class Repository {
  root:string;
  warning='';
  graphFault='';
  manifest:Manifest;
  threads:Thread[];
  entities:Entity[];
  locations:Location[];
  threadById:Map<string,Thread>;
  entityById:Map<string,Entity>;
  locationById:Map<string,Location>;
  private _timeline?:Event[];
  private timelinePartitions:{key:string;count:number}[];
  private loadedPartitions=new Map<string,Event[]>();
  private _eventById?:Map<string,Event>;
  private _graphManifest?:{format:string;node_count:number;edge_count:number;edge_types:string[];buckets:string[]};
  private graphBuckets=new Map<string,{nodes:Record<string,GraphNode>;adjacency:Record<string,Edge[]>}>();
  private _searchHits?:SearchHit[];
  private _searchIndex?:Map<string,Set<number>>;
  static open(output:string):Repository {
    let pointer='';
    try {pointer=readFileSync(join(output,'CURRENT'),'utf8').trim();return new Repository(output,pointer)}
    catch (error) {
      let candidates:string[]=[];
      try{candidates=readdirSync(join(output,'generations')).filter(name=>name!==pointer).sort().reverse()}catch{throw error}
      for(const candidate of candidates){try{const repository=new Repository(output,candidate);repository.warning=`Current generation invalid; using ${candidate}. ${String(error)}`;return repository}catch{continue}}
      throw error;
    }
  }
  constructor(output:string,pointer?:string) {
    pointer=pointer??readFileSync(join(output,'CURRENT'),'utf8').trim();
    if (!/^world-historian-dashboard\.v1-0\.7\.[01]-[a-f0-9]{20}$/.test(pointer)) throw Error('Invalid generation pointer');
    this.root=join(output,'generations',pointer);
    const get=<T>(name:string):T=>JSON.parse(readFileSync(join(this.root,name),'utf8')) as T;
    this.manifest=get<Manifest>('manifest.json');
    if(this.manifest.schema_version!=='world-historian-dashboard.v1') throw Error('Unsupported dashboard schema');
    if(!existsSync(join(this.root,'graph-manifest.json'))||!existsSync(join(this.root,'timeline-partitions.json')))throw Error('Incomplete dashboard generation');
    this.timelinePartitions=get<{key:string;count:number}[]>('timeline-partitions.json');
    if(!Array.isArray(this.timelinePartitions)||this.timelinePartitions.reduce((n,p)=>n+p.count,0)!==this.manifest.event_count||this.timelinePartitions.some(p=>!/^(\d{4}-\d{2}|undated)$/.test(p.key)||!Number.isInteger(p.count)||p.count<0))throw Error('Invalid timeline partitions');
    const graphManifest=get<{format:string;node_count:number;edge_count:number;edge_types:string[];buckets:string[]}>('graph-manifest.json');
    if(graphManifest.format!=='sharded-adjacency.v1'||!Array.isArray(graphManifest.buckets)||!Array.isArray(graphManifest.edge_types))throw Error('Invalid graph manifest');
    this._graphManifest=graphManifest;
    this.threads=get<Thread[]>('threads.json');this.entities=get<Entity[]>('entities.json');this.locations=get<Location[]>('locations.json');
    if(this.threads.length!==this.manifest.thread_count||this.entities.length!==this.manifest.entity_count||this.locations.length!==this.manifest.location_count) throw Error('Invalid dashboard generation');
    this.threadById=new Map(this.threads.map(t=>[t.thread_id,t]));this.entityById=new Map(this.entities.map(e=>[e.entity_id,e]));this.locationById=new Map(this.locations.map(l=>[l.location_id,l]));
  }
  private partition(key:string):Event[]{let items=this.loadedPartitions.get(key);if(!items){items=JSON.parse(readFileSync(join(this.root,'timeline',`${key}.json`),'utf8')) as Event[];if(items.length!==this.timelinePartitions.find(p=>p.key===key)?.count)throw Error('Invalid timeline partition');this.loadedPartitions.set(key,items)}return items}
  get timeline():Event[]{if(!this._timeline){this._timeline=this.timelinePartitions.flatMap(p=>this.partition(p.key));if(this._timeline.length!==this.manifest.event_count)throw Error('Invalid timeline index')}return this._timeline}
  get eventById():Map<string,Event>{if(!this._eventById)this._eventById=new Map(this.timeline.map(e=>[e.event_id,e]));return this._eventById}
  get graphManifest(){if(!this._graphManifest){const value=JSON.parse(readFileSync(join(this.root,'graph-manifest.json'),'utf8'));if(value.format!=='sharded-adjacency.v1')throw Error('Invalid graph format');this._graphManifest=value}return this._graphManifest!}
  private bucket(id:string){const prefix=createHash('sha256').update(id).digest('hex').slice(0,2);let bucket=this.graphBuckets.get(prefix);if(!bucket){bucket=JSON.parse(readFileSync(join(this.root,'graph',`${prefix}.json`),'utf8'));if(!bucket?.nodes||!bucket?.adjacency)throw Error('Invalid graph bucket');this.graphBuckets.set(prefix,bucket);if(this.graphBuckets.size>24)this.graphBuckets.delete(this.graphBuckets.keys().next().value!)}return bucket}
  graphNode(id:string):GraphNode|undefined{try{return this.bucket(id).nodes[id]}catch(error){this.graphFault=`Graph bucket could not be read: ${String(error)}`;return undefined}}
  neighbors(id:string):Edge[]{try{return this.bucket(id).adjacency[id]||[]}catch(error){this.graphFault=`Graph bucket could not be read: ${String(error)}`;return []}}
  graphEdgeTypes():string[]{try{return this.graphManifest.edge_types}catch(error){this.graphFault=`Graph manifest could not be read: ${String(error)}`;return []}}
  private initSearch(){if(this._searchIndex)return;this._searchHits=[...this.threads.map(t=>({type:'thread' as const,id:t.thread_id,label:t.title,summary:t.latest_event_summary||''})),...this.timeline.map(e=>({type:'event' as const,id:e.event_id,label:e.title,summary:e.summary})),...this.entities.map(e=>({type:'entity' as const,id:e.entity_id,label:e.name,summary:e.aliases.join(' ')}))];this._searchIndex=new Map();this._searchHits.forEach((hit,index)=>{for(const gram of this.grams((hit.label+' '+hit.summary).toLocaleLowerCase())){let set=this._searchIndex!.get(gram);if(!set){set=new Set();this._searchIndex!.set(gram,set)}set.add(index)}})}
  private grams(value:string):Set<string>{const chars=[...value];const grams=new Set<string>();for(let i=0;i<chars.length;i++){if(!chars[i].trim())continue;grams.add(chars[i]);if(i+1<chars.length)grams.add(chars[i]+chars[i+1])}return grams}
  search(query:string,limit=20):SearchHit[]{const normalized=query.trim().toLocaleLowerCase();if(!normalized)return [];this.initSearch();const hits=this._searchHits!,index=this._searchIndex!;const grams=[...this.grams(normalized)];if(!grams.length)return [];grams.sort((a,b)=>(index.get(a)?.size||0)-(index.get(b)?.size||0));const first=index.get(grams[0]);if(!first)return [];const matches=[];for(const number of first){if(grams.every(g=>index.get(g)?.has(number))){const hit=hits[number];if((hit.label+' '+hit.summary).toLocaleLowerCase().includes(normalized))matches.push(hit)}}matches.sort((a,b)=>Number(b.label.toLocaleLowerCase().startsWith(normalized))-Number(a.label.toLocaleLowerCase().startsWith(normalized))||a.label.localeCompare(b.label));return matches.slice(0,limit)}
  thread(id:string):Thread {return this.detail('threads',id) as Thread}
  event(id:string):Event {return this.detail('events',id) as Event}
  entity(id:string):Entity {return this.detail('entities',id) as Entity}
  private detail(kind:string,id:string):unknown {
    if(!/^[a-z0-9_-]+$/i.test(id)) throw Error('Invalid object ID');
    const path=join(this.root,kind,`${id}.json`);
    if(!existsSync(path)) throw Error(`Missing ${kind} detail: ${id}`);
    return JSON.parse(readFileSync(path,'utf8'));
  }
  matchesEvent(e:Event,scope:Scope):boolean {
    const date=e.occurred_at||e.reported_at||e.first_observed_at||'';
    return (!scope.from||date>=scope.from)&&(!scope.to||date.slice(0,10)<=scope.to)&&(!scope.threadId||e.thread_ids.includes(scope.threadId))&&(!scope.entityId||e.entity_ids.includes(scope.entityId))&&(!scope.locationId||e.location_ids.includes(scope.locationId))&&(!scope.claimState||e.claim_states.includes(scope.claimState))&&(!scope.status&&!scope.priority||e.thread_ids.some(id=>{const thread=this.threadById.get(id);return thread&&(!scope.status||thread.status===scope.status)&&(!scope.priority||thread.priority===scope.priority)}))&&(!scope.search||(e.title+' '+e.summary).toLocaleLowerCase().includes(scope.search.toLocaleLowerCase()));
  }
  filteredEvents(scope:Scope):Event[] {const partitions=scope.from||scope.to?this.timelinePartitions.filter(p=>p.key==='undated'||(!scope.from||p.key>=scope.from.slice(0,7))&&(!scope.to||p.key<=scope.to.slice(0,7))):this.timelinePartitions;return partitions.flatMap(p=>this.partition(p.key)).filter(e=>this.matchesEvent(e,scope))}
  filteredThreads(scope:Scope):Thread[] {const needsEvents=Boolean(scope.from||scope.to||scope.claimState);const visibleThreadIds=needsEvents?new Set(this.filteredEvents({...scope,search:''}).flatMap(e=>e.thread_ids)):null;return this.threads.filter(t=>
    (!scope.status||t.status===scope.status)&&(!scope.priority||t.priority===scope.priority)&&(!scope.threadId||t.thread_id===scope.threadId)&&(!scope.entityId||this.entityById.get(scope.entityId)?.thread_ids.includes(t.thread_id))&&(!scope.locationId||t.location_ids.includes(scope.locationId))&&(!visibleThreadIds||visibleThreadIds.has(t.thread_id))&&(!scope.search||(t.title+' '+(t.latest_event_summary||'')).toLocaleLowerCase().includes(scope.search.toLocaleLowerCase())))}
  filteredEntities(scope:Scope):Entity[] {const needsEvents=Boolean(scope.from||scope.to||scope.locationId||scope.claimState||scope.status||scope.priority);const visible=needsEvents?new Set(this.filteredEvents({...scope,search:''}).flatMap(e=>e.entity_ids)):null;return this.entities.filter(e=>(!scope.search||(e.name+' '+e.aliases.join(' ')).toLocaleLowerCase().includes(scope.search.toLocaleLowerCase()))&&(!scope.threadId||e.thread_ids.includes(scope.threadId))&&(!visible||visible.has(e.entity_id)))}
}
