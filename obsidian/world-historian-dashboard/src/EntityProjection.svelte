<script>
  import worldPath from './world-path.json';
  export let entity;
  export let repository;
  export let scope = {search:'',from:'',to:'',threadId:'',entityId:'',locationId:'',status:'',priority:'',claimState:''};
  export let projection = 'Graph';
  export let openThread = () => {};
  export let openEntity = () => {};
  export let openLocation = () => {};
  $: scoped = Object.values(scope).some(Boolean);
  $: visibleThreads = scoped?new Set(repository.filteredThreads(scope).map(thread=>thread.thread_id)):null;
  $: threads = (entity?.thread_ids || []).filter(id=>!visibleThreads||visibleThreads.has(id)).slice(0, 5).map(id => repository.threadById.get(id)).filter(Boolean);
  $: related = (entity?.related_entity_ids || []).slice(0, 4).map(id => repository.entityById.get(id)).filter(Boolean);
  $: neighbors = [...threads.map(thread => ({id:thread.thread_id,label:thread.title,type:'thread'})), ...related.map(item => ({id:item.entity_id,label:item.name,type:'entity'}))];
  $: scopedEvents = scoped?(entity?.event_ids||[]).map(id=>repository.eventById.get(id)).filter(event=>event&&repository.matchesEvent(event,scope)):[];
  $: locationIds = scoped?[...new Set(scopedEvents.flatMap(event=>event.location_ids))]:(entity?.location_ids||[]);
  $: locations = locationIds.slice(0, 18).map(id => repository.locationById.get(id)).filter(Boolean);
</script>

<div class="wh-projection" data-projection={projection}>
  {#if projection === 'Graph'}
    <svg class="wh-mini-graph" viewBox="0 0 280 180" role="img" aria-label={`${entity.name} 与 ${threads.length} 个 Thread、${related.length} 个 Entity 的关系`}>
      {#each neighbors as neighbor, i}<line x1="140" y1="90" x2={140 + 96 * Math.cos(2 * Math.PI * i / neighbors.length - Math.PI / 2)} y2={90 + 65 * Math.sin(2 * Math.PI * i / neighbors.length - Math.PI / 2)} class="wh-mini-edge"><title>{neighbor.type === 'thread' ? '参与 Thread' : '相关 Entity'}</title></line>{/each}
      <circle cx="140" cy="90" r="16" class="wh-mini-entity"/><text x="140" y="94" text-anchor="middle">E</text>
      {#each neighbors as neighbor, i}<g role="button" tabindex="0" on:click={() => neighbor.type === 'thread' ? openThread(neighbor.id) : openEntity(neighbor.id)} on:keydown={event => event.key === 'Enter' && (neighbor.type === 'thread' ? openThread(neighbor.id) : openEntity(neighbor.id))}><circle cx={140 + 96 * Math.cos(2 * Math.PI * i / neighbors.length - Math.PI / 2)} cy={90 + 65 * Math.sin(2 * Math.PI * i / neighbors.length - Math.PI / 2)} r="10" class:wh-mini-entity={neighbor.type === 'entity'} class:wh-mini-thread-node={neighbor.type === 'thread'}/><title>{neighbor.label} · {neighbor.type}</title></g>{/each}
    </svg>
    <div class="wh-mini-legend">● Entity　◯ Thread · 关系见节点提示</div>
    {#each neighbors as neighbor}<button class="wh-mini-link" on:click={() => neighbor.type === 'thread' ? openThread(neighbor.id) : openEntity(neighbor.id)}>{neighbor.label}</button>{:else}<p class="wh-muted">没有可见关系。</p>{/each}
  {:else}
    {#if locations.length}<svg class="wh-mini-map" viewBox="0 0 900 450" role="img" aria-label={`${entity.name} 关联 Event 的地点`}><path d={worldPath} class="wh-world-shape"/>{#each locations as location}<g role="button" tabindex="0" on:click={() => openLocation(location.location_id)} on:keydown={event => event.key === 'Enter' && openLocation(location.location_id)}><circle cx={(location.lon + 180) * 2.5} cy={(90 - location.lat) * 2.5} r={location.geo_precision === 'exact' || location.geo_precision === 'city' ? 7 : 13} class:approximate={location.geo_precision !== 'exact' && location.geo_precision !== 'city'} class="wh-mini-map-dot"/><title>{location.name} · Event 地点 · {location.geo_precision}</title></g>{/each}</svg><div class="wh-mini-legend">● 精确 / 城市　◌ 区域 / 近似 · Event 发生地</div>{#each locations as location}<button class="wh-mini-link" on:click={() => openLocation(location.location_id)}>{location.name} · {location.geo_precision}</button>{/each}{:else}<p class="wh-muted">没有有坐标的相关 Event 地点。</p>{/if}
  {/if}
</div>
