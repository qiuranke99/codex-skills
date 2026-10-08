import test from 'node:test';
import assert from 'node:assert/strict';
import { PassThrough } from 'node:stream';
import { EventEmitter } from 'node:events';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { inspectNativeTrace, inspectAppServerTrace, validateHostEvidence, AppServerClient, executeHost, successfulToolItem } from '../runtime/host-adapter.mjs';
import { digest } from '../runtime/project-store.mjs';

const skillPath = 'D:/skills/visual-exploration-moodboard/SKILL.md';
const projectRoot = 'D:/work/project';
const skillText = '---\nname: visual-exploration-moodboard\n---\nActual current contract.\n';
const config = { skillText, skillPath, projectRoot, packagePath: 'D:/skills/visual-exploration-moodboard' };
const line = (type, payload) => JSON.stringify({ type, payload });
function trace({ model = 'gpt-6.1-sol', effort = 'ultra', content = skillText, after = true, outputError = false } = {}) {
  return [
    line('session_meta', { id: 'synthetic-only', cli_version: '0.160.0' }),
    line('turn_context', { model, effort }),
    line('response_item', { type: 'function_call', call_id: 'read', name: 'functions.exec', arguments: `Get-Content -LiteralPath '${skillPath}' -Raw` }),
    line('response_item', { type: 'function_call_output', call_id: 'read', output: JSON.stringify({ output: content, exit_code: outputError ? 1 : 0 }) }),
    ...(after ? [
      line('response_item', { type: 'function_call', call_id: 'work', name: 'functions.exec', arguments: `node scripts/moodboard.mjs check --project '${projectRoot}'` }),
      line('response_item', { type: 'function_call_output', call_id: 'work', output: '{"exit_code":0,"output":"observed result"}' })
    ] : [])
  ].join('\n');
}

test('native import requires full current tool-read content and subsequent same-turn project tool result', () => {
  const observed = inspectNativeTrace(trace(), config);
  assert.equal(observed.status, 'executed'); assert.equal(observed.actualToolActions, 1); assert.equal(observed.actualEffort, 'ultra');
  for (const options of [{ content: 'skill_loaded:true' }, { content: skillText.replace('current', 'old') }, { after: false }, { outputError: true }, { effort: 'high' }, { model: 'other-model' }]) assert.equal(inspectNativeTrace(trace(options), config).status, 'unverified');
  assert.equal(inspectNativeTrace(trace().replaceAll('\\"exit_code\\":0', '\\"exit_code\\":-1'), config).status, 'unverified');
  assert.equal(inspectNativeTrace(trace().replace('{\\"exit_code\\":0,\\"output\\":\\"observed result\\"}', '{\\"session_id\\":123,\\"output\\":\\"running\\"}'), config).status, 'unverified');
});
test('native evidence cannot cross a runtime turn or be supplied in a user message', () => {
  const unrelated = trace({ after: false }) + '\n' + line('turn_context', { model: 'gpt-6.1-sol', effort: 'ultra' }) + '\n' + trace().split('\n').slice(-2).join('\n');
  assert.equal(inspectNativeTrace(unrelated, config).status, 'unverified');
  const declared = [line('turn_context', { model: 'gpt-6.1-sol', effort: 'ultra' }), line('response_item', { type: 'message', role: 'user', content: skillText }), ...trace().split('\n').slice(-2)].join('\n');
  assert.equal(inspectNativeTrace(declared, config).status, 'unverified');
});
test('native parser handles escaped Windows paths and reports truncated live-log tail without swallowing mid-file corruption', () => {
  const escaped = trace().replaceAll('D:/skills/', 'D:\\\\skills\\\\').replaceAll('/visual-exploration-moodboard/', '\\\\visual-exploration-moodboard\\\\');
  assert.equal(inspectNativeTrace(escaped, config).status, 'executed');
  const installedAlias = trace().replaceAll('D:/skills/visual-exploration-moodboard/SKILL.md', 'C:/home/.agents/skills/visual-exploration-moodboard/SKILL.md');
  // An unresolvable alias is not evidence of the actual current Skill path.
  assert.equal(inspectNativeTrace(installedAlias, config).status, 'unverified');
  assert.equal(inspectNativeTrace(trace() + '\n{"type":', config).warnings.length, 1);
  assert.throws(() => inspectNativeTrace(trace() + '\nBAD\n' + line('session_meta', {}), config), { code: 'INVALID_HOST_TRACE' });
});

function mutateTrace(mutator) { const rows = trace().split('\n').map(JSON.parse); mutator(rows); return rows.map(JSON.stringify).join('\n'); }
test('native positive completion schemas reject missing, structured failed, unknown and running results', () => {
  for (const output of ['', null, {}, { output: 'Unverified' }, { exit_code: 1, output: 'Failed' }, { exit_code: -1, output: 'Failed' }, { exit_code: 0, isError: true, output: skillText }, { session_id: 123, output: 'Still running' }, 'success', '{"success":true}']) {
    assert.equal(inspectNativeTrace(mutateTrace(rows => { rows[5].payload.output = output; }), config).status, 'unverified', JSON.stringify(output));
  }
  assert.equal(inspectNativeTrace(mutateTrace(rows => { rows[3].payload.output = { isError: true, output: skillText }; }), config).status, 'unverified');
  assert.equal(inspectNativeTrace(mutateTrace(rows => { rows[3].payload.output = { exit_code: 0, output: skillText }; rows[5].payload.output = { exit_code: 0, output: '' }; }), config).status, 'executed');
});
test('native code-mode envelope requires a successful supported child result and preserves failures', () => {
  const envelope = value => [{ type: 'input_text', text: 'Script completed\nWall time 0.1 seconds\nOutput:\n' }, { type: 'input_text', text: JSON.stringify(value) }];
  const good = mutateTrace(rows => { rows[3].payload.output = envelope({ exit_code: 0, output: skillText }); rows[5].payload.output = envelope({ exit_code: 0, output: 'Done' }); });
  assert.equal(inspectNativeTrace(good, config).status, 'executed');
  for (const value of [{ exit_code: 2, output: 'Failed child' }, { isError: true, output: 'Failed child' }, { output: 'No completion state' }]) assert.equal(inspectNativeTrace(mutateTrace(rows => { rows[5].payload.output = envelope(value); }), config).status, 'unverified');
  assert.equal(inspectNativeTrace(mutateTrace(rows => { rows[5].payload.output = [{ type: 'input_text', text: 'Script completed\nWall time 0.1 seconds\nOutput:\n' }]; }), config).status, 'unverified');
});
test('native project binding uses complete normalized arguments/cwd, never sibling names or prose', () => {
  for (const cmd of [`node scripts/moodboard.mjs check --project '${projectRoot}-other'`, `node scripts/moodboard.mjs check --project '${projectRoot}/../other'`, `echo '${projectRoot}'`, `# node scripts/moodboard.mjs check --project '${projectRoot}'`, `node -e 'console.log("${projectRoot}")'`]) {
    assert.equal(inspectNativeTrace(mutateTrace(rows => { rows[4].payload.arguments = cmd; }), config).status, 'unverified', cmd);
  }
  for (const cmd of [`node scripts/moodboard.mjs check --project '${projectRoot}/subproject'`, `node scripts/moodboard.mjs check --project '${projectRoot}/../project'`]) assert.equal(inspectNativeTrace(mutateTrace(rows => { rows[4].payload.arguments = cmd; }), config).status, 'executed');
  const withCwd = mutateTrace(rows => { rows[4].payload.arguments = JSON.stringify({ cmd: 'node scripts/moodboard.mjs check --project .', workdir: projectRoot }); });
  assert.equal(inspectNativeTrace(withCwd, config).status, 'executed');
  const explicitOther = mutateTrace(rows => { rows[4].payload.arguments = JSON.stringify({ cmd: `node scripts/moodboard.mjs check --project '${projectRoot}-other'`, workdir: projectRoot }); });
  assert.equal(inspectNativeTrace(explicitOther, config).status, 'unverified');
  const outer = mutateTrace(rows => { rows[4].payload.arguments = `text(await tools.exec_command({cmd:${JSON.stringify(`node scripts/moodboard.mjs check --project '${projectRoot}'`)},workdir:'D:/unrelated'}));`; });
  assert.equal(inspectNativeTrace(outer, config).status, 'executed');
  const comment = mutateTrace(rows => { rows[4].payload.arguments = `// tools.exec_command({cmd:"node scripts/moodboard.mjs check --project '${projectRoot}'"})\ntext('Done')`; });
  assert.equal(inspectNativeTrace(comment, config).status, 'unverified');
});
test('native call/output cannot cross sessions, turns or contradictory explicit turn metadata', () => {
  for (const [index, record] of [
    [4, { type: 'session_meta', payload: { id: 'second', cli_version: '0.160.0' } }],
    [5, { type: 'turn_context', payload: { model: 'gpt-6-sol', effort: 'high' } }],
    [3, { type: 'turn_context', payload: { model: 'gpt-6.1-sol', effort: 'ultra' } }]
  ]) assert.equal(inspectNativeTrace(mutateTrace(rows => { rows.splice(index, 0, record); }), config).status, 'unverified');
  assert.equal(inspectNativeTrace(mutateTrace(rows => { rows[1].payload.turn_id = 'one'; rows[5].payload.internal_chat_message_metadata_passthrough = { turn_id: 'two' }; }), config).status, 'unverified');
  assert.equal(inspectNativeTrace(mutateTrace(rows => { rows.shift(); }), config).status, 'unverified');
  const duplicateSameTurn = mutateTrace(rows => { rows[1].payload.turn_id = 'same'; rows.splice(5, 0, { type: 'turn_context', payload: { turn_id: 'same', model: 'gpt-6.1-sol', effort: 'ultra' } }); });
  assert.equal(inspectNativeTrace(duplicateSameTurn, config).status, 'executed');
});

// Explicitly synthetic transport fixture; it never certifies a live model.
function protocol() {
  const client = (id, method, params) => ({ direction: 'client', message: { id, method, params } });
  const server = (id, result) => ({ direction: 'server', message: { id, result } });
  return [client(1, 'initialize', {}), server(1, { userAgent: 'Codex Desktop/0.160.0 synthetic' }), { direction: 'client', message: { method: 'initialized' } }, client(2, 'skills/list', { cwds: [projectRoot], forceReload: true }), server(2, { data: [{ cwd: projectRoot, skills: [{ name: 'visual-exploration-moodboard', enabled: true, path: skillPath }] }] }), client(3, 'thread/start', { cwd: projectRoot, model: 'gpt-6.1-sol', ephemeral: true, config: { model_reasoning_effort: 'ultra' } }), server(3, { thread: { id: 'synthetic-thread' }, cwd: projectRoot, model: 'gpt-6.1-sol', reasoningEffort: 'ultra' }), client(4, 'turn/start', { threadId: 'synthetic-thread', cwd: projectRoot, model: 'gpt-6.1-sol', effort: 'ultra', input: [{ type: 'skill', name: 'visual-exploration-moodboard', path: skillPath }] }), server(4, { turn: { id: 'synthetic-turn', status: 'inProgress' } }), { direction: 'server', message: { method: 'item/completed', params: { threadId: 'synthetic-thread', turnId: 'synthetic-turn', item: { id: 'synthetic-command', type: 'commandExecution', command: 'echo SYNTHETIC', commandActions: [], cwd: projectRoot, status: 'completed', exitCode: 0 } } } }, { direction: 'server', message: { method: 'turn/completed', params: { threadId: 'synthetic-thread', turn: { id: 'synthetic-turn', status: 'completed' } } } }];
}
const protocolText = rows => rows.map(JSON.stringify).join('\n');
test('app-server evidence is re-derived from correlated real-shaped protocol events', () => {
  const derived = inspectAppServerTrace(protocolText(protocol()), { skillPath, projectRoot });
  assert.equal(derived.status, 'executed'); assert.equal(derived.actualToolActions, 1); assert.equal(derived.runtimeEvidence.runtimeResponseLine, 7);
  const changes = [
    rows => { rows[6].message.result.model = 'wrong-model'; },
    rows => { rows[6].message.result.reasoningEffort = 'high'; },
    rows => { rows[7].message.params.input = [{ type: 'text', text: 'skill_loaded:true' }]; },
    rows => { rows[7].message.params.input[0].path = skillPath + '.old'; },
    rows => { rows[9].message.params.item.exitCode = 1; },
    rows => { rows[9].message.params.item.cwd = projectRoot + '-other'; },
    rows => { rows[9].message.params.turnId = 'other-turn'; },
    rows => { rows[10].message.params.turn.status = 'failed'; },
    rows => { rows.pop(); },
    rows => { rows[8].message.id = 900; },
    rows => { rows[3].message.params.forceReload = false; },
    rows => { rows[4].message.result.data[0].skills[0].enabled = false; },
    rows => { rows.push(rows[9]); },
    rows => { rows.splice(9, 0, rows[9]); }
  ];
  for (const mutate of changes) { const rows = protocol(); mutate(rows); assert.throws(() => inspectAppServerTrace(protocolText(rows), { skillPath, projectRoot }), { code: 'INVALID_HOST_EVIDENCE' }); }
  assert.throws(() => inspectAppServerTrace('not JSONL', { skillPath, projectRoot }), { code: 'INVALID_HOST_TRACE' });
});
test('host gate refuses ordinary claims, wrong schema and stale versions before trusting execution', async t => {
  const temporaryRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'vem-host-gate-'));
  assert.equal(path.dirname(await fs.realpath(temporaryRoot)), await fs.realpath(os.tmpdir()));
  t.after(async () => { await fs.rm(temporaryRoot, { recursive: true, force: true }); });
  await assert.rejects(validateHostEvidence(temporaryRoot, { schemaVersion: 1, kind: 'host-execution', status: 'executed' }), { code: 'INVALID_HOST_EVIDENCE' });
  const currentAdapter = digest(await fs.readFile(new URL('../runtime/host-adapter.mjs', import.meta.url)));
  for (const receipt of [{ schemaVersion: 2, kind: 'host-execution', status: 'executed', adapterDigest: currentAdapter }, { schemaVersion: 1, kind: 'host-execution', status: 'prepared', adapterDigest: currentAdapter }, { schemaVersion: 1, kind: 'host-execution', status: 'executed', adapterDigest: currentAdapter, skillDigest: 'old' }]) await assert.rejects(validateHostEvidence(temporaryRoot, receipt), { code: 'INVALID_HOST_EVIDENCE' });
  const raw = 'SYNTHETIC ordinary placeholder: not JSONL or execution evidence';
  await fs.writeFile(path.join(temporaryRoot, 'raw.txt'), raw);
  const currentSkill = digest(await fs.readFile(new URL('../SKILL.md', import.meta.url)));
  const placeholder = { schemaVersion: 1, kind: 'host-execution', host: 'native', status: 'executed', adapterDigest: currentAdapter, skillDigest: currentSkill, rawTrace: { path: 'raw.txt', kind: 'host-raw-trace', sha256: digest(raw) }, binary: { path: '/not-invoked/codex', sha256: 'a'.repeat(64), version: 'codex-cli 0.160.0' }, actualModel: 'gpt-6.1-sol', actualEffort: 'ultra', actualToolActions: 1 };
  await assert.rejects(validateHostEvidence(temporaryRoot, placeholder), { code: 'INVALID_HOST_EVIDENCE' });
  await assert.rejects(validateHostEvidence(temporaryRoot, { ...placeholder, host: 'codex-app-server' }), { code: 'INVALID_HOST_TRACE' });
  await assert.rejects(validateHostEvidence(temporaryRoot, { ...placeholder, rawTrace: { ...placeholder.rawTrace, sha256: 'b'.repeat(64) } }), { code: 'INVALID_HOST_EVIDENCE' });
});

function fakeProcess(handler) {
  const child = new EventEmitter(); child.stdin = new PassThrough(); child.stdout = new PassThrough(); child.stderr = new PassThrough();
  let pending = '';
  child.stdin.on('data', bytes => { pending += bytes; let index; while ((index = pending.indexOf('\n')) >= 0) { const data = pending.slice(0, index); pending = pending.slice(index + 1); handler(JSON.parse(data), message => child.stdout.write(JSON.stringify(message) + '\n')); } });
  child.stdin.on('finish', () => child.emit('exit', 0, null)); child.kill = () => { child.emit('exit', null, 'SIGTERM'); };
  return child;
}
test('app-server client correlates out-of-order JSON-RPC responses, rejects protocol errors and never grants server approvals', async () => {
  const received = []; let first;
  const client = new AppServerClient({ codexPath: 'synthetic', cwd: '.', timeoutMs: 100, spawnImpl: () => fakeProcess((message, send) => {
    received.push(message);
    if (message.method === 'first') first = message;
    if (message.method === 'second') { send({ id: message.id, result: 2 }); send({ id: first.id, result: 1 }); send({ id: 987, method: 'item/commandExecution/requestApproval', params: {} }); }
    if (message.method === 'bad') send({ id: message.id, error: { code: 1, message: 'unsupported' } });
  }) });
  assert.deepEqual(await Promise.all([client.request('first', {}), client.request('second', {})]), [1, 2]);
  assert.equal(received.find(m => m.id === 987)?.error?.code, -32601);
  await assert.rejects(client.request('bad', {}), { code: 'APP_SERVER_RPC' });
  await assert.rejects(client.request('never', {}, 10), { code: 'APP_SERVER_TIMEOUT' });
  await client.close();
});
test('app-server wait only resolves matching actual events and fails when transport closes', async () => {
  let process;
  const client = new AppServerClient({ codexPath: 'synthetic', cwd: '.', timeoutMs: 100, spawnImpl: () => (process = fakeProcess(() => {})) });
  process.stdout.write(JSON.stringify({ method: 'turn/completed', params: { turn: { id: 'wrong' } } }) + '\n');
  await assert.rejects(client.waitFor(m => m.params?.turn?.id === 'correct', 10), { code: 'APP_SERVER_TIMEOUT' });
  const waiting = client.waitFor(m => m.params?.turn?.id === 'correct', 100);
  process.stdout.write(JSON.stringify({ method: 'turn/completed', params: { turn: { id: 'correct' } } }) + '\n');
  assert.equal((await waiting).params.turn.id, 'correct');
  const closed = client.waitFor(() => false, 100); process.emit('exit', 3, null);
  await assert.rejects(closed, { code: 'APP_SERVER_CLOSED' });
  await client.close();
});
test('server completion with failed or missing tool results is not tool execution evidence', () => {
  assert.equal(Boolean(successfulToolItem({ type: 'commandExecution', id: 'synthetic-command', command: 'echo SYNTHETIC', cwd: projectRoot, commandActions: [], status: 'completed', exitCode: 0 })), true);
  for (const item of [
    { type: 'commandExecution', status: 'completed', exitCode: null },
    { type: 'commandExecution', status: 'completed', exitCode: 2 },
    { type: 'commandExecution', status: 'completed', exitCode: 0 },
    { type: 'mcpToolCall', status: 'completed', error: { message: 'failed' } },
    { type: 'mcpToolCall', status: 'completed', result: { isError: true } },
    { type: 'dynamicToolCall', status: 'completed', success: false },
    { type: 'fileChange', status: 'completed', changes: [] },
    { type: 'collabAgentToolCall', status: 'completed' }
  ]) assert.equal(successfulToolItem(item), false);
});
test('native preparation persists honest incomplete evidence and refuses redirected evidence directories', async t => {
  const temporaryRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'vem-host-boundary-'));
  assert.equal(path.dirname(await fs.realpath(temporaryRoot)), await fs.realpath(os.tmpdir()));
  t.after(async () => { await fs.rm(temporaryRoot, { recursive: true, force: true }); });
  const project = path.join(temporaryRoot, 'project'); const outside = path.join(temporaryRoot, 'outside');
  await fs.mkdir(project); await fs.mkdir(outside);
  const prepared = await executeHost({ projectRoot: project });
  assert.equal(prepared.status, 'prepared'); assert.equal(prepared.actualToolActions, 0); assert.equal(prepared.actualModel, null);
  const normalEvidence = path.join(project, 'evidence'); await fs.rename(normalEvidence, path.join(project, 'saved-evidence'));
  await fs.symlink(outside, normalEvidence, process.platform === 'win32' ? 'junction' : 'dir');
  await assert.rejects(executeHost({ projectRoot: project }), { code: 'UNSAFE_PATH' });
  assert.deepEqual(await fs.readdir(outside), []);
  await fs.unlink(normalEvidence);
});
