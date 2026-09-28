<script>
  import worldPath from './world-path.json';
  import ActivitySparkline from './ActivitySparkline.svelte';
  export let thread;
  export let repository;
  export let scope = {search:'',from:'',to:'',threadId:'',entityId:'',locationId:'',status:'',priority:'',claimState:''};
  export let projection = 'Time';
  export let openEvent = () => {};
  export let openEntity = () => {};
  export let openLocation = () => {};
  function scopedSeries(items){
    const dated=items.map(event=>event.occurred_at||event.reported_at||event.first_observed_at).filter(Boolean).map(value=>new Date(value.slice(0,10)+'T00:00:00Z')).filter(date=>Number.isFinite(date.getTime()));
    if(!dated.length)return {measure:'event_count',aggregation:'week',window:'latest_12_weeks',bins:[]};
    const end=new Date(dated.reduce((latest,date)=>Math.max(latest,date.getTime()),0));end.setUTCDate(end.getUTCDate()-(end.getUTCDay()+6)%7);
    const start=new Date(end);start.setUTCDate(start.getUTCDate()-77);
    const bins=Array.from({length:12},(_,i)=>{const day=new Date(start);day.setUTCDate(day.getUTCDate()+i*7);return {start:day.toISOString().slice(0,10),count:0}});
    for(const date of dated){const week=new Date(date);week.setUTCDate(week.getUTCDate()-(week.getUTCDay()+6)%7);const index=Math.floor((week.getTime()-start.getTime())/604800000);if(index>=0&&index<12)bins[index].count++}
    return {measure:'event_count',aggregation:'week',window:'latest_12_weeks',bins};
  }
  $: scoped = Object.values(scope).some(Boolean);
  $: scopedEvents = (thread?.event_summaries || []).filter(event=>!scoped||repository.matchesEvent(event,scope));
  $: events = scopedEvents.slice(0, 6);
  $: series = scoped?scopedSeries(scopedEvents):thread.activity_series;
  $: entityIds = scoped?[...new Set(scopedEvents.flatMap(event=>event.entity_ids))]:(thread?.top_entity_ids || []);
  $: entities = entityIds.slice(0, 5).map(id => repository.entityById.get(id)).filter(Boolean);
  $: locationIds = scoped?[...new Set(scopedEvents.flatMap(event=>event.location_ids))]:(thread?.location_ids || []);
  $: locations = locationIds.slice(0, 18).map(id => repository.locationById.get(id)).filter(Boolean);
</script>

<div class="wh-projection" data-projection={projection}>
  {#if projection === 'Time'}
    <ActivitySparkline {series} width={220} height={46}/>
    <div class="wh-mini-timeline">
      {#each events as event}<button class="wh-mini-event" on:click={() => openEvent(event)} title={event.title}><span class:approximate={event.time_precision !== 'day'} class:corrected={event.has_corrected_claim} class:contested={event.has_contested_claim} class="wh-mini-dot"></span><time>{(event.occurred_at || event.reported_at || event.first_observed_at || '未知').slice(0, 10)}</time><span>{event.title}</span>{#if event.has_corrected_claim}<small title="Claim 修正">↺</small>{/if}{#if event.has_contested_claim}<small title="Claim 争议">⇄</small>{/if}</button>{:else}<p class="wh-muted">尚无 Event。</p>{/each}
    </div>
  {:else if projection === 'Graph'}
    <svg class="wh-mini-graph" viewBox="0 0 280 180" role="img" aria-label={`Thread ${thread.title} 与 ${entities.length} 个关联 Entity`}>
      {#each entities as entity, i}<line x1="140" y1="90" x2={140 + 95 * Math.cos(2 * Math.PI * i / entities.length - Math.PI / 2)} y2={90 + 62 * Math.sin(2 * Math.PI * i / entities.length - Math.PI / 2)} class="wh-mini-edge"><title>涉及 Entity</title></line>{/each}
      <rect x="98" y="74" width="84" height="32" rx="12" class="wh-mini-thread"/><text x="140" y="94" text-anchor="middle">Thread</text>
      {#each entities as entity, i}<g role="button" tabindex="0" on:click={() => openEntity(entity.entity_id)} on:keydown={event => event.key === 'Enter' && openEntity(entity.entity_id)}><circle cx={140 + 95 * Math.cos(2 * Math.PI * i / entities.length - Math.PI / 2)} cy={90 + 62 * Math.sin(2 * Math.PI * i / entities.length - Math.PI / 2)} r="12" class="wh-mini-entity"/><title>{entity.name} · 涉及 Entity</title></g>{/each}
    </svg>
    <div class="wh-mini-legend">▢ Thread　● Entity · 关系：涉及</div>
    {#each entities as entity}<button class="wh-mini-link" on:click={() => openEntity(entity.entity_id)}>{entity.name}</button>{:else}<p class="wh-muted">此 Thread 暂无关联 Entity。</p>{/each}
  {:else}
    {#if locations.length}
      <svg class="wh-mini-map" viewBox="0 0 900 450" role="img" aria-label={`Thread ${thread.title} 的 ${locations.length} 个地点`}><path d={worldPath} class="wh-world-shape"/>{#each locations as location}<g role="button" tabindex="0" on:click={() => openLocation(location.location_id)} on:keydown={event => event.key === 'Enter' && openLocation(location.location_id)}><circle cx={(location.lon + 180) * 2.5} cy={(90 - location.lat) * 2.5} r={location.geo_precision === 'exact' || location.geo_precision === 'city' ? 7 : 13} class:approximate={location.geo_precision !== 'exact' && location.geo_precision !== 'city'} class="wh-mini-map-dot"/><title>{location.name} · {location.geo_precision}</title></g>{/each}</svg>
      <div class="wh-mini-legend">● 精确 / 城市　◌ 区域 / 近似</div>
      {#each locations as location}<button class="wh-mini-link" on:click={() => openLocation(location.location_id)}>{location.name} · {location.geo_precision}</button>{/each}
    {:else}<p class="wh-muted">此 Thread 没有有坐标的 Event 地点。</p>{/if}
  {/if}
</div>
