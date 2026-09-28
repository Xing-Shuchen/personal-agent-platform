<script>
  export let series = {measure:'event_count',aggregation:'week',window:'latest_12_weeks',bins:[]};
  export let width = 108;
  export let height = 26;
  $: counts = (series?.bins || []).map(bin => bin.count);
  $: peak = Math.max(1, ...counts);
  $: points = counts.map((count, index) => `${2 + index * (width - 4) / Math.max(1, counts.length - 1)},${height - 3 - count / peak * (height - 7)}`).join(' ');
  $: total = counts.reduce((sum, count) => sum + count, 0);
</script>

<span class="wh-spark" title={`截至最新 Event 所在周的 12 周，每周发生的 Event：${counts.join('、') || '无日期记录'}`} aria-label={`截至最新 Event 所在周的 12 周 Event 活动：${total} 条；按周计数`}>
  <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-hidden="true">
    <line x1="2" y1={height - 3} x2={width - 2} y2={height - 3} class="wh-spark-base"/>
    {#if counts.length > 1}<polyline points={points} class="wh-spark-line"/>{:else}<circle cx="3" cy={height - 3} r="2" class="wh-spark-zero"/>{/if}
  </svg>
  <span class="wh-spark-caption">{total} Events / 12 周</span>
</span>
