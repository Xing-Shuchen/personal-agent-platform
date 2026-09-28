<script>
  export let series;
  export let events=[];
  export let openWeek=()=>{};
  function weekStart(value){if(!value)return '';const date=new Date(value.slice(0,10)+'T00:00:00Z');if(Number.isNaN(date.getTime()))return '';date.setUTCDate(date.getUTCDate()-(date.getUTCDay()+6)%7);return date.toISOString().slice(0,10)}
  function summaries(bins,items){const byWeek=new Map((bins||[]).map(bin=>[bin.start,{start:bin.start,events:0,covered:0,claimStates:{}}]));for(const event of items){const week=byWeek.get(weekStart(event.occurred_at));if(!week)continue;week.events++;if(event.source_count>0)week.covered++;for(const [state,count] of Object.entries(event.claim_state_summary||{}))week.claimStates[state]=(week.claimStates[state]||0)+count}return [...byWeek.values()].map(week=>({...week,claims:Object.values(week.claimStates).reduce((sum,count)=>sum+count,0)}))}
  $: weeks=summaries(series?.bins,events);
  $: maxEvents=Math.max(1,...weeks.map(week=>week.events));
  $: maxClaims=Math.max(1,...weeks.map(week=>week.claims));
</script>

{#if weeks.length}
  <div class="wh-context-charts">
    <div><h4>Source coverage</h4><div class="wh-chart-bars" aria-label="每周 Event 来源覆盖率">{#each weeks as week}<button title={`${week.start} · ${week.covered}/${week.events} Events 有 Source`} aria-label={`${week.start}：${week.covered}/${week.events} Events 有 Source`} on:click={()=>openWeek(week.start)}><span class="wh-chart-track" style={`height:${Math.max(2,week.events/maxEvents*48)}px`}><span class="wh-chart-covered" style={`height:${week.events?week.covered/week.events*100:0}%`}></span></span></button>{/each}</div><small>浅色：有 Source 的 Event；轨道：全部 Event。按发生日期分周。</small></div>
    <div><h4>Claim states</h4><div class="wh-chart-bars" aria-label="每周 Event 关联 Claim 状态">{#each weeks as week}<button title={`${week.start} · ${week.claims} 条 Event–Claim 关联 · ${Object.entries(week.claimStates).map(([state,count])=>`${state} ${count}`).join(' / ')||'无 Claim'}`} aria-label={`${week.start}：${week.claims} 条 Event–Claim 关联`} on:click={()=>openWeek(week.start)}><span class="wh-chart-track wh-claim-track" style={`height:${Math.max(2,week.claims/maxClaims*48)}px`}><span class="wh-chart-uncertain" style={`height:${week.claims?(week.claimStates.uncertain||0)/week.claims*100:0}%`}></span><span class="wh-chart-contested" style={`height:${week.claims?['contested','corrected','superseded','retracted'].reduce((sum,state)=>sum+(week.claimStates[state]||0),0)/week.claims*100:0}%`}></span></span></button>{/each}</div><small>深色：争议、修正、取代或撤回；中间色：不确定；其余为其他状态。按 Event 发生日期分周，计 Event–Claim 关联。</small></div>
  </div>
{/if}
