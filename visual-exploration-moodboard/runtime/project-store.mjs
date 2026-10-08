import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import {decodePNG} from './media-contract.mjs';
import {validateAsset,verifyAsset} from './asset-contract.mjs';
import {dependencyIdentity} from './dependency-contract.mjs';

export const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const now = () => new Date().toISOString();
export class ContractError extends Error {
  constructor(code, message, exitCode = 1) { super(message); this.code = code; this.exitCode = exitCode; }
}
export function assert(condition, code, message) { if (!condition) throw new ContractError(code, message); }
export function canonical(value) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number') { assert(Number.isFinite(value), 'NON_FINITE', 'Non-finite number'); return JSON.stringify(value); }
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  assert(value && Object.getPrototypeOf(value) === Object.prototype, 'INVALID_JSON', 'Expected plain JSON value');
  return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
}
export const digest = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : canonical(value)).digest('hex');
export async function readJSON(filename) {
  let text;
  try { text = await fs.readFile(filename, 'utf8'); } catch (e) { throw new ContractError('MISSING_FILE', `${filename}: ${e.code}`, 2); }
  try { return JSON.parse(text.replace(/^\uFEFF/, '')); } catch { throw new ContractError('INVALID_JSON', `Invalid JSON: ${filename}`); }
}
export async function atomicJSON(filename, value) {
  canonical(value);
  await fs.mkdir(path.dirname(filename), { recursive: true });
  const temporary = `${filename}.${randomUUID()}.tmp`;
  try { await fs.writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { flag: 'wx' }); await fs.rename(temporary, filename); }
  finally { await fs.rm(temporary, { force: true }); }
}
export function validId(id) { return typeof id === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$/.test(id); }
export function inside(root, target) { const relative = path.relative(root, target); return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative)); }
export async function projectFile(root, relative, { mustExist = false } = {}) {
  assert(typeof relative === 'string' && relative.length > 0 && !relative.includes('\0') && !path.isAbsolute(relative) && !path.win32.isAbsolute(relative) && !/^[a-zA-Z]:/.test(relative), 'UNSAFE_PATH', 'Expected project-relative path');
  relative=relative.replaceAll('\\','/');
  const actualRoot = await fs.realpath(root);
  const absolute = path.resolve(actualRoot, relative);
  assert(inside(actualRoot, absolute), 'UNSAFE_PATH', `Path escapes project: ${relative}`);
  let current = absolute;
  while (true) {
    try { const real = await fs.realpath(current); assert(inside(actualRoot, real), 'UNSAFE_PATH', `Redirected path escapes project: ${relative}`); break; }
    catch (e) { if (e instanceof ContractError) throw e; if (e.code !== 'ENOENT') throw e; if (mustExist || current === actualRoot) throw new ContractError('MISSING_FILE', `Missing project file: ${relative}`, 2); current = path.dirname(current); }
  }
  return absolute;
}
export async function withProjectLock(root, callback) {
  const name = path.join(root, '.vem-write.lock');
  const token = randomUUID(); let handle;
  try { handle = await fs.open(name, 'wx'); } catch (e) { if (e.code === 'EEXIST') throw new ContractError('PROJECT_BUSY', 'Project is being written; retry after the active operation finishes', 2); throw e; }
  try { await handle.writeFile(JSON.stringify({ pid: process.pid, token, createdAt: now() })); return await callback(); }
  finally { await handle.close(); try { const lock = await readJSON(name); if (lock.token === token) await fs.rm(name); } catch {} }
}
const strings = x => Array.isArray(x) && x.length > 0 && x.every(v => typeof v === 'string' && v.trim());
export function validateStudyComposition(direction){
  const c=direction.studyComposition;if(c==null)return;
  assert(c&&Object.getPrototypeOf(c)===Object.prototype&&Object.keys(c).length===6&&Object.keys(c).every(k=>['baseAssetId','maskAssetId','opacity','blendMode','aspectRatio','purpose'].includes(k)),'COMPOSITION_INVALID','Composition requires the supported declarative fields');
  assert(validId(c.baseAssetId)&&validId(c.maskAssetId)&&c.baseAssetId!==c.maskAssetId&&Number.isFinite(c.opacity)&&c.opacity>0&&c.opacity<=1&&Number.isFinite(c.aspectRatio)&&c.aspectRatio>=.25&&c.aspectRatio<=4&&['multiply','screen','normal'].includes(c.blendMode)&&typeof c.purpose==='string'&&c.purpose.trim(),'COMPOSITION_INVALID','Composition settings must be finite, visible and purposeful');
  const assets=direction.assets||[];for(const id of [c.baseAssetId,c.maskAssetId])assert(assets.filter(a=>a.id===id).length===1,'COMPOSITION_ASSET_MISSING',`${direction.id}: composition asset ${id} is missing or ambiguous`);
  const base=assets.find(a=>a.id===c.baseAssetId),mask=assets.find(a=>a.id===c.maskAssetId);
  assert(base.url&&mask.url&&base.presentation==='composition-only'&&mask.presentation==='composition-only','COMPOSITION_ASSET_MISSING','Composition sources must be authorized embedded assets with composition-only presentation');
  assert(['subject-color-material','background-composite'].includes(base.operation?.type)&&base.operation.maskRef?.sha256===mask.sourceRef?.sha256&&base.operation.maskRef?.path===mask.sourceRef?.path,'COMPOSITION_AUTHORIZATION','Shader composition needs the matching affected-region authorization and mask');
  return c;
}
export function validateProject(project) {
  assert(project?.schemaVersion === 1, 'SCHEMA_VERSION', 'schemaVersion must be 1');
  assert(validId(project.project?.id), 'PROJECT_ID', 'Invalid project id');
  assert(typeof project.project.title === 'string' && project.project.title.trim(), 'PROJECT_TITLE', 'Project title required');
  assert(typeof project.brief?.decision === 'string' && project.brief.decision.trim(), 'DECISION_MISSING', 'Current decision required');
  assert(strings(project.brief.objectSuccess) && strings(project.brief.carrierSuccess), 'QUALITY_CONDITIONS_MISSING', 'Object and carrier success conditions are separately required');
  assert(Array.isArray(project.brief.locks) && Array.isArray(project.brief.openVariables), 'LOCKS_MISSING', 'Locks and open variables must be explicit arrays');
  assert(project.benchmarks && validId(project.benchmarks.revision) && Array.isArray(project.benchmarks.object) && Array.isArray(project.benchmarks.carrier), 'BENCHMARK_CONTRACT_MISSING', 'Separate, versioned benchmark collections required');
  assert(Array.isArray(project.directions) && project.directions.length > 0, 'DIRECTIONS_MISSING', 'At least one draft direction required');
  const ids = new Set();
  for (const direction of project.directions) {
    assert(validId(direction.id) && !ids.has(direction.id), 'DIRECTION_ID', `Invalid/duplicate direction id: ${direction.id}`); ids.add(direction.id);
    assert(typeof direction.title === 'string' && direction.title.trim() && validId(direction.recipeId), 'DIRECTION_INVALID', `Title and recipeId required: ${direction.id}`);
    assert(direction.parameters && !Array.isArray(direction.parameters) && typeof direction.parameters === 'object', 'PARAMETERS_MISSING', `parameters required: ${direction.id}`);
    canonical(direction.parameters);
    for (const key of ['question', 'mechanism', 'expected', 'failure']) assert(typeof direction.hypothesis?.[key] === 'string' && direction.hypothesis[key].trim(), 'HYPOTHESIS_MISSING', `${direction.id}: hypothesis.${key}`);
    for (const key of ['adopt', 'exclude', 'unproven']) assert(strings(direction.handoff?.[key]), 'HANDOFF_MISSING', `${direction.id}: handoff.${key}`);
    for (const target of ['object', 'carrier']) assert(direction.quality?.[target] && ['unverified', 'needs_revision', 'supported'].includes(direction.quality[target].status), 'QUALITY_STATUS_MISSING', `${direction.id}: quality.${target}`);
    for(const asset of direction.assets||[])validateAsset(asset);
    validateStudyComposition(direction);
  }
  return project;
}
export async function loadProject(root) { return validateProject(await readJSON(await projectFile(root,'project.json',{mustExist:true}))); }
export async function createProject(root, input) {
  validateProject(input); await fs.mkdir(root, { recursive: true });
  return withProjectLock(root, async () => {
    try { await fs.access(path.join(root, 'project.json')); throw new ContractError('PROJECT_EXISTS', 'Existing project is never overwritten; use resume'); } catch (e) { if (e instanceof ContractError || e.code !== 'ENOENT') throw e; }
    const project = structuredClone(input);
    project.project.createdAt ||= now(); project.revision = 1;
    for (const d of project.directions) { delete d.snapshot; delete d.poster; delete d.compositionPoster; delete d.render; d.status = 'draft'; }
    await atomicJSON(path.join(root, 'project.json'), project);
    const baseline = { schemaVersion: 1, kind: 'project-baseline', createdAt: now(), projectIdentityDigest:digest(project.project),initialProject:structuredClone(project),brief: project.brief, benchmarks: project.benchmarks, initialProjectDigest: digest(project), scope: 'Pre-production declaration; not proof that benchmarks were actually observed' };
    await atomicJSON(await projectFile(root, 'evidence/baseline-1.json'), baseline);
    project.baselineRef=await fileReference(root,'evidence/baseline-1.json');
    await atomicJSON(await projectFile(root,'project.json'),project);
    return project;
  });
}
export async function shaderModule() { return import('./shader-adapter.mjs'); }
export async function recipeFor(id) {
  const shader = await shaderModule();
  const catalog = shader.recipeCatalog;
  const recipe = Array.isArray(catalog) ? catalog.find(x => x.id === id) : catalog?.[id];
  assert(recipe, 'UNKNOWN_RECIPE', `Unsupported recipe: ${id}`);
  return recipe;
}
export async function engineDigest() {
  const files = ['runtime/board.html', 'runtime/board.css', 'runtime/board.mjs', 'runtime/shader-adapter.mjs', 'runtime/browser-tools.mjs','runtime/server.mjs','runtime/project-store.mjs','runtime/asset-contract.mjs','runtime/media-contract.mjs','runtime/dependency-contract.mjs','runtime/render-profile.mjs', 'assets/recipes/catalog.mjs', 'assets/recipes/original-fields.mjs', 'package-lock.json'];
  const records = [];
  for (const file of files) { try { records.push([file, digest(await fs.readFile(path.join(packageRoot, file)))]); } catch { throw new ContractError('BUILD_INCOMPLETE', `Missing runtime file: ${file}`, 2); } }
  records.push(['actualInstalledDependencies',await dependencyIdentity()]);return digest(records);
}
export async function commitSnapshot(root, { directionId, parameters, timeSeconds }) {
  assert(Number.isFinite(timeSeconds) && timeSeconds >= 0 && timeSeconds <= 600, 'INVALID_TIME', 'timeSeconds must be finite, 0..600');
  const shader = await shaderModule();
  return withProjectLock(root, async () => {
    const project = await loadProject(root); const direction = project.directions.find(x => x.id === directionId);
    assert(direction, 'UNKNOWN_DIRECTION', `Unknown direction: ${directionId}`);
    const validParameters = shader.validateParameters(direction.recipeId, parameters);
    const params = validParameters && !Array.isArray(validParameters) && typeof validParameters === 'object' ? validParameters : parameters;
    const recipe = await recipeFor(direction.recipeId); const currentEngine = await engineDigest();
    await validateBaseline(root,project,{requireChange:false});
    const assets = direction.assets || [];
    for (const asset of assets) await verifyAsset(root,asset,verifyFileReference);
    const {authorityRenderProfile}=await import('./render-profile.mjs');
    const state = { schemaVersion: 1, directionId, recipeId: direction.recipeId, recipeDigest: digest(recipe), engineDigest: currentEngine, renderProfile:authorityRenderProfile, baselineDigest:digest(project.baselineRef),compositionDigest:digest(direction.studyComposition||null),parameters: params, timeSeconds, initialState: 'stateless-reset', inputs: [], hypothesisDigest: digest(direction.hypothesis), handoffDigest: digest(direction.handoff), briefDigest: digest(project.brief), benchmarkRevision: project.benchmarks.revision, benchmarkDigest:digest(project.benchmarks),assetsDigest:digest(assets),narrativeDigest:digest(narrative(direction)),projectIdentityDigest:digest(project.project) };
    const hash = digest(state);
    if (direction.snapshot?.digest === hash) {await validateSavedSnapshot(root,project,direction,currentEngine);return { snapshot: direction.snapshot, project };}
    const snapshot = { ...state, id: `${directionId}-${hash.slice(0, 16)}`, digest: hash, revision: (direction.snapshot?.revision || 0) + 1, committedAt: now() };
    await atomicJSON(await projectFile(root, `snapshots/${snapshot.id}.json`), snapshot);
    direction.snapshot = snapshot; direction.parameters = params; direction.poster = null; delete direction.compositionPoster; delete direction.render;
    direction.quality = { object: { status: 'unverified', evidence: [], issues: ['Snapshot changed; affected review requires current evidence'] }, carrier: { status: 'unverified', evidence: [], issues: ['Snapshot changed; affected review requires current evidence'] } };
    direction.status = 'draft'; project.revision++;
    await atomicJSON(path.join(root, 'project.json'), project);
    return { snapshot, project };
  });
}
export async function fileReference(root, filename, extra = {}) {
  const absolute = await projectFile(root, filename, { mustExist: true });
  return { ...extra, path: filename.replaceAll('\\', '/'), sha256: digest(await fs.readFile(absolute)) };
}
export async function verifyFileReference(root, ref) {
  assert(ref && typeof ref.path === 'string' && /^[a-f0-9]{64}$/.test(ref.sha256 || ''), 'EVIDENCE_REFERENCE_INVALID', 'Hash-bound evidence reference required');
  const absolute = await projectFile(root, ref.path, { mustExist: true }); const bytes = await fs.readFile(absolute);
  assert(bytes.length>0,'EMPTY_EVIDENCE',`Empty file: ${ref.path}`);
  assert(digest(bytes) === ref.sha256, 'STALE_EVIDENCE', `Changed evidence: ${ref.path}`); return {absolute, bytes, sha256: ref.sha256};
}
export async function verifyReference(root, ref) { const checked = await verifyFileReference(root, ref); return readJSON(checked.absolute); }
export async function attachRender(root, directionId, receiptRef, posterPath, compositionPath) {
  return withProjectLock(root, async () => {
    const project = await loadProject(root); const direction = project.directions.find(x => x.id === directionId);
    assert(direction?.snapshot, 'SNAPSHOT_MISSING', 'Commit a valid snapshot before rendering');
    await validateSavedSnapshot(root,project,direction);
    const receipt = await verifyReference(root, receiptRef);
    assert(receipt.snapshotDigest === direction.snapshot.digest && receipt.engineDigest === await engineDigest(), 'STALE_RENDER', 'Render does not match current snapshot/engine');
    assert(receipt.gpu?.device && receipt.pixels?.nonTransparent > 0, 'NO_GPU_OUTPUT', 'Actual GPU and visible pixel evidence required');
    await validateRender(root,direction,receipt,await engineDigest());
    assert(receipt.output.path === posterPath, 'POSTER_MISMATCH', 'Poster must be the rendered output');
    if(direction.studyComposition){assert(receipt.composition?.output.path===compositionPath,'COMPOSITION_MISMATCH','Composition poster must be the actual captured output');direction.compositionPoster=`/media/${compositionPath.split('/').map(encodeURIComponent).join('/')}`;}else delete direction.compositionPoster;
    direction.poster = `/media/${posterPath.split('/').map(encodeURIComponent).join('/')}`; direction.render = receiptRef; project.revision++;
    await atomicJSON(path.join(root, 'project.json'), project); return project;
  });
}
export async function validateSavedSnapshot(root,project,direction,currentEngine) {
  assert(direction.snapshot,'SNAPSHOT_MISSING',`${direction.id}: snapshot missing`);
  const s=direction.snapshot;const {id,digest:stored,revision,committedAt,...state}=s;
  assert(s.directionId===direction.id&&s.recipeId===direction.recipeId&&canonical(s.parameters)===canonical(direction.parameters),'SNAPSHOT_BINDING_MISMATCH',`${direction.id}: snapshot is bound to another direction, recipe or parameters`);
  assert(digest(state)===stored&&s.engineDigest===(currentEngine||await engineDigest())&&s.recipeDigest===digest(await recipeFor(direction.recipeId)),'STALE_SNAPSHOT',`${direction.id}: snapshot/recipe/engine changed`);
  assert(s.hypothesisDigest===digest(direction.hypothesis)&&s.handoffDigest===digest(direction.handoff)&&s.briefDigest===digest(project.brief)&&s.benchmarkRevision===project.benchmarks.revision&&s.benchmarkDigest===digest(project.benchmarks)&&s.assetsDigest===digest(direction.assets||[]),'STALE_CREATIVE_CONTRACT',`${direction.id}: creative/brief/benchmark/assets changed`);
  assert(s.narrativeDigest===digest(narrative(direction))&&s.projectIdentityDigest===digest(project.project),'STALE_NARRATIVE',`${direction.id}: visible narrative or project identity changed`);
  assert(s.compositionDigest===digest(direction.studyComposition||null),'STALE_COMPOSITION',`${direction.id}: subject/field composition changed`);
  const {authorityRenderProfile}=await import('./render-profile.mjs');assert(canonical(s.renderProfile)===canonical(authorityRenderProfile),'RENDER_PROFILE_MISMATCH',`${direction.id}: committed capture settings differ`);assert(s.baselineDigest===digest(project.baselineRef),'STALE_BASELINE',`${direction.id}: frozen baseline reference changed`);
  for(const asset of direction.assets||[]) {await verifyAsset(root,asset,verifyFileReference);if(asset.url)assert(asset.url===`/media/${asset.sourceRef.path.split('/').map(encodeURIComponent).join('/')}`,'ASSET_URL_MISMATCH',`${direction.id}: displayed asset differs from sourceRef`);}
  const saved=await readJSON(await projectFile(root,`snapshots/${s.id}.json`,{mustExist:true}));assert(canonical(saved)===canonical(s),'SNAPSHOT_MISMATCH',`${direction.id}: manifest differs from saved snapshot`);
  (await shaderModule()).validateParameters(direction.recipeId,s.parameters);return s.id;
}
export async function checkProject(root, { scope = 'technical' } = {}) {
  assert(['technical','delivery'].includes(scope),'CHECK_SCOPE','Only technical or delivery checks are supported');
  const findings = []; let project;
  const check = async (code, fn) => { try { const detail = await fn(); findings.push({ code, status: 'PASS', detail }); } catch (e) { findings.push({ code: e.code || code, status: e.exitCode === 2 ? 'UNVERIFIED' : 'FAIL', detail: e.message }); } };
  await check('PROJECT_CONTRACT', async () => { project = await loadProject(root); return 'Separate quality conditions, direction hypotheses and handoff present'; });
  if (!project) return result();
  let currentEngine;await check('RUNTIME_DEPENDENCIES',async()=>{currentEngine=await engineDigest();return currentEngine;});if(!currentEngine)return result();
  for (const direction of project.directions) {
    await check(`SNAPSHOT_${direction.id}`,()=>validateSavedSnapshot(root,project,direction,currentEngine));
    await check(`RENDER_${direction.id}`, async () => {
      const r = await validateSavedRender(root,direction,currentEngine);return r.output.path;
    });
  }
  if (scope === 'delivery') {
    await check('FROZEN_BASELINE',async()=>{const baseline=await validateBaseline(root,project);for(const d of project.directions)assert(Date.parse(baseline.createdAt)<=Date.parse(d.snapshot?.committedAt),'BASELINE_ORDER','Baseline must precede committed production');return project.baselineRef.path;});
    await check('HOST_EXECUTION', async () => {
      assert(project.host?.evidence, 'HOST_EXECUTION_MISSING', 'Actual skill input and model/tool execution evidence missing');
      const host = await verifyReference(root, project.host.evidence);
      const {validateHostEvidence}=await import('./host-adapter.mjs');return validateHostEvidence(root,host);
    });
    await check('QUALITY_AND_INDEPENDENCE', async () => {
      assert(project.review?.evidence, 'REVIEW_MISSING', 'Current independent review missing');
      const review = await verifyReference(root, project.review.evidence);
      assert(review.schemaVersion===1&&review.kind==='independent-art-review','REVIEW_SCHEMA','A structured independent art review is required');
      assert(review.initialReview && review.reviewer && review.participatedInProduction === false && review.independentOrderEvidence, 'REVIEW_INDEPENDENCE_MISSING', 'Sealed initial review/order evidence required');
      await verifyFileReference(root, review.initialReview);const order=await verifyReference(root, review.independentOrderEvidence);
      assert(order.schemaVersion===1&&order.kind==='independent-review-order'&&order.reviewer===review.reviewer&&order.participatedInProduction===false&&order.executionConclusionsSeenBeforeInitialReview===false&&order.initialReview?.sha256===review.initialReview.sha256,'REVIEW_ORDER_INVALID','Order evidence must bind the sealed first review and declared independence');
      assert(Number.isFinite(Date.parse(order.acknowledgedAt))&&Date.parse(order.acknowledgedAt)<=Date.parse(order.initialSealedAt)&&(!order.comparisonOpenedAt||Date.parse(order.initialSealedAt)<=Date.parse(order.comparisonOpenedAt)),'REVIEW_ORDER_INVALID','Review acknowledgement/seal/comparison order is invalid');
      assert(order.ackRef&&order.runtimeRef,'REVIEW_ORDER_INVALID','Actual acknowledgement and runtime references required');await verifyFileReference(root,order.ackRef);await verifyFileReference(root,order.runtimeRef);
      assert(review.engineDigest === currentEngine, 'STALE_REVIEW', 'Review engine changed');
      assert(Array.isArray(review.renderBindings)&&canonical(review.renderBindings)===canonical(await renderBindings(root,project)),'STALE_REVIEW','Review must bind actual authoritative render receipts, output pixels and capture profile');
      for (const d of project.directions) {
        const inspected = review.directions?.find(x => x.id === d.id);
        assert(inspected?.snapshotDigest === d.snapshot?.digest, 'STALE_REVIEW', `${d.id}: review snapshot differs`);
        for (const target of ['object', 'carrier']) {
          assert(inspected[target]?.status === 'supported' && strings(inspected[target].basis) && (!inspected[target].criticalIssues?.length), 'QUALITY_NOT_SUPPORTED', `${d.id}: ${target} lacks competitive actual evidence or has unresolved issues`);
        }
      }
      assert(review.benchmarkRevision === project.benchmarks.revision && !review.unresolvedCritical?.length, 'REVIEW_INCOMPLETE', 'Benchmark mismatch or critical issues remain');
      return 'Separate professional judgments are recorded; this checker does not certify their aesthetic truth';
    });
    await check('BENCHMARK_OBSERVATIONS', async () => {
      for (const target of ['object', 'carrier']) {
        assert(project.benchmarks[target].length > 0, 'BENCHMARKS_MISSING', `${target}: relevant benchmarks required`);
        for (const b of project.benchmarks[target]) { assert(b.observed===true&&b.observationRef, 'BENCHMARK_UNOBSERVED', `${b.id}: actual observation missing`); await verifyFileReference(root, b.observationRef); }
      }
      return 'Hash-bound observations present; professional relevance requires actual review';
    });
    await check('PNG_EXPORT', async () => { assert(project.exports?.png, 'EXPORT_MISSING', 'Current PNG overview missing'); const receipt = await verifyReference(root, project.exports.png); assert(receipt.schemaVersion===1&&receipt.kind==='png-overview'&&receipt.browser?.version,'EXPORT_SCHEMA','Actual browser export receipt required');assert(receipt.engineDigest === currentEngine && canonical(receipt.snapshots) === canonical(project.directions.map(d => [d.id, d.snapshot?.digest])), 'STALE_EXPORT', 'PNG overview does not match current snapshots');assert(Array.isArray(receipt.renderBindings)&&canonical(receipt.renderBindings)===canonical(await renderBindings(root,project)),'STALE_EXPORT','Authoritative poster outputs/settings changed after export'); const decoded=decodePNG((await verifyFileReference(root, receipt.output)).bytes);assert(decoded.nonTransparent>0,'EMPTY_EXPORT','PNG overview is empty');return receipt.output.path; });
  }
  return result();
  function result() { const status = findings.some(f => f.status === 'FAIL') ? 'FAIL' : findings.some(f => f.status === 'UNVERIFIED') ? 'UNVERIFIED' : 'PASS'; return { schemaVersion: 1, checkedAt: now(), scope, status, findings, boundaries: { aestheticCertification: false, userAcceptance: 'not_inferred', independentMediaReview: 'only_as_referenced' } }; }
}
function narrative(direction){return {title:direction.title,subtitle:direction.subtitle||'',description:direction.description||'',claim:direction.claim||'',caption:direction.caption||'',palette:direction.palette||[]};}
export async function validateSavedRender(root,direction,currentEngine){
  assert(direction.render,'RENDER_MISSING',`${direction.id}: actual render missing`);
  const r=await verifyReference(root,direction.render);await validateRender(root,direction,r,currentEngine||await engineDigest());
  assert(direction.poster===`/media/${r.output.path.split('/').map(encodeURIComponent).join('/')}`,'POSTER_MISMATCH',`${direction.id}: visible poster differs from checked output`);
  if(direction.studyComposition)assert(direction.compositionPoster===`/media/${r.composition.output.path.split('/').map(encodeURIComponent).join('/')}`,'COMPOSITION_MISMATCH',`${direction.id}: visible object frame differs from checked output`);
  return r;
}
async function validateRender(root,direction,r,currentEngine){
  assert(r.schemaVersion===1&&r.kind==='actual-shader-frame'&&r.directionId===direction.id&&r.browser?.version,'RENDER_SCHEMA','A real direction-specific browser frame receipt is required');
  assert(r.snapshotDigest===direction.snapshot?.digest&&r.engineDigest===currentEngine,'STALE_RENDER',`${direction.id}: render stale`);
  const gpu=r.gpu?.observation;assert(r.gpu?.device===true&&gpu?.deviceCreated===true&&gpu.status==='ready'&&gpu.drawCount>0&&gpu.currentFrameReadbackVerified===true,'NO_GPU_OUTPUT','Actual current GPU draw/readback required');
  const {authorityRenderProfile,assertAuthorityRenderProfile,assertRenderEnvironment}=await import('./render-profile.mjs');assertAuthorityRenderProfile(r.renderProfile);assertRenderEnvironment(r.renderProfile,r.renderEnvironment,r.pixels);assert(canonical(r.renderProfile)===canonical(direction.snapshot.renderProfile)&&canonical(r.renderProfile)===canonical(authorityRenderProfile),'RENDER_PROFILE_MISMATCH','Frame capture settings differ from committed settings');
  const image=decodePNG((await verifyFileReference(root,r.output)).bytes);
  assert(image.nonTransparent>0&&image.width===r.pixels?.width&&image.height===r.pixels?.height&&image.pixelDigest===r.pixels?.decodedDigest&&image.pixelDigest===gpu.lastReadback?.pixelDigest,'GPU_PIXEL_MISMATCH','Decoded poster does not match the captured GPU pixels');
  if(direction.studyComposition){const c=r.composition,scene=direction.studyComposition;assert(c?.enabled===true&&c.sourceDigest===digest(scene),'COMPOSITION_MISMATCH','Captured object must include the saved authorized field composition');
    const o=c.observation,a=c.assets;assert(o?.enabled===true&&o.decoded===true&&!o.failure&&['baseAssetId','maskAssetId','opacity','blendMode','aspectRatio','purpose'].every(k=>o[k]===scene[k]),'COMPOSITION_MISMATCH','Observed composition differs from the saved enabled/decoded contract');
    const roles=[['base',scene.baseAssetId],['mask',scene.maskAssetId]],{decodeAssetDimensions}=await import('./browser-tools.mjs'),dimensions=await decodeAssetDimensions(root,roles.map(([,id])=>direction.assets.find(x=>x.id===id)));
    for(const [index,[role,id]]of roles.entries()){const observed=a?.[role],asset=direction.assets.find(x=>x.id===id),actual=dimensions[index];assert(Number.isSafeInteger(observed?.width)&&observed.width>0&&Number.isSafeInteger(observed?.height)&&observed.height>0&&typeof observed.src==='string','COMPOSITION_MISMATCH','Observed composition image did not decode');assert(observed.width===actual.width&&observed.height===actual.height,'COMPOSITION_MISMATCH','Observed composition dimensions differ from the independently decoded bound source');const url=new URL(observed.src);assert(url.pathname===asset.url&&!url.search&&!url.hash&&url.protocol==='http:'&&['127.0.0.1','localhost'].includes(url.hostname),'COMPOSITION_MISMATCH','Observed composition source differs from the authorized asset');}
    assert(a.styles?.display!=='none'&&a.styles?.visibility!=='hidden'&&a.styles?.opacity===scene.opacity&&a.styles?.blendMode===scene.blendMode&&typeof a.styles?.maskImage==='string'&&a.styles.maskImage.includes(a.mask.src),'COMPOSITION_MISMATCH','Observed masked field is hidden or has conflicting styles');
    const object=decodePNG((await verifyFileReference(root,c.output)).bytes);assert(object.nonTransparent>0&&object.width===c.pixels?.width&&object.height===c.pixels?.height&&object.pixelDigest===c.pixels?.decodedDigest,'COMPOSITION_PIXEL_MISMATCH','Decoded subject/field frame differs from its actual capture');assert(Number.isFinite(a.stage?.width)&&a.stage.width>0&&Number.isFinite(a.stage?.height)&&a.stage.height>0&&Math.abs(a.stage.width/object.width-1)<.01&&Math.abs(a.stage.height/object.height-1)<.01&&Math.abs(a.stage.width/a.stage.height-scene.aspectRatio)<.01,'COMPOSITION_MISMATCH','Actual stage dimensions differ from the captured subject frame');
  }else assert(!r.composition,'COMPOSITION_MISMATCH','Unexpected subject composition');return image;
}
export async function snapshotStates(root,project){const current=await engineDigest(),states={};for(const d of project.directions){try{await validateSavedSnapshot(root,project,d,current);states[d.id]={status:'current'};}catch(e){states[d.id]={status:'stale',code:e.code||'SNAPSHOT_INVALID',message:e.message};}}return states;}
export async function validateBaseline(root,project,{requireChange=true}={}){
  assert(project.baselineRef,'BASELINE_MISSING','Frozen pre-production baseline reference required');const b=await verifyReference(root,project.baselineRef);
  assert(b.schemaVersion===1&&b.kind==='project-baseline'&&b.initialProject&&b.brief&&b.benchmarks&&Number.isFinite(Date.parse(b.createdAt)),'BASELINE_INVALID','Baseline requires the actual hash-bound initial project');
  validateProject(b.initialProject);assert(b.initialProject.revision===1&&b.initialProject.directions.every(d=>d.status==='draft'&&!d.snapshot&&!d.render&&!d.poster&&!d.compositionPoster),'BASELINE_INVALID','Baseline must contain a complete actual initial draft project');
  assert(digest(b.initialProject)===b.initialProjectDigest&&digest(b.initialProject.project)===b.projectIdentityDigest&&b.projectIdentityDigest===digest(project.project),'BASELINE_BINDING_MISMATCH','Frozen baseline belongs to another project or its initial content differs');
  assert(canonical(b.initialProject.brief)===canonical(b.brief)&&canonical(b.initialProject.benchmarks)===canonical(b.benchmarks),'BASELINE_BINDING_MISMATCH','Frozen brief/benchmark differs from its initial project');
  if(b.originalBaselineRef){const original=await verifyReference(root,b.originalBaselineRef);assert(original.initialProjectDigest===b.initialProjectDigest&&canonical(original.brief)===canonical(b.brief)&&canonical(original.benchmarks)===canonical(b.benchmarks)&&original.createdAt===b.createdAt,'BASELINE_BINDING_MISMATCH','Upgraded baseline does not preserve its historical frozen source');}
  if(requireChange&&(canonical(b.brief)!==canonical(project.brief)||canonical(b.benchmarks)!==canonical(project.benchmarks))){let found=false;for(const ref of project.baselineChanges||[]){const change=await verifyReference(root,ref);if(change.schemaVersion===1&&change.kind==='baseline-change'&&change.baselineSha256===project.baselineRef.sha256&&change.previousBriefDigest===digest(b.brief)&&change.currentBriefDigest===digest(project.brief)&&change.previousBenchmarkDigest===digest(b.benchmarks)&&change.currentBenchmarkDigest===digest(project.benchmarks)&&typeof change.reason==='string'&&change.reason.trim()&&strings(change.affectedScope)&&Date.parse(change.changedAt)>=Date.parse(b.createdAt))found=true;}assert(found,'BASELINE_CHANGE_MISSING','Current brief/benchmarks need a hash-bound change reason and affected scope');}
  return b;
}
export async function renderBindings(root,project){const {renderBinding}=await import('./render-profile.mjs');const rows=[];for(const d of project.directions){assert(d.render,'RENDER_MISSING',`${d.id}: actual render missing`);const r=await verifyReference(root,d.render);rows.push(renderBinding(r,d.render));}return rows;}
