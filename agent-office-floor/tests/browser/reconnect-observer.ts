/** Manual real-Gateway probe. Prints only aggregate state, never session keys or credentials. */
import { FloorStore, GatewayObserver } from '@pap/openclaw-adapter';

const token = process.env.OPENCLAW_GATEWAY_TOKEN;
const agentId = process.env.PAP_PROBE_AGENT_ID;
const proxyPort = Number(process.env.PAP_PROBE_PROXY_PORT ?? 18790);
if (!token || !agentId || !Number.isInteger(proxyPort) || proxyPort < 1 || proxyPort > 65535)
  throw new Error('set token, selected agent ID and loopback proxy port');

const store = new FloorStore();
const observer = new GatewayObserver({ gatewayId: 'reconnect-probe',
  gatewayUrl: `ws://127.0.0.1:${proxyPort}`, token, selectedAgentIds: [agentId] }, store);
let previous = '';
store.observe(() => {
  const state = store.snapshot();
  const agents = Object.values(state.agents);
  const summary = { connection: state.connection.state, mode: state.connection.mode,
    count: agents.length, fresh: agents.filter(agent => agent.freshness === 'fresh').length,
    stale: agents.filter(agent => agent.freshness === 'stale').length,
    runningStatus: agents.filter(agent => agent.work.status === 'running').length,
    running: agents.filter(agent => agent.freshness === 'fresh' && agent.work.status === 'running').length,
    epoch: state.epoch, subscription: state.capabilities.sessionEvents };
  const key = JSON.stringify(summary);
  if (key !== previous) { previous = key; process.stdout.write(`${key}\n`); }
});
observer.start();
process.on('SIGINT', () => { observer.stop(); process.exit(0); });
