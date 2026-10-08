import fs from 'node:fs/promises';
import { writeSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createInterface } from 'node:readline';
import { randomUUID } from 'node:crypto';
import { atomicJSON, digest, fileReference, packageRoot, projectFile, ContractError, now } from './project-store.mjs';

const execFileAsync = promisify(execFile);
const MODEL = 'gpt-6.1-sol';
const EFFORT = 'ultra';
const SKILL = 'visual-exploration-moodboard';
const MAX_TRACE_BYTES = 128 * 1024 * 1024;
const ADAPTER_DIGEST = digest(await fs.readFile(new URL(import.meta.url)));
const normal = text => String(text).replace(/\r\n/g, '\n');
const normPath = value => String(value).replaceAll('\\\\', '\\').replaceAll('\\', '/').toLowerCase();

function strings(value, depth = 0) {
  if (depth > 8 || value == null) return [];
  if (typeof value === 'string') {
    try { const decoded = JSON.parse(value); if (decoded !== value) return [value, ...strings(decoded, depth + 1)]; } catch {}
    return [value];
  }
  if (Array.isArray(value)) return value.flatMap(x => strings(x, depth + 1));
  if (typeof value === 'object') return Object.values(value).flatMap(x => strings(x, depth + 1));
  return [];
}
// Only observed positive result schemas count. Unknown text, an empty result,
// or a successful outer code cell hiding a failed child is not a process result.
function toolResult(value, depth = 0) {
  if (depth > 8 || value == null) return { success: false, failure: false, text: [] };
  if (typeof value === 'string') {
    try { return toolResult(JSON.parse(value), depth + 1); }
    catch { return { success: false, failure: /^Script (?:failed|running)\b/.test(value), text: [] }; }
  }
  if (Array.isArray(value)) {
    if (!value.length || !value.every(x => x && ['input_text', 'text'].includes(x.type) && typeof x.text === 'string')) return { success: false, failure: false, text: [] };
    const complete = /^Script completed\r?\nWall time [^\n]+\nOutput:\r?\n/.test(value[0].text);
    const parts = value.slice(1).map(x => toolResult(x.text, depth + 1));
    return { success: complete && parts.some(x => x.success) && !parts.some(x => x.failure), failure: !complete || parts.some(x => x.failure), text: parts.filter(x => x.success).flatMap(x => x.text) };
  }
  if (typeof value !== 'object') return { success: false, failure: false, text: [] };
  const failure = value.isError === true || value.success === false || value.error != null || value.failure != null || (Object.hasOwn(value, 'exit_code') && value.exit_code !== 0);
  if (failure) return { success: false, failure: true, text: [] };
  if (value.exit_code === 0 && typeof value.output === 'string') return { success: true, failure: false, text: [value.output] };
  if (value.isError === false && Array.isArray(value.content) && value.content.length && value.content.every(x => x && typeof x.type === 'string')) return { success: true, failure: false, text: value.content.filter(x => x.type === 'text' && typeof x.text === 'string').map(x => x.text) };
  return { success: false, failure: false, text: [] };
}

// A deliberately limited literal parser, never eval. Dynamic expressions and
// paths mentioned in prose/comments remain unsupported evidence.
function tokens(source, shell = false) {
  const result = []; let i = 0;
  while (i < source.length) {
    if (/\s/.test(source[i])) { i++; continue; }
    if ((!shell && source.startsWith('//', i)) || (shell && source[i] === '#')) { while (i < source.length && source[i] !== '\n') i++; continue; }
    if (!shell && source.startsWith('/*', i)) { const end = source.indexOf('*/', i + 2); i = end < 0 ? source.length : end + 2; continue; }
    const quote = source[i];
    if (['"', "'", '`'].includes(quote)) {
      let value = ''; let dynamic = false; let closed = false; i++;
      while (i < source.length) {
        if (source[i] === quote) { i++; closed = true; break; }
        if (!shell && quote === '`' && source.startsWith('${', i)) dynamic = true;
        if (!shell && source[i] === '\\') {
          i++; const c = source[i++]; const escape = { n: '\n', r: '\r', t: '\t', b: '\b', f: '\f', v: '\v', '0': '\0' };
          if (c === 'u' && /^[0-9a-f]{4}$/i.test(source.slice(i, i + 4))) { value += String.fromCharCode(parseInt(source.slice(i, i + 4), 16)); i += 4; }
          else if (c === 'x' && /^[0-9a-f]{2}$/i.test(source.slice(i, i + 2))) { value += String.fromCharCode(parseInt(source.slice(i, i + 2), 16)); i += 2; }
          else value += escape[c] ?? c ?? '';
        } else value += source[i++];
      }
      result.push({ type: closed && !dynamic ? 'string' : 'unknown', value }); continue;
    }
    if (shell) {
      if (';|&()'.includes(source[i])) { result.push({ type: 'punct', value: source[i++] }); continue; }
      const start = i; while (i < source.length && !/\s/.test(source[i]) && !';|&()\'"`'.includes(source[i])) i++;
      result.push({ type: 'word', value: source.slice(start, i) }); continue;
    }
    const match = /^[\w$-]+/.exec(source.slice(i));
    if (match) { result.push({ type: 'word', value: match[0] }); i += match[0].length; }
    else result.push({ type: 'punct', value: source[i++] });
  }
  return result;
}
function objectLiterals(ts, start) {
  if (ts[start]?.value !== '{') return null;
  const result = {}; let depth = 1;
  for (let i = start + 1; i < ts.length && depth; i++) {
    if (ts[i].value === '{') depth++;
    if (ts[i].value === '}') depth--;
    if (depth === 1 && ['word', 'string'].includes(ts[i].type) && ts[i + 1]?.value === ':' && ts[i + 2]?.type === 'string') result[ts[i].value] = ts[i + 2].value;
  }
  return result;
}
function literalCalls(source, names) {
  const ts = tokens(source); const found = [];
  for (let i = 0; i < ts.length - 2; i++) if (ts[i].type === 'word' && names.includes(ts[i].value) && ts[i + 1].value === '(') {
    const object = objectLiterals(ts, i + 2);
    if (object) found.push({ name: ts[i].value, ...object });
  }
  return found;
}
function absolutePath(value, cwd) {
  if (typeof value !== 'string' || !value.trim() || /[\r\n\0]/.test(value)) return null;
  const windows = /^[a-z]:[\\/]|^\\\\/i.test(value) || /^[a-z]:[\\/]|^\\\\/i.test(cwd ?? '');
  const api = windows ? path.win32 : path.posix;
  if (!api.isAbsolute(value) && (!cwd || !api.isAbsolute(cwd))) return null;
  let resolved = api.resolve(cwd ?? '', value);
  try { resolved = realpathSync(resolved); } catch {}
  return windows ? resolved.replaceAll('\\', '/').toLowerCase().replace(/\/$/, '') : resolved.replace(/\/$/, '') || '/';
}
function samePath(a, b) { const aa = absolutePath(a); return aa != null && aa === absolutePath(b); }
function withinProject(candidate, root, cwd) { const a = absolutePath(candidate, cwd); const r = absolutePath(root); return a != null && r != null && (a === r || a.startsWith(r === '/' ? '/' : r + '/')); }
function shellDetails(command, cwd) {
  const ts = tokens(command, true); const paths = []; const reads = []; let nodeCode;
  // Accept real command arguments, not a project name inside echo/comment text.
  for (let start = 0; start < ts.length;) {
    let end = start; while (end < ts.length && ![';', '|', '&'].includes(ts[end].value)) end++;
    const part = ts.slice(start, end); const exe = part[0]?.value?.replaceAll('\\', '/').split('/').at(-1)?.toLowerCase();
    if (['get-content', 'cat', 'type'].includes(exe)) {
      let i = 1; if (['-literalpath', '-path'].includes(part[i]?.value.toLowerCase())) i++;
      if (part[i] && ['string', 'word'].includes(part[i].type) && !part[i].value.startsWith('-')) reads.push(part[i].value);
    }
    if (['node', 'node.exe'].includes(exe)) {
      const script = part.findIndex(x => /(?:^|[\\/])moodboard\.mjs$/.test(x.value));
      if (script >= 0 && ['start', 'resume', 'init', 'commit', 'render', 'export', 'check', 'serve', 'probe'].includes(part[script + 1]?.value)) {
        const flag = part.findIndex((x, i) => i > script && x.value === '--project');
        if (flag >= 0 && part[flag + 1]) paths.push(part[flag + 1].value);
      }
      const index = part.findIndex(x => ['-e', '--eval'].includes(x.value)); if (index >= 0 && part[index + 1]?.type === 'string') nodeCode = part[index + 1].value;
    }
    start = end + 1;
  }
  if (nodeCode) for (const call of literalCalls(nodeCode, ['executeHost', 'probeHost', 'createProject', 'loadProject', 'commitSnapshot', 'renderProject', 'exportProject', 'checkProject'])) if (call.projectRoot) paths.push(call.projectRoot);
  return { cwd, paths, reads };
}
function nativeCallDetails(item, context) {
  const body = callBody(item); let argumentsObject;
  try { argumentsObject = typeof item.arguments === 'object' ? item.arguments : JSON.parse(body); } catch {}
  if (argumentsObject && typeof argumentsObject === 'object' && !Array.isArray(argumentsObject) && typeof argumentsObject.cmd === 'string') return [shellDetails(argumentsObject.cmd, argumentsObject.workdir ?? argumentsObject.cwd ?? context?.cwd)];
  const calls = literalCalls(body, ['exec_command']);
  if (calls.length) return calls.filter(c => typeof c.cmd === 'string').map(c => shellDetails(c.cmd, c.workdir ?? c.cwd ?? context?.cwd));
  // The synthetic controls and older direct shell-call records use a raw cmd.
  if (/^(?:Get-Content|cat|type|node(?:\.exe)?)\s/i.test(body.trim())) return [shellDetails(body, context?.cwd)];
  return [];
}
function callBody(item) { return typeof item.arguments === 'string' ? item.arguments : typeof item.input === 'string' ? item.input : JSON.stringify(item.arguments ?? item.input ?? ''); }
function contextRuntime(context) { return { model: context?.model ?? null, effort: context?.effort ?? context?.reasoning_effort ?? null }; }
export function successfulToolItem(item) {
  if (!item || item.error || item.failure || item.success === false) return false;
  if (item.type === 'commandExecution') return item.status === 'completed' && item.exitCode === 0 && typeof item.id === 'string' && item.id && typeof item.command === 'string' && item.command.trim() && typeof item.cwd === 'string' && Array.isArray(item.commandActions);
  if (item.type === 'fileChange') return item.status === 'completed' && Array.isArray(item.changes) && item.changes.length > 0;
  if (item.type === 'mcpToolCall') return item.status === 'completed' && item.result?.isError !== true && (Array.isArray(item.result?.content) && item.result.content.length > 0 || item.result?.structuredContent != null && Object.keys(item.result.structuredContent).length > 0);
  if (item.type === 'dynamicToolCall') return item.status === 'completed' && item.success === true;
  if (item.type === 'webSearch') return Array.isArray(item.results) && item.results.length > 0;
  if (item.type === 'imageGeneration') return item.status === 'completed' && Boolean(item.result);
  return false;
}

// Parses observed local records only. A declared flag, a read command without its
// output, or matching prose in a user message never establishes Skill loading.
export function inspectNativeTrace(text, { skillText, skillPath, projectRoot, packagePath = packageRoot }) {
  const lines = text.split('\n');
  const calls = new Map(); const reads = []; const actions = []; const contexts = []; const warnings = [];
  let context = null; let meta = null; let sessions = 0; let ambiguous = false;
  for (let index = 0; index < lines.length; index++) {
    if (!lines[index].trim()) continue;
    let record;
    try { record = JSON.parse(lines[index]); }
    catch { if (index === lines.length - 1) { warnings.push('Incomplete final live-log line excluded'); continue; } throw new ContractError('INVALID_HOST_TRACE', `Invalid JSONL at line ${index + 1}`); }
    if (record.type === 'session_meta') { sessions++; meta = record.payload; context = null; calls.clear(); if (sessions > 1) ambiguous = true; }
    if (record.type === 'turn_context') {
      const payload = record.payload ?? {};
      const sameTurn = context && payload.turn_id && context.turn_id === payload.turn_id;
      if (!sameTurn || context.model !== payload.model || contextRuntime(context).effort !== contextRuntime(payload).effort) calls.clear();
      if (sameTurn && (context.model !== payload.model || contextRuntime(context).effort !== contextRuntime(payload).effort)) ambiguous = true;
      context = { ...payload, line: sameTurn ? context.line : index + 1, sessionId: meta?.id, turnKey: payload.turn_id ?? `context-${index + 1}` }; contexts.push(context);
    }
    if (record.type !== 'response_item') continue;
    const item = record.payload;
    const itemTurn = item?.internal_chat_message_metadata_passthrough?.turn_id;
    if (itemTurn && itemTurn !== context?.turn_id) continue;
    if (['function_call', 'custom_tool_call'].includes(item?.type) && typeof item.call_id === 'string') { if (calls.has(item.call_id)) ambiguous = true; calls.set(item.call_id, { item, line: index + 1, context, body: callBody(item) }); }
    if (!['function_call_output', 'custom_tool_call_output'].includes(item?.type)) continue;
    const call = calls.get(item.call_id);
    calls.delete(item.call_id);
    if (!call || !call.context || !context || call.context.sessionId !== context.sessionId || call.context.turnKey !== context.turnKey) continue;
    const result = toolResult(item.output); if (!result.success) continue;
    const details = nativeCallDetails(call.item, call.context);
    const referencesSkill = details.some(d => d.reads.some(p => samePath(absolutePath(p, d.cwd), skillPath) || (normPath(p).endsWith(`/${SKILL}/skill.md`) && samePath(absolutePath(p, d.cwd), skillPath))));
    const binding = { sessionId: context.sessionId, turnId: context.turn_id ?? null, turnKey: context.turnKey };
    if (referencesSkill && result.text.some(s => normal(s).includes(normal(skillText)))) reads.push({ line: call.line, outputLine: index + 1, contextLine: call.context.line, ...binding, ...contextRuntime(call.context) });
    const related = details.some(d => d.paths.length ? d.paths.some(p => withinProject(p, projectRoot, d.cwd)) : withinProject(d.cwd, projectRoot));
    if (related && /^(?:functions\.)?(?:exec|exec_command)$/.test(call.item.name ?? '')) actions.push({ line: call.line, outputLine: index + 1, name: call.item.name, contextLine: call.context.line, ...binding });
  }
  const read = !ambiguous && sessions === 1 && meta?.id ? [...reads].reverse().find(r => r.model === MODEL && r.effort === EFFORT && actions.some(a => a.sessionId === r.sessionId && a.turnKey === r.turnKey && a.line > r.outputLine)) : null;
  const linkedActions = read ? actions.filter(a => a.sessionId === read.sessionId && a.turnKey === read.turnKey && a.line > read.outputLine) : [];
  const missing = [];
  if (!reads.length) missing.push('Current full SKILL content was not observed in a successful, related read tool output');
  if (ambiguous || sessions !== 1 || !meta?.id) missing.push('Trace must have one identified session and unambiguous call/output runtime boundaries');
  if (!read) missing.push('No current Skill read and subsequent project/package tool result in the same Sol Ultra turn');
  return { status: read ? 'executed' : 'unverified', actualModel: read?.model ?? null, actualEffort: read?.effort ?? null, actualToolActions: linkedActions.length, skillRead: read ?? null, toolActions: linkedActions, contexts: contexts.map(c => ({ line: c.line, ...contextRuntime(c) })), session: { id: meta?.id ?? null, cliVersion: meta?.cli_version ?? meta?.codex_version ?? null, source: meta?.source ?? meta?.originator ?? null }, warnings, missing };
}

const RUNTIME_BOUNDARY = 'Server-resolved configuration and successful turn/tool events; not a captured turn_context, model self-report or provider cryptographic attestation';
function requireEvidence(condition, message) { if (!condition) throw new ContractError('INVALID_HOST_EVIDENCE', message, 2); }
function parseProtocol(text) {
  const lines = text.split('\n'); const events = [];
  for (let index = 0; index < lines.length; index++) {
    if (!lines[index].trim()) continue;
    let event; try { event = JSON.parse(lines[index]); } catch { throw new ContractError('INVALID_HOST_TRACE', `Invalid protocol JSONL at line ${index + 1}`, 2); }
    requireEvidence(event && ['client', 'server', 'stderr'].includes(event.direction) && (event.direction === 'stderr' ? typeof event.text === 'string' : event.message && typeof event.message === 'object' && !Array.isArray(event.message)), `Unsupported protocol event at line ${index + 1}`);
    events.push({ ...event, line: index + 1 });
  }
  requireEvidence(events.length > 0, 'Empty protocol trace'); return events;
}
function appToolRelated(item, root) {
  if (item.type === 'commandExecution') return withinProject(item.cwd, root);
  if (item.type === 'fileChange') return item.changes?.length > 0 && item.changes.every(change => withinProject(change.path, root));
  // No inferred project binding for opaque remote/dynamic tools.
  return false;
}
export function inspectAppServerTrace(text, { skillPath = path.join(packageRoot, 'SKILL.md'), projectRoot }) {
  const events = parseProtocol(text); const pending = new Map(); const pairs = [];
  for (const event of events) {
    const message = event.message; if (!message || !Object.hasOwn(message, 'id')) continue;
    if (event.direction === 'client' && typeof message.method === 'string') {
      requireEvidence(!pending.has(message.id) && !pairs.some(pair => pair.request.message.id === message.id), 'Duplicate client request id'); pending.set(message.id, event);
    } else if (event.direction === 'server' && !message.method) {
      const request = pending.get(message.id); requireEvidence(request, 'Response without a matching preceding request'); pending.delete(message.id);
      pairs.push({ request, response: event });
    }
  }
  const one = method => { const matches = pairs.filter(pair => pair.request.message.method === method); requireEvidence(events.filter(event => event.direction === 'client' && event.message?.method === method && Object.hasOwn(event.message, 'id')).length === 1 && matches.length === 1 && !matches[0].response.message.error && matches[0].response.message.result != null, `Missing/ambiguous successful ${method}`); return matches[0]; };
  const initialized = one('initialize'); const catalog = one('skills/list'); const thread = one('thread/start'); const turn = one('turn/start');
  requireEvidence(initialized.response.line < catalog.request.line && catalog.response.line < thread.request.line && thread.response.line < turn.request.line, 'Host requests cross initialization/runtime boundaries');
  requireEvidence(events.some(event => event.direction === 'client' && event.message?.method === 'initialized' && event.line > initialized.response.line && event.line < catalog.request.line), 'Missing initialized notification');
  const catalogParams = catalog.request.message.params;
  requireEvidence(catalogParams?.forceReload === true && catalogParams.cwds?.some(cwd => samePath(cwd, projectRoot)), 'Skill catalog is not refreshed for this project');
  const selected = catalog.response.message.result.data?.filter(entry => samePath(entry.cwd, projectRoot)).flatMap(entry => entry.skills ?? []).filter(skill => skill.name === SKILL && skill.enabled === true && samePath(skill.path, skillPath));
  requireEvidence(selected?.length === 1, 'Current Skill is absent or ambiguous in the refreshed host catalog');
  const threadParams = thread.request.message.params; const runtime = thread.response.message.result;
  requireEvidence(threadParams?.ephemeral === true && threadParams.model === MODEL && threadParams.config?.model_reasoning_effort === EFFORT && samePath(threadParams.cwd, projectRoot), 'Thread request does not bind the requested Sol Ultra project');
  requireEvidence(runtime.model === MODEL && runtime.reasoningEffort === EFFORT && typeof runtime.thread?.id === 'string' && runtime.thread.id && samePath(runtime.cwd ?? runtime.thread.cwd, projectRoot), 'Server-resolved runtime/project mismatch');
  const threadId = runtime.thread.id; const params = turn.request.message.params; const started = turn.response.message.result.turn;
  requireEvidence(params?.threadId === threadId && params.model === MODEL && params.effort === EFFORT && samePath(params.cwd, projectRoot), 'Turn request does not bind the actual thread/runtime/project');
  const skillInputs = params.input?.filter(input => input.type === 'skill');
  requireEvidence(skillInputs?.length === 1 && skillInputs[0].name === SKILL && samePath(skillInputs[0].path, skillPath), 'Actual turn lacks the current explicit Skill input');
  requireEvidence(typeof started?.id === 'string' && started.id && ['inProgress', 'completed'].includes(started.status) && !started.error, 'No actual successful turn start');
  const turnId = started.id;
  const completions = events.filter(event => event.direction === 'server' && event.message?.method === 'turn/completed' && event.message.params?.threadId === threadId && event.message.params?.turn?.id === turnId);
  requireEvidence(completions.length === 1 && completions[0].line > turn.response.line && completions[0].message.params.turn.status === 'completed' && !completions[0].message.params.turn.error, 'Actual turn did not complete successfully');
  const completion = completions[0];
  const itemEvents = events.filter(event => event.direction === 'server' && event.message?.method === 'item/completed' && event.message.params?.threadId === threadId && event.message.params?.turnId === turnId);
  requireEvidence(itemEvents.every(event => event.line > turn.response.line && event.line < completion.line), 'Completed item lies outside its active turn boundary');
  const itemIds = new Set();
  for (const event of itemEvents) { const id = event.message.params.item?.id; requireEvidence(typeof id === 'string' && id && !itemIds.has(id), 'Missing or repeated completed item id'); itemIds.add(id); }
  const items = itemEvents.map(event => event.message.params.item);
  const toolActions = items.filter(item => successfulToolItem(item) && appToolRelated(item, projectRoot));
  requireEvidence(toolActions.length > 0, 'No completed successful project tool action in the actual turn');
  const serverVersion = initialized.response.message.result.userAgent?.match(/\/(\d+\.\d+\.\d+(?:-[^\s]+)?)/)?.[1] ?? null;
  requireEvidence(serverVersion, 'Actual server version is missing from initialization');
  return { status: 'executed', actualModel: runtime.model, actualEffort: runtime.reasoningEffort, actualToolActions: toolActions.length, toolActions, threadId, turnId, turnStatus: completion.message.params.turn.status, serverVersion, runtimeEvidence: { kind: 'server-resolved-thread-runtime-and-completed-turn', runtimeResponseLine: thread.response.line, completedTurnLine: completion.line, boundary: RUNTIME_BOUNDARY }, finalMessages: items.filter(item => item.type === 'agentMessage').map(item => item.text) };
}

// Re-derive host execution from the exact bounded raw snapshot on every gate.
// Hashes bind bytes; local observations are not provider-signed attestations.
export async function validateHostEvidence(projectRoot, receipt) {
  projectRoot = await fs.realpath(projectRoot);
  requireEvidence(receipt?.schemaVersion === 1 && receipt.kind === 'host-execution' && receipt.status === 'executed', 'Unsupported/incomplete host receipt');
  requireEvidence(receipt.adapterDigest === ADAPTER_DIGEST && digest(await fs.readFile(new URL(import.meta.url))) === ADAPTER_DIGEST, 'Host receipt is not from the current adapter');
  const skillPath = path.join(packageRoot, 'SKILL.md'); const skillBytes = await fs.readFile(skillPath);
  requireEvidence(receipt.skillDigest === digest(skillBytes), 'Host receipt does not bind the current Skill');
  requireEvidence(receipt.rawTrace?.kind === 'host-raw-trace' && /^[a-f0-9]{64}$/.test(receipt.rawTrace.sha256), 'Missing typed raw host trace reference');
  const rawPath = await projectFile(projectRoot, receipt.rawTrace.path, { mustExist: true }); const stat = await fs.stat(rawPath);
  requireEvidence(stat.isFile() && stat.size > 0 && stat.size <= MAX_TRACE_BYTES, 'Raw host trace is empty, invalid or too large');
  const raw = await fs.readFile(rawPath); requireEvidence(raw.length <= MAX_TRACE_BYTES && digest(raw) === receipt.rawTrace.sha256, 'Raw host trace hash mismatch');
  requireEvidence(receipt.binary && /^[a-f0-9]{64}$/.test(receipt.binary.sha256), 'Missing actual host executable evidence');
  const recordedVersion = receipt.binary.version?.match(/\b\d+\.\d+\.\d+(?:-[^\s]+)?/)?.[0];
  let derived;
  if (receipt.host === 'native') {
    derived = inspectNativeTrace(raw.toString('utf8'), { skillText: skillBytes.toString('utf8'), skillPath, projectRoot });
    requireEvidence(derived.status === 'executed' && derived.warnings.length === 0 && derived.session.cliVersion === recordedVersion, 'Native raw trace lacks current positive same-session/turn execution');
    requireEvidence(receipt.source?.sha256 === digest(raw) && receipt.source.capturedBytes === raw.length, 'Native source snapshot binding mismatch');
    for (const field of ['status', 'actualModel', 'actualEffort', 'actualToolActions', 'session', 'skillRead', 'toolActions', 'contexts', 'warnings', 'missing']) requireEvidence(Object.hasOwn(receipt, field) && digest(receipt[field]) === digest(derived[field]), `Native receipt contradicts raw trace: ${field}`);
  } else if (receipt.host === 'codex-app-server') {
    derived = inspectAppServerTrace(raw.toString('utf8'), { skillPath, projectRoot });
    requireEvidence(derived.serverVersion === recordedVersion, 'Actual app-server and recorded executable version differ');
    for (const field of Object.keys(derived)) requireEvidence(Object.hasOwn(receipt, field) && digest(receipt[field]) === digest(derived[field]), `App-server receipt contradicts raw trace: ${field}`);
  } else requireEvidence(false, 'Unsupported host evidence type');
  // Invalid ordinary traces are rejected before invoking a referenced binary.
  const actualBinary = await binaryInfo(receipt.binary.path);
  requireEvidence(actualBinary.path === receipt.binary.path && actualBinary.sha256 === receipt.binary.sha256 && actualBinary.version === receipt.binary.version, 'Actual executable path/version/hash mismatch');
  return { status: derived.status, host: receipt.host, actualModel: derived.actualModel, actualEffort: derived.actualEffort, actualToolActions: derived.actualToolActions, threadId: derived.threadId ?? derived.session?.id, turnId: derived.turnId ?? derived.skillRead?.turnId, adapterDigest: ADAPTER_DIGEST, skillDigest: receipt.skillDigest, rawTrace: receipt.rawTrace, boundary: 'Re-derived local execution evidence; not creative quality, model understanding or provider cryptographic attestation' };
}

export class AppServerClient {
  constructor({ codexPath, cwd, timeoutMs = 30000, onTrace = () => {}, spawnImpl = spawn }) {
    this.timeoutMs = timeoutMs; this.onTrace = onTrace; this.pending = new Map(); this.messages = []; this.nextId = 1; this.closed = false;
    this.child = spawnImpl(codexPath, ['app-server'], { cwd, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
    this.reader = createInterface({ input: this.child.stdout });
    this.reader.on('line', line => {
      let message; try { message = JSON.parse(line); } catch { this.fail(new ContractError('APP_SERVER_PROTOCOL', 'Non-JSON stdout from app-server')); return; }
      this.onTrace({ at: now(), direction: 'server', message }); this.messages.push(message);
      if (Object.hasOwn(message, 'id') && !message.method) {
        const p = this.pending.get(message.id); if (!p) return;
        this.pending.delete(message.id); clearTimeout(p.timer);
        if (message.error) p.reject(new ContractError('APP_SERVER_RPC', JSON.stringify(message.error), 2)); else p.resolve(message.result);
      } else if (Object.hasOwn(message, 'id') && message.method) {
        // Never grant an approval, call a dynamic tool, or answer user input on
        // behalf of the user. The current allowed task must run without it.
        this.write({ id: message.id, error: { code: -32601, message: 'This adapter does not grant permissions or provide interactive tool responses' } });
      }
      this.notify?.();
    });
    this.child.stderr.on('data', chunk => this.onTrace({ at: now(), direction: 'stderr', text: String(chunk) }));
    this.child.on('error', e => this.fail(new ContractError('APP_SERVER_SPAWN', e.message, 2)));
    this.child.on('exit', (code, signal) => this.fail(new ContractError('APP_SERVER_CLOSED', `app-server exited (${code ?? signal})`, 2)));
  }
  fail(error) { this.failure = error; this.closed = true; for (const p of this.pending.values()) { clearTimeout(p.timer); p.reject(error); } this.pending.clear(); this.notify?.(); }
  write(message) { if (this.closed) throw this.failure ?? new ContractError('APP_SERVER_CLOSED', 'App-server is closed', 2); this.onTrace({ at: now(), direction: 'client', message }); this.child.stdin.write(`${JSON.stringify(message)}\n`); }
  request(method, params, timeoutMs = this.timeoutMs) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new ContractError('APP_SERVER_TIMEOUT', `${method} timed out; do not blindly retry a dispatched turn`, 2)); }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      try { this.write({ id, method, params }); } catch (e) { clearTimeout(timer); this.pending.delete(id); reject(e); }
    });
  }
  async waitFor(predicate, timeoutMs = this.timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    while (true) {
      const found = this.messages.find(predicate); if (found) return found;
      if (this.closed) throw this.failure;
      const remaining = deadline - Date.now(); if (remaining <= 0) throw new ContractError('APP_SERVER_TIMEOUT', 'Turn outcome is unknown; inspect the preserved trace before retrying', 2);
      await new Promise(resolve => { const timer = setTimeout(resolve, remaining); this.notify = () => { clearTimeout(timer); this.notify = null; resolve(); }; });
    }
  }
  async close() {
    this.reader.close(); this.child.stdin.end();
    if (!this.closed) { await new Promise(resolve => { const timer = setTimeout(() => { this.child.kill(); resolve(); }, 1000); this.child.once('exit', () => { clearTimeout(timer); resolve(); }); }); }
  }
}

async function binaryInfo(codexPath) {
  if (!codexPath || !path.isAbsolute(codexPath)) throw new ContractError('CODEX_PATH_REQUIRED', 'Pass the absolute path of the actual Codex executable', 2);
  const absolute = await fs.realpath(codexPath);
  if (!['codex', 'codex.exe'].includes(path.basename(absolute).toLowerCase())) throw new ContractError('CODEX_PATH_REQUIRED', 'The host must be the actual codex executable, not a shell shim or arbitrary program', 2);
  const bytes = await fs.readFile(absolute);
  const version = await execFileAsync(absolute, ['--version'], { windowsHide: true, timeout: 15000, maxBuffer: 1024 * 1024 });
  if (!/^codex-cli \d+\.\d+\.\d+(?:-[^\s]+)?$/.test(version.stdout.trim())) throw new ContractError('HOST_RUNTIME_MISMATCH', 'Actual executable did not identify as a supported Codex CLI', 2);
  return { path: absolute, sha256: digest(bytes), version: version.stdout.trim() };
}
async function setupSession({ projectRoot, codexPath, timeoutMs, events, onTrace }) {
  const binary = await binaryInfo(codexPath);
  const client = new AppServerClient({ codexPath: binary.path, cwd: projectRoot, timeoutMs, onTrace: event => { events.push(event); onTrace?.(event); } });
  try {
    const initialize = await client.request('initialize', { clientInfo: { name: 'visual_exploration_moodboard', title: 'Visual exploration moodboard', version: '1.0.0' }, capabilities: { experimentalApi: true } });
    client.write({ method: 'initialized', params: {} });
    const listed = await client.request('skills/list', { cwds: [projectRoot], forceReload: true });
    const skillPath = await fs.realpath(path.join(packageRoot, 'SKILL.md'));
    const candidates = listed?.data?.flatMap(entry => entry.skills ?? []) ?? [];
    let selected = null;
    for (const skill of candidates) {
      if (skill.name !== SKILL || skill.enabled !== true) continue;
      try { if (await fs.realpath(skill.path) === skillPath) { selected = skill; break; } } catch {}
    }
    return { client, binary, initialize, selected, skillPath, skillErrors: listed?.data?.flatMap(entry => entry.errors ?? []) ?? [] };
  } catch (e) { await client.close(); throw e; }
}
async function traceSink(projectRoot) {
  await fs.mkdir(await projectFile(projectRoot, 'evidence'), { recursive: true });
  const relative = `evidence/host-live-${randomUUID()}.jsonl`;
  const file = await fs.open(await projectFile(projectRoot, relative), 'wx'); let failure;
  return {
    relative,
    record(event) { if (failure) return; try { const bytes = Buffer.from(JSON.stringify(event) + '\n'); let offset = 0; while (offset < bytes.length) offset += writeSync(file.fd, bytes, offset, bytes.length - offset); } catch (e) { failure = e; } },
    async close() { try { await file.sync(); } catch (e) { failure ||= e; } finally { await file.close(); } return failure; }
  };
}
async function persist(projectRoot, receipt, eventsOrBytes, suffix, existingRawPath) {
  const token = randomUUID(); const rawName = `evidence/host-${token}.${suffix}`;
  await fs.mkdir(await projectFile(projectRoot, 'evidence'), { recursive: true });
  if (!existingRawPath) {
    const raw = typeof eventsOrBytes === 'string' || Buffer.isBuffer(eventsOrBytes) ? eventsOrBytes : eventsOrBytes.map(event => JSON.stringify(event)).join('\n') + '\n';
    await fs.writeFile(await projectFile(projectRoot, rawName), raw, { flag: 'wx' });
  }
  receipt.rawTrace = await fileReference(projectRoot, existingRawPath ?? rawName, { kind: 'host-raw-trace' });
  const name = `evidence/host-${token}.json`;
  await atomicJSON(await projectFile(projectRoot, name), receipt);
  return { ...receipt, evidence: await fileReference(projectRoot, name, { kind: receipt.kind }) };
}

// A real handshake/catalog probe. It deliberately does not create a model turn.
export async function probeHost({ projectRoot, codexPath, timeoutMs = 30000 }) {
  projectRoot = await fs.realpath(projectRoot);
  const events = []; let session; const sink = await traceSink(projectRoot);
  const receipt = { schemaVersion: 1, kind: 'host-probe', adapterDigest: ADAPTER_DIGEST, createdAt: now(), status: 'unverified', actualToolActions: 0, boundaries: 'Handshake/catalog only; no model turn or Skill understanding inferred' };
  try {
    session = await setupSession({ projectRoot, codexPath, timeoutMs, events, onTrace: event => sink.record(event) });
    Object.assign(receipt, { status: 'handshake', binary: session.binary, initialize: session.initialize, skillDiscovered: Boolean(session.selected), skillErrors: session.skillErrors });
  } catch (e) { Object.assign(receipt, { status: 'unsupported', error: { code: e.code ?? 'HOST_ERROR', message: e.message } }); }
  finally { if (session) await session.client.close(); const failure = await sink.close(); if (failure) { receipt.status = 'unverified'; receipt.traceFailure = failure.message; } }
  return persist(projectRoot, receipt, events, 'jsonl', sink.relative);
}

export async function executeHost({ projectRoot, host = 'native', codexPath, task, tracePath, timeoutMs = 900000 }) {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 2147483647) throw new ContractError('INVALID_HOST_TIMEOUT', 'timeoutMs must be positive and within the native timer range');
  projectRoot = await fs.realpath(projectRoot);
  await projectFile(projectRoot, 'evidence');
  const skillPath = path.join(packageRoot, 'SKILL.md'); const skillBytes = await fs.readFile(skillPath);
  const receipt = { schemaVersion: 1, kind: 'host-execution', adapterDigest: ADAPTER_DIGEST, createdAt: now(), host, skillDigest: digest(skillBytes), actualModel: null, actualEffort: null, actualToolActions: 0, status: 'prepared', boundaries: 'Observed Skill input and model/tool execution only; creative quality and task completion require separate review' };
  if (host === 'native') {
    if (!tracePath) return persist(projectRoot, { ...receipt, missing: ['Native preparation does not dispatch an agent; pass an authorized actual JSONL trace after native execution'] }, '', 'jsonl');
    const stat = await fs.stat(tracePath); if (stat.size > MAX_TRACE_BYTES) throw new ContractError('HOST_TRACE_TOO_LARGE', 'Import a bounded authorized source trace', 2);
    const raw = await fs.readFile(tracePath);
    if (raw.length > MAX_TRACE_BYTES) throw new ContractError('HOST_TRACE_TOO_LARGE', 'Source trace grew beyond the bounded import size', 2);
    const inspected = inspectNativeTrace(raw.toString('utf8'), { skillText: skillBytes.toString('utf8'), skillPath, projectRoot });
    Object.assign(receipt, inspected, { source: { path: await fs.realpath(tracePath), capturedBytes: raw.length, sha256: digest(raw), provenance: 'Explicit caller-selected authorized runtime log; no provider signature or model-understanding attestation inferred' } });
    if (codexPath) {
      receipt.binary = await binaryInfo(codexPath);
      const actualVersion = receipt.binary.version.match(/\b\d+\.\d+\.\d+(?:-[^\s]+)?/)?.[0];
      if (!inspected.session.cliVersion || actualVersion !== inspected.session.cliVersion) { receipt.status = 'unverified'; receipt.missing.push('Executable version is missing from, or differs from, source session'); }
    } else { receipt.status = 'unverified'; receipt.missing.push('Actual host executable path/version/hash not supplied'); }
    return persist(projectRoot, receipt, raw, 'jsonl');
  }
  if (host !== 'codex-app-server') throw new ContractError('HOST_UNSUPPORTED', `Unsupported host: ${host}`, 2);
  if (typeof task !== 'string' || !task.trim()) throw new ContractError('HOST_TASK_REQUIRED', 'Actual agent task is required');
  const events = []; let session; let threadId; let turnId; const sink = await traceSink(projectRoot);
  try {
    session = await setupSession({ projectRoot, codexPath, timeoutMs: Math.min(timeoutMs, 30000), events, onTrace: event => sink.record(event) });
    receipt.binary = session.binary;
    if (!session.selected) throw new ContractError('SKILL_NOT_DISCOVERED', 'Current enabled Skill is absent from the actual host catalog', 2);
    const thread = await session.client.request('thread/start', { cwd: projectRoot, model: MODEL, ephemeral: true, config: { model_reasoning_effort: EFFORT } });
    threadId = thread?.thread?.id; receipt.threadId = threadId;
    receipt.actualModel = thread?.model ?? null; receipt.actualEffort = thread?.reasoningEffort ?? null;
    if (!threadId || receipt.actualModel !== MODEL || receipt.actualEffort !== EFFORT) throw new ContractError('HOST_RUNTIME_MISMATCH', 'Server-resolved runtime does not match Sol Ultra', 2);
    if (digest(await fs.readFile(session.selected.path)) !== receipt.skillDigest) throw new ContractError('SKILL_VERSION_CHANGED', 'Skill changed before actual turn input', 2);
    const started = await session.client.request('turn/start', { threadId, model: MODEL, effort: EFFORT, cwd: projectRoot, input: [{ type: 'skill', name: SKILL, path: session.selected.path }, { type: 'text', text: task }] });
    turnId = started?.turn?.id; receipt.turnId = turnId;
    if (!turnId) throw new ContractError('HOST_TURN_MISSING', 'No actual turn id returned', 2);
    const completed = await session.client.waitFor(m => m.method === 'turn/completed' && m.params?.threadId === threadId && m.params?.turn?.id === turnId, timeoutMs);
    Object.assign(receipt, inspectAppServerTrace(events.map(event => JSON.stringify(event)).join('\n') + '\n', { skillPath, projectRoot }));
    if (digest(await fs.readFile(session.selected.path)) !== receipt.skillDigest) throw new ContractError('SKILL_VERSION_CHANGED', 'Skill changed during the actual turn', 2);
  } catch (e) {
    receipt.status = threadId || turnId ? 'unverified' : 'unsupported'; receipt.error = { code: e.code ?? 'HOST_ERROR', message: e.message };
    if (threadId && turnId && session && !session.client.closed) { try { await session.client.request('turn/interrupt', { threadId, turnId }, 5000); receipt.interruptRequested = true; } catch {} }
  } finally { if (session) await session.client.close(); const failure = await sink.close(); if (failure) { receipt.status = 'unverified'; receipt.traceFailure = failure.message; } }
  return persist(projectRoot, receipt, events, 'jsonl', sink.relative);
}
