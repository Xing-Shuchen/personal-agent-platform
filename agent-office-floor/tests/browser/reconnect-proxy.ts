/** Manual, loopback-only TCP interruption probe for the real Gateway. */
import { createServer as createHttpServer } from 'node:http';
import { createServer as createTcpServer, Socket } from 'node:net';

const gatewayPort = Number(process.env.PAP_PROBE_GATEWAY_PORT);
const proxyPort = Number(process.env.PAP_PROBE_PROXY_PORT ?? 18790);
const controlPort = Number(process.env.PAP_PROBE_CONTROL_PORT ?? 18791);
if (![gatewayPort, proxyPort, controlPort].every(port => Number.isInteger(port) && port > 0 && port <= 65535) ||
    new Set([gatewayPort, proxyPort, controlPort]).size !== 3)
  throw new Error('set distinct loopback probe ports');

const sockets = new Set<Socket>();
const tcp = createTcpServer(client => {
  const upstream = new Socket();
  sockets.add(client); sockets.add(upstream);
  const close = () => { client.destroy(); upstream.destroy(); sockets.delete(client); sockets.delete(upstream); };
  client.on('error', close); upstream.on('error', close);
  client.on('close', close); upstream.on('close', close);
  upstream.connect(gatewayPort, '127.0.0.1', () => { client.pipe(upstream); upstream.pipe(client); });
});
const control = createHttpServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/drop') { res.writeHead(404).end(); return; }
  const count = sockets.size / 2;
  for (const socket of [...sockets]) socket.destroy();
  res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' })
    .end(JSON.stringify({ droppedConnections: count }));
});
tcp.listen(proxyPort, '127.0.0.1', () => process.stdout.write(`probe proxy listening on ${proxyPort}\n`));
control.listen(controlPort, '127.0.0.1', () => process.stdout.write(`probe control listening on ${controlPort}\n`));
