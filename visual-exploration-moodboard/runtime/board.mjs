import {createShaderStudy, validateParameters} from './shader-adapter.mjs';

// The page is the viewing surface. Committed project/snapshot authority remains
// in the local service; browser drafts never silently replace saved evidence.
const $ = (id) => document.getElementById(id);
const clone = (value) => value == null ? value : JSON.parse(JSON.stringify(value));
const asArray = (value) => Array.isArray(value) ? value : value == null ? [] : [value];
const textOf = (value) => typeof value === 'string' ? value : value == null ? '' : typeof value === 'object' ? (value.description || value.text || value.label || value.title || JSON.stringify(value)) : String(value);
const sameParameters = (a, b) => {
  const keys = [...new Set([...Object.keys(a || {}), ...Object.keys(b || {})])].sort();
  return keys.every((key) => JSON.stringify(a?.[key]) === JSON.stringify(b?.[key]));
};
const mediaURL = (value) => {
  if (typeof value !== 'string' || !value) return null;
  try { const url = new URL(value, location.href); return url.origin === location.origin && /^https?:$/.test(url.protocol) ? url.href : null; } catch { return null; }
};
const sourceURL = (value) => {
  try { const url = new URL(value, location.href); return /^https?:$/.test(url.protocol) ? url.href : null; } catch { return null; }
};
const make = (tag, className, text) => {const node = document.createElement(tag); if (className) node.className = className; if (text != null) node.textContent = textOf(text); return node;};
function originalImageLink(url, name) {const link = make('a', 'fullres-link', `查看原图 · ${name}`); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; return link;}
const setText = (id, value) => {$(id).textContent = textOf(value);};
const numbered = (index) => String(index + 1).padStart(2, '0');
const state = {project: null, directionId: null, recipe: null, parameters: {}, timeSeconds: 0, paused: true, reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches, snapshot: null, gpu: null, failure: null, composition: null, dirty: false, saving: false, loading: false, exporting: false};
const drafts = new Map();
let renderer = null;
let queue = Promise.resolve();
let toastTimer;
let lastAnnouncedFailure = '';
let printWasPlaying = false;
let exportFrozen = false;

function currentDirection() { return state.project?.directions.find((item) => item.id === state.directionId); }
const visibleAssets = (direction) => asArray(direction.assets).filter((asset) => asset.presentation !== 'composition-only');
const viewingPoster = (direction) => direction.studyComposition ? direction.compositionPoster : direction.poster;
function compositionError(code, message) {return Object.assign(new Error(message), {code});}
function resetComposition() {
  state.composition = null; const stage = $('shader-stage'), canvas = $('study-canvas');
  stage.classList.remove('has-composition'); stage.style.removeProperty('aspect-ratio');
  for (const key of ['opacity', 'mix-blend-mode', 'mask-image', 'mask-size', 'mask-position', 'mask-repeat', 'mask-mode', '-webkit-mask-image', '-webkit-mask-size', '-webkit-mask-position', '-webkit-mask-repeat']) canvas.style.removeProperty(key);
  for (const id of ['composition-base', 'composition-mask-source']) {$(id).hidden = true; $(id).removeAttribute('src');}
  $('composition-controls').hidden = true;
}
async function decodeCompositionImage(img, url, assetId) {
  img.src = url; let timer;
  try {
    await Promise.race([img.decode(), new Promise((_, reject) => {timer = setTimeout(() => reject(new Error('图像解码超过15秒')), 15000);})]);
    if (!img.naturalWidth || !img.naturalHeight) throw new Error('图像尺寸为空');
  } catch (error) {throw compositionError('COMPOSITION_ASSET_DECODE_FAILED', `合成素材「${assetId}」加载或解码失败：${error.message}`);}
  finally {clearTimeout(timer);}
}
async function loadComposition(direction) {
  const config = direction.studyComposition; if (!config) return;
  state.composition = {enabled: true, baseAssetId: config.baseAssetId, maskAssetId: config.maskAssetId, decoded: false, status: 'loading', opacity: config.opacity, blendMode: config.blendMode, aspectRatio: config.aspectRatio, purpose: config.purpose, failure: null};
  $('composition-controls').hidden = false;
  try {
    if (typeof config.baseAssetId !== 'string' || typeof config.maskAssetId !== 'string' || !Number.isFinite(config.opacity) || config.opacity < 0 || config.opacity > 1 || !['multiply', 'screen', 'normal'].includes(config.blendMode) || !Number.isFinite(config.aspectRatio) || config.aspectRatio <= 0 || typeof config.purpose !== 'string' || !config.purpose.trim()) throw compositionError('COMPOSITION_CONTRACT_INVALID', '主体与光场的合成定义无效。');
    const asset = (id) => {
      const matches = asArray(direction.assets).filter((item) => item.id === id);
      const url = matches.length === 1 ? mediaURL(matches[0].url) : null;
      if (!url || !new URL(url).pathname.startsWith('/media/')) throw compositionError('COMPOSITION_ASSET_INVALID', `合成素材「${id}」必须引用本方向唯一的本地工程素材。`);
      return {asset: matches[0], url};
    };
    const base = asset(config.baseAssetId), mask = asset(config.maskAssetId), stage = $('shader-stage'), canvas = $('study-canvas');
    stage.classList.add('has-composition'); stage.style.aspectRatio = String(config.aspectRatio);
    canvas.style.opacity = String(config.opacity); canvas.style.mixBlendMode = config.blendMode;
    canvas.style.maskImage = `url(${JSON.stringify(mask.url)})`; canvas.style.webkitMaskImage = canvas.style.maskImage;
    canvas.style.maskSize = canvas.style.webkitMaskSize = '100% 100%'; canvas.style.maskPosition = canvas.style.webkitMaskPosition = 'center'; canvas.style.maskRepeat = canvas.style.webkitMaskRepeat = 'no-repeat'; canvas.style.maskMode = 'luminance';
    const img = $('composition-base'); img.alt = base.asset.alt || base.asset.caption || `${direction.title} · 主体研究`; img.hidden = false;
    setText('composition-purpose', config.purpose);
    const decoded = await Promise.allSettled([decodeCompositionImage(img, base.url, config.baseAssetId), decodeCompositionImage($('composition-mask-source'), mask.url, config.maskAssetId)]);
    const failed = decoded.find((item) => item.status === 'rejected'); if (failed) throw failed.reason;
    state.composition.decoded = true; state.composition.status = 'ready';
  } catch (error) {
    state.composition.status = 'failed'; state.composition.failure = {code: error.code || 'COMPOSITION_ASSET_DECODE_FAILED', message: error.message};
    throw error;
  }
}
function requireComposition() {
  if (!state.composition) return;
  if (state.composition.failure || !state.composition.decoded) throw compositionError('COMPOSITION_UNAVAILABLE', '主体或遮罩尚未成功解码，不能导出完整合成研究。');
  if (!state.composition.enabled) throw compositionError('COMPOSITION_DISABLED', '当前只看主体原件。请打开「光场介入」后再导出已保存研究。');
}
async function setCompositionEnabled(enabled) {
  if (typeof enabled !== 'boolean') throw new Error('光场开关必须为布尔值。');
  if (!state.composition) throw new Error('当前方向没有声明主体与光场合成。');
  if (state.exporting) throw new Error('正在导出当前已保存状态。');
  if (state.composition.failure || !state.composition.decoded) throw new Error('主体或遮罩不可用，光场合成尚未成立。');
  state.composition.enabled = enabled; updatePlayback(); return getState();
}
function synchronize() {
  if (renderer) {
    const actual = renderer.getState();
    if (Number.isFinite(actual.timeSeconds)) state.timeSeconds = actual.timeSeconds;
    if (typeof actual.paused === 'boolean') state.paused = actual.paused;
    state.gpu = clone(actual.gpu);
    if (actual.failure) state.failure = clone(actual.failure);
    if (actual.gpu?.status === 'failed' && !state.failure) state.failure = {code: 'GPU_FAILED', message: 'GPU 绘制失效。'};
  }
  state.dirty = state.project?._snapshotStates?.[state.directionId]?.status==='stale' || !state.snapshot || !sameParameters(state.parameters, state.snapshot.parameters) || Math.abs(state.timeSeconds - (state.snapshot.timeSeconds ?? 0)) > 0.015;
  return state;
}
function getState() {
  synchronize();
  return {directionId: state.directionId, projectId: state.project?.project?.id ?? null, parameters: clone(state.parameters), timeSeconds: state.timeSeconds, dirty: state.dirty, snapshot: clone(state.snapshot), gpu: clone(state.gpu), failure: clone(state.failure), composition: clone(state.composition), paused: state.paused, reducedMotion: state.reducedMotion, loading: state.loading, saving: state.saving, exporting: state.exporting, recipeId: state.recipe?.id || state.recipe?.recipeId || null, viewport: {width: innerWidth, height: innerHeight, dpr: devicePixelRatio}, deliveryStatus: state.failure || state.gpu?.status !== 'ready' || state.composition?.enabled === false ? 'partial' : 'unverified'};
}
function enqueue(operation) {const result = queue.then(operation); queue = result.catch(() => {}); return result;}
function toast(message) {clearTimeout(toastTimer); setText('toast', message); $('toast').hidden = false; toastTimer = setTimeout(() => {$('toast').hidden = true;}, 5200);}
function reportError(error, fallback = '操作未完成') {toast(`${fallback}：${error?.message || error}`); console.error('[VEM]', error);}
function act(operation) {Promise.resolve().then(operation).catch((error) => reportError(error));}
async function requestJSON(url, options = {}) {
  const response = await fetch(url, {...options, headers: {'Content-Type': 'application/json', ...(options.headers || {})}, cache: 'no-store'});
  let data; try {data = await response.json();} catch {throw new Error(`本地服务返回无效数据（${response.status}）`);}
  if (!response.ok) throw new Error(textOf(data.error?.message || data.error || data.message || `HTTP ${response.status}`));
  return data;
}
function validateProject(project) {
  if (project?.schemaVersion !== 1 || !project.project?.id || !Array.isArray(project.directions) || !project.directions.length) throw new Error('项目结构无效，或没有可浏览的方向。');
  const ids = new Set(); for (const direction of project.directions) {if (!direction.id || ids.has(direction.id) || !direction.recipeId) throw new Error('方向 ID 重复、缺失或未指定 Shader 配方。'); ids.add(direction.id);}
  return project;
}
function populateList(id, values, emptyText) {
  const element = $(id); element.replaceChildren();
  for (const value of asArray(values)) element.append(make('li', '', value));
  if (!element.childElementCount) element.append(make('li', 'empty-note', emptyText));
}
function renderProject() {
  const project = state.project.project;
  document.title = `${project.title || '视觉探索'} · 视觉研究`;
  setText('project-title', project.title); setText('project-subtitle', project.subtitle);
  setText('medium-label', project.medium || '视觉研究'); setText('masthead-context', project.title);
  setText('decision', state.project.brief?.decision || '当前项目尚未声明决策问题。');
  setText('footer-title', project.title); setText('direction-count', String(state.project.directions.length).padStart(2, '0'));
  renderDirectionNav();
}
function renderDirectionNav() {
  const nav = $('direction-nav'); nav.replaceChildren();
  state.project.directions.forEach((direction, index) => {
    const button = make('button', 'direction-tab'); button.type = 'button'; button.dataset.directionId = direction.id;
    button.setAttribute('aria-current', String(direction.id === state.directionId));
    button.append(make('span', 'tab-number', numbered(index)), make('span', '', direction.title || direction.id));
    const dot = make('span', 'tab-state'); dot.setAttribute('aria-hidden', 'true'); button.append(dot);
    button.addEventListener('click', () => act(() => api.setDirection(direction.id)));
    nav.append(button);
  });
}
function renderAssets(direction) {
  const strip = $('asset-strip'); strip.replaceChildren();
  const assets=visibleAssets(direction),sequenceRoles=['entrance','threshold','center'];
  const sequence=sequenceRoles.every(role=>assets.filter(a=>a.role===role).length===1)?make('div','asset-sequence'):null;
  if(sequence){sequence.append(make('h3','asset-sequence-title','入口 → 屏端 → 中央'));strip.append(sequence);}
  const ordered=sequence?[...sequenceRoles.map(role=>assets.find(a=>a.role===role)),...assets.filter(a=>!sequenceRoles.includes(a.role))]:assets;
  ordered.forEach((asset) => {
    const figure = make('figure');figure.dataset.role=asset.role||''; const wrap = make('div', 'asset-image-wrap');
    const url = mediaURL(asset.url); const caption = make('figcaption');
    caption.append(make('span', 'asset-role', roleLabels[asset.role] || asset.role || '素材角色未声明'), make('span', '', asset.caption || asset.title || '未附素材说明'));
    if (url) {
      const img = make('img'); img.src = url; img.alt = asset.alt || asset.caption || asset.title || '项目素材'; img.loading = 'lazy'; img.decoding = 'async';
      img.addEventListener('error', () => {wrap.replaceChildren(make('p', 'asset-error', '素材未能载入。此项尚未验证。'));}); wrap.append(img);
      caption.append(originalImageLink(url, asset.title || `${direction.title} / ${asset.role || asset.id || '素材'}`));
      caption.append(inspectButton([{url,title:`${direction.title} / ${roleLabels[asset.role]||asset.role||'画面'}`,caption:asset.caption}]));
    } else if(asset.rights?.status==='reference-only'&&sourceURL(asset.sourceURL)) {const link=make('a','','查看外部参考来源');link.href=sourceURL(asset.sourceURL);link.target='_blank';link.rel='noopener noreferrer';wrap.append(link);}
    else wrap.append(make('p', 'asset-error', '素材地址不在当前本地工程，未载入。'));
    figure.append(wrap, caption); (sequence&&sequenceRoles.includes(asset.role)?sequence:strip).append(figure);
  });
  $('asset-section').hidden = !strip.childElementCount;
}
function renderDirection() {
  const direction = currentDirection(); const index = state.project.directions.indexOf(direction);
  setText('direction-number', numbered(index)); setText('stage-corner', numbered(index)); setText('direction-subtitle', direction.subtitle || 'DIRECTION STUDY');
  setText('direction-title', direction.title); setText('direction-claim', direction.claim); setText('direction-description', direction.description);
  const hypothesis = direction.hypothesis || {};
  setText('hypothesis-question', hypothesis.question || '尚未声明可观察的视觉问题。');
  setText('hypothesis-mechanism', hypothesis.mechanism || '尚未声明表现机制。');
  setText('hypothesis-expected', hypothesis.expected || '预期观看结果尚待明确。');
  setText('hypothesis-failure', hypothesis.failure ? `需要修订的反例：${textOf(hypothesis.failure)}` : '关键失败依据尚待明确。');
  populateList('handoff-adopt', direction.handoff?.adopt, '采用关系尚未形成结论。');
  populateList('handoff-exclude', direction.handoff?.exclude, '排除继承范围尚未声明。');
  populateList('handoff-unproven', direction.handoff?.unproven, '尚未声明未证明项；这不代表全部已验证。');
  const palette = $('palette'); palette.replaceChildren();
  asArray(direction.palette).forEach((color) => {
    const value = typeof color === 'string' ? color : color.color || color.value;
    if (!value || !CSS.supports('color', value)) return;
    const swatch = make('span', 'palette-swatch'); swatch.style.setProperty('--swatch', value); swatch.title = typeof color === 'string' ? color : `${color.label || ''} ${value}`; palette.append(swatch);
  });
  const posterURL = mediaURL(direction.poster);
  const poster = $('stage-poster'); poster.hidden = !posterURL || !!direction.studyComposition;
  if (posterURL) {poster.src = posterURL; poster.alt = `${direction.title} · 已提交快照静态图`;} else poster.removeAttribute('src');
  setText('study-caption', direction.caption || direction.claim || direction.description);
  renderAssets(direction); renderDirectionNav(); updatePlayback();
}
function parameterContract(recipe) { return recipe?.parameters || {}; }
function renderParameters() {
  const container = $('parameter-controls'); container.replaceChildren();
  const definitions = parameterContract(state.recipe);
  for (const [key, definition] of Object.entries(definitions)) {
    if (!definition || typeof definition !== 'object') continue;
    const control = make('div', 'parameter-control');
    const heading = make('div', 'parameter-heading'); const label = make('label', '', definition.label || key); const id = `parameter-${key}`; label.htmlFor = id;
    const output = make('output', '', state.parameters[key]); output.htmlFor = id; output.dataset.parameterOutput = key; heading.append(label, output);
    control.append(heading, make('p', '', definition.meaning || definition.description || '此参数的艺术意义尚未说明。'));
    let input;
    if (definition.type === 'number' || typeof definition.default === 'number') {
      input = make('input'); input.type = 'range'; input.min = definition.min ?? 0; input.max = definition.max ?? 1; input.step = definition.step ?? .01; input.value = state.parameters[key] ?? definition.default;
    } else if (definition.type === 'color') {input = make('input'); input.type = 'color'; input.value = state.parameters[key] ?? definition.default;}
    else if (Array.isArray(definition.options) || Array.isArray(definition.enum)) {
      input = make('select'); for (const option of (definition.options || definition.enum)) {const el = make('option', '', option.label || option); el.value = option.value ?? option; input.append(el);} input.value = state.parameters[key] ?? definition.default;
    } else {control.append(make('p', '', '本参数暂不提供网页编辑；当前值仍绑定在研究快照。')); container.append(control); continue;}
    input.id = id; input.dataset.parameter = key; input.setAttribute('aria-describedby', `${id}-meaning`); control.querySelector('p').id = `${id}-meaning`;
    input.addEventListener('input', () => {const value = input.type === 'range' ? Number(input.value) : input.value; output.value = String(value); act(() => api.setParameters({[key]: value}));});
    control.append(input); container.append(control);
  }
  if (!container.childElementCount) container.append(make('p', 'direction-description', '本方向未开放网页参数。'));
}
function updateParameterValues() {
  document.querySelectorAll('[data-parameter]').forEach((input) => {const value = state.parameters[input.dataset.parameter]; if (value != null) input.value = value;});
  document.querySelectorAll('[data-parameter-output]').forEach((output) => {output.value = String(state.parameters[output.dataset.parameterOutput] ?? '');});
}
function updatePlayback() {
  synchronize();
  const failed = !!state.failure; const unavailable = failed || state.loading || !renderer;
  const composition = state.composition; const compositionHidden = composition?.enabled === false;
  $('shader-stage').setAttribute('aria-busy', String(state.loading));
  $('play-toggle').disabled = unavailable; $('restart').disabled = unavailable; $('timeline').disabled = unavailable;
  $('save-snapshot').disabled = unavailable || state.saving || state.exporting;
  $('export-png').disabled = unavailable || state.saving || state.exporting || compositionHidden;
  $('export-pdf').disabled = unavailable || state.saving || state.exporting || compositionHidden;
  $('composition-enabled').checked = composition?.enabled !== false;
  $('composition-enabled').disabled = unavailable || state.exporting || !composition?.decoded;
  setText('composition-status', compositionHidden ? '只看主体原件 · 打开光场后可导出' : composition ? (composition.decoded ? '主体与真实光场共同观看' : '主体与遮罩正在解码') : '');
  $('restore').disabled = state.loading || state.saving;
  $('reduced-motion').checked = state.reducedMotion;
  setText('play-icon', state.paused ? '▷' : 'Ⅱ'); setText('play-label', state.paused ? '播放' : '暂停');
  $('play-toggle').setAttribute('aria-label', state.paused ? '播放动态研究' : '暂停动态研究');
  $('play-toggle').setAttribute('aria-pressed', String(!state.paused));
  const duration = Math.max(12, Number(state.recipe?.durationSeconds || state.recipe?.loopSeconds || 12), state.timeSeconds);
  $('timeline').max = String(duration);
  if (document.activeElement !== $('timeline')) $('timeline').value = String(state.timeSeconds);
  setText('time-display', `${state.timeSeconds.toFixed(2).padStart(5, '0')} s`);
  setText('stage-mode', state.loading ? '正在建立画面' : failed ? 'PARTIAL / 研究不可用' : compositionHidden ? '主体原件 / 光场暂隐藏' : state.gpu?.status === 'ready' ? (composition ? (state.paused ? '主体 × 光场 / 静止选帧' : '主体 × 光场 / 实时观看') : (state.paused ? 'SHADER STUDY / 静止选帧' : 'SHADER STUDY / 实时观看')) : 'GPU 绘制尚待核实');
  $('stage-failure').hidden = !failed;
  $('study-canvas').style.visibility = failed || compositionHidden ? 'hidden' : 'visible';
  if (failed) {setText('stage-failure-message', state.failure.message || state.failure.code); if (lastAnnouncedFailure !== state.failure.code) {lastAnnouncedFailure = state.failure.code; toast(`动态研究不可用：${state.failure.message || state.failure.code}`);}}
  const snapshot = state.snapshot;
  setText('snapshot-caption', snapshot ? `保存版本 ${snapshot.revision ?? '—'} · ${Number(snapshot.timeSeconds||0).toFixed(2)} s` : '尚无保存快照');
  const stale=state.project?._snapshotStates?.[state.directionId];
  const status = state.saving ? '正在保存此参数与选帧…' : state.loading ? '正在载入此方向…' : failed ? '当前为部分可浏览状态；动态与导出尚未成立。' : stale?.status==='stale' ? `保存版本已失效：${stale.message}。请重新保存并生成海报。` : state.dirty ? (state.paused ? '有未保存变化。对照仍使用已保存快照。' : '正在观看动态。保存会冻结当前帧与参数。') : `已保存 · ${state.timeSeconds.toFixed(2)} 秒。保存不代表批准。`;
  if ($('save-state').textContent !== status) setText('save-state', status);
  $('save-state').dataset.dirty = String(state.dirty);
}
async function loadDirection(id) {
  const direction = state.project.directions.find((item) => item.id === id);
  if (!direction) throw new Error(`没有方向：${id}`);
  if (renderer) {synchronize(); drafts.set(state.directionId, {parameters: clone(state.parameters), timeSeconds: state.timeSeconds, paused: state.paused}); await renderer.destroy(); renderer = null;}
  state.directionId = id; state.snapshot = clone(direction.snapshot || null); state.failure = null; state.gpu = null; state.recipe = null; state.loading = true; state.paused = true; resetComposition();
  const draft = drafts.get(id); state.parameters = clone(draft?.parameters || direction.snapshot?.parameters || direction.parameters || {}); state.timeSeconds = draft?.timeSeconds ?? direction.snapshot?.timeSeconds ?? 0;
  renderDirection(); $('parameter-controls').replaceChildren(); $('print-frame').hidden = true;
  const canvas = $('study-canvas'); canvas.width = Math.max(1, canvas.clientWidth); canvas.height = Math.max(1, canvas.clientHeight);
  try {
    await loadComposition(direction);
    canvas.width = Math.max(1, canvas.clientWidth); canvas.height = Math.max(1, canvas.clientHeight);
    const result = await requestJSON(`/api/recipe/${encodeURIComponent(direction.recipeId)}`); state.recipe = result.recipe || result;
    state.parameters = validateParameters(direction.recipeId, state.parameters);
    renderParameters();
    renderer = await createShaderStudy(canvas, state.recipe, state.parameters);
    await renderer.pause(); await renderer.renderAt(state.timeSeconds);
    synchronize();
    if (!state.failure && !state.reducedMotion && (draft ? !draft.paused : true) && !exportFrozen) await renderer.resume();
    synchronize();
    recordObservation('direction-loaded');
  } catch (error) {
    state.failure = {code: error.code || 'STUDY_INITIALIZATION_FAILED', message: error.message || String(error)};
  } finally {state.loading = false; updatePlayback();}
  return getState();
}
async function setParameters(parameters) {
  if (!renderer || !state.recipe || state.loading) throw new Error('当前方向尚未可编辑。');
  if (!parameters || typeof parameters !== 'object' || Array.isArray(parameters)) throw new Error('参数必须为对象。');
  const next = validateParameters(currentDirection().recipeId, {...state.parameters, ...parameters});
  synchronize(); await renderer.pause(); synchronize(); state.paused = true;
  await renderer.setParameters(next); state.parameters = clone(next);
  await renderer.renderAt(state.timeSeconds); synchronize(); updateParameterValues(); updatePlayback(); return getState();
}
async function pause() {if (renderer) await renderer.pause(); synchronize(); updatePlayback(); return getState();}
async function resume() {
  if (!renderer || state.failure) throw new Error('当前 Shader 动态不可用。');
  if (exportFrozen) throw new Error('正在导出当前已保存状态。');
  if (state.reducedMotion) {state.reducedMotion = false; $('reduced-motion').checked = false;}
  await renderer.resume(); synchronize(); updatePlayback(); return getState();
}
async function seek(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) throw new Error('选帧时间必须是非负有限秒数。');
  if (!renderer || state.failure) throw new Error('当前 Shader 不支持选帧。');
  await renderer.pause(); await renderer.renderAt(seconds); state.timeSeconds = seconds; state.paused = true; synchronize(); updatePlayback(); return getState();
}
async function commitSnapshot() {
  if (!renderer || state.failure || state.loading) throw new Error('Shader 尚未可用，不能提交当前研究。');
  await renderer.pause(); synchronize(); await renderer.renderAt(state.timeSeconds); synchronize();
  if (state.gpu?.status !== 'ready' || !state.gpu.deviceCreated || !(state.gpu.drawCount > 0) || !state.gpu.currentFrameReadbackVerified) throw new Error('缺少当前 GPU 实际绘制与读回证据，未保存为有效快照。');
  state.saving = true; updatePlayback();
  try {
    const result = await requestJSON('/api/snapshot', {method: 'POST', body: JSON.stringify({directionId: state.directionId, parameters: state.parameters, timeSeconds: state.timeSeconds})});
    if (!result.snapshot || !result.project) throw new Error('保存响应缺少快照或更新后的项目。');
    state.project = validateProject(result.project); state.snapshot = clone(result.snapshot);
    state.parameters = clone(result.snapshot.parameters); state.timeSeconds = result.snapshot.timeSeconds;
    drafts.delete(state.directionId); renderDirection(); renderComparison();
    toast('已保存当前参数与选帧。原有海报及审阅证据按版本重新核对。');
    return getState();
  } finally {state.saving = false; updatePlayback();}
}
function snapshotFigure(direction, index, allowSelect = true) {
  const article = make('article', 'compare-item'); const image = make('div', 'compare-image');
  if (direction.studyComposition) {article.classList.add('has-composition'); image.style.aspectRatio = String(direction.studyComposition.aspectRatio);}
  const heading = make('header', 'compare-direction-heading'); heading.append(make('h3', '', `${numbered(index)} / ${direction.title || direction.id}`), make('p', '', direction.claim)); article.append(heading);
  const assets = make('div', 'compare-assets');
  for (const asset of visibleAssets(direction)) {
    const figure = make('figure', 'compare-asset'); const url = mediaURL(asset.url);
    if(!asset.url)continue;
    if (url) {const img = make('img'); img.src = url; img.alt = asset.alt || asset.caption || asset.title || '方向主体研究'; img.loading = 'eager'; figure.append(img);}
    else figure.append(make('p', 'asset-error', '方向主体研究未能载入。'));
    const caption = make('figcaption', '', asset.caption || asset.title || asset.role || '方向主体研究');
    if (url) caption.append(originalImageLink(url, asset.title || `${direction.title} / ${asset.role || asset.id || '素材'}`));
    figure.append(caption); assets.append(figure);
  }
  const poster = mediaURL(viewingPoster(direction));
  if (poster && direction.snapshot) {
    const img = make('img', 'compare-poster'); img.src = poster; img.alt = `${direction.title} · 快照 ${direction.snapshot.id}`; img.loading = 'eager';
    img.addEventListener('error', () => image.replaceChildren(make('p', 'compare-missing', '已保存海报未能载入；此方向画面尚未验证。'))); image.append(img);
  } else image.append(make('p', 'compare-missing', direction.snapshot ? '当前快照尚无对应静态图。请先从当前快照生成总览。' : '此方向尚未提交快照，不能作为同版画面对照。'));
  article.append(image);
  if (poster && direction.snapshot) article.append(originalImageLink(poster, `${direction.title} / ${direction.studyComposition ? '主体与光场' : 'Shader研究'}`));
  if (assets.childElementCount) article.append(assets);
  const shown=new Set([direction.claim].filter(Boolean));
  for(const [key,label] of [['description','方向说明'],['caption','画面说明']]){
    const content=direction[key];if(typeof content==='string'&&content.trim()&&!shown.has(content)){article.append(make('p',`compare-${key}`,`${label}：${content}`));shown.add(content);}
  }
  const snapshot = direction.snapshot;
  article.append(make('p', 'compare-snapshot', snapshot ? `保存版本 ${snapshot.revision ?? '—'} · ${Number(snapshot.timeSeconds || 0).toFixed(2)} s` : '未保存'));
  if (direction.hypothesis?.mechanism) article.append(make('p', 'compare-mechanism', direction.hypothesis.mechanism));
  if (!allowSelect) {
    const notes = make('div', 'print-direction-notes');
    const hypothesis=make('div','print-hypothesis-block');
    if (direction.hypothesis?.question) hypothesis.append(make('h4', '', '判断的问题'), make('p', '', direction.hypothesis.question));
    if (direction.hypothesis?.expected) hypothesis.append(make('p', '', `预期：${textOf(direction.hypothesis.expected)}`));
    if (direction.hypothesis?.failure) hypothesis.append(make('p', '', `反例：${textOf(direction.hypothesis.failure)}`));
    notes.append(hypothesis);
    for (const [key, label] of [['adopt', '采用的关系'], ['exclude', '不继承的内容'], ['unproven', '仍未证明']]) {
      const block = make('div', 'print-handoff-block'); block.append(make('h4', '', label)); const list = make('ul');
      for (const item of asArray(direction.handoff?.[key])) list.append(make('li', '', item));
      if (!list.childElementCount) list.append(make('li', '', '尚未声明；不代表已验证或获批。'));
      block.append(list); notes.append(block);
    }
    article.append(notes);
  }
  if (allowSelect) {const button = make('button', 'text-button'); button.type = 'button'; button.append(make('span', '', '进入此方向'), make('span', '', '↗')); button.addEventListener('click', () => {$('compare-dialog').close(); act(() => api.setDirection(direction.id)); $('study').scrollIntoView({behavior: state.reducedMotion ? 'auto' : 'smooth'});}); article.append(button);}
  return article;
}
const roleLabels = {__proto__:null, hero:'主体关系', macro:'局部与空间关系', aperture:'气口对照', plan:'总图', entrance:'入口视点', threshold:'屏端视点', center:'中央视点', material:'光与材质'};
let comparisonRole = null;
function pairedFigure(direction, index, role) {
  const article = make('article', 'paired-item'); article.dataset.directionId = direction.id;
  article.append(make('h3', '', `${numbered(index)} / ${direction.title || direction.id}`));
  const asset = role === null ? null : visibleAssets(direction).find(item => item.role === role && mediaURL(item.url));
  const url = mediaURL(asset?.url || (role === null && direction.snapshot ? viewingPoster(direction) : null));
  const image = make('div', 'paired-image');
  if (url) {const img = make('img'); img.src = url; img.alt = asset?.alt || asset?.caption || `${direction.title} · 已保存主体与光场`; img.loading = 'eager'; img.addEventListener('error', () => image.replaceChildren(make('p', 'compare-missing', '此画面载入失败，尚未验证。'))); image.append(img);}
  else image.append(make('p', 'compare-missing', '此维度尚无可用画面。'));
  article.append(image, make('p', 'paired-caption', asset?.caption || (direction.snapshot ? `${Number(direction.snapshot.timeSeconds || 0).toFixed(2)} s · v${direction.snapshot.revision ?? '—'} · 已保存主体与光场` : '尚无已保存快照')));
  if (url) article.append(originalImageLink(url, `${direction.title} / ${roleLabels[role] || (role === null ? '已保存主体与光场' : role)}`));
  return article;
}
let inspectZoom=1,inspectPan={x:0,y:0},inspectWasPlaying=false;
function inspectButton(entries){const button=make('button','inspect-link','板内细看 ↗');button.type='button';button.addEventListener('click',()=>openInspector(entries));return button;}
function updateInspector(){
  const limit=(inspectZoom-1)/2;inspectPan.x=Math.max(-limit,Math.min(limit,inspectPan.x));inspectPan.y=Math.max(-limit,Math.min(limit,inspectPan.y));
  $('inspect-scale').value=`${Math.round(inspectZoom*100)}%`;
  for(const img of $('inspect-grid').querySelectorAll('img'))img.style.transform=`translate(${inspectPan.x*100}%,${inspectPan.y*100}%) scale(${inspectZoom})`;
  $('inspect-out').disabled=inspectZoom<=1;$('inspect-in').disabled=inspectZoom>=6;
}
function openInspector(entries){
  entries=entries.filter(entry=>mediaURL(entry.url));if(!entries.length){toast('尚无可细看的已保存画面。');return;}
  const dialog=$('inspect-dialog'),grid=$('inspect-grid');grid.replaceChildren();inspectZoom=1;inspectPan={x:0,y:0};dialog.dataset.single='false';
  $('inspect-layout').hidden=entries.length<2;$('inspect-layout').textContent='逐图细看';
  for(const entry of entries){const figure=make('figure','inspect-item'),viewport=make('div','inspect-viewport'),img=make('img');
    figure.append(make('h3','',entry.title));viewport.tabIndex=0;viewport.setAttribute('aria-label',`${entry.title}，可放大和平移`);viewport.setAttribute('aria-describedby','inspect-hint');
    img.src=entry.url;img.alt=entry.caption||entry.title;img.draggable=false;img.addEventListener('error',()=>viewport.replaceChildren(make('p','asset-error','此画面载入失败，不能细看。')));viewport.append(img);
    let drag=null;viewport.addEventListener('pointerdown',event=>{if(event.button!==0)return;viewport.focus();drag={id:event.pointerId,x:event.clientX,y:event.clientY,pan:{...inspectPan}};viewport.setPointerCapture(event.pointerId);});
    viewport.addEventListener('pointermove',event=>{if(!drag||drag.id!==event.pointerId)return;const rect=viewport.getBoundingClientRect();inspectPan={x:drag.pan.x+(event.clientX-drag.x)/rect.width,y:drag.pan.y+(event.clientY-drag.y)/rect.height};updateInspector();});
    const finish=()=>{drag=null;};viewport.addEventListener('pointerup',finish);viewport.addEventListener('pointercancel',finish);viewport.addEventListener('lostpointercapture',finish);
    viewport.addEventListener('keydown',event=>{const actions={ArrowLeft:()=>inspectPan.x-=.08,ArrowRight:()=>inspectPan.x+=.08,ArrowUp:()=>inspectPan.y-=.08,ArrowDown:()=>inspectPan.y+=.08,'+':()=>inspectZoom=Math.min(6,inspectZoom+.5),'=':()=>inspectZoom=Math.min(6,inspectZoom+.5),'-':()=>inspectZoom=Math.max(1,inspectZoom-.5),'0':()=>{inspectZoom=1;inspectPan={x:0,y:0};}};if(actions[event.key]){event.preventDefault();actions[event.key]();updateInspector();}});
    figure.append(viewport,make('figcaption','',entry.caption||''),originalImageLink(entry.url,entry.title));grid.append(figure);
  }
  inspectWasPlaying=!getState().paused;act(()=>api.pause());updateInspector();dialog.showModal();
}
function renderPairedComparison() {
  const grid = $('compare-grid'); grid.replaceChildren();
  state.project.directions.forEach((direction, index) => grid.append(pairedFigure(direction, index, comparisonRole)));
}
function renderComparison() {
  const print = $('print-directions'), details = $('compare-details'), select = $('compare-role'); print.replaceChildren(); details.replaceChildren(); select.replaceChildren();
  const roles = state.project.directions.map(direction => {
    const counts = new Map(); for (const asset of visibleAssets(direction)) if (mediaURL(asset.url) && typeof asset.role === 'string' && asset.role.trim()) counts.set(asset.role, (counts.get(asset.role) || 0) + 1);
    return new Set([...counts].filter(([, count]) => count === 1).map(([role]) => role));
  });
  const common = [...roles[0]].filter(role => roles.every(set => set.has(role)));
  const choices = new Map([['snapshot', null], ...common.map(role => [JSON.stringify(['asset', role]), role])]);
  for (const [value, role] of choices) {const option = make('option', '', role === null ? '已保存主体与光场' : roleLabels[role] || role); option.value = value; select.append(option);}
  if (comparisonRole !== null && !common.includes(comparisonRole)) comparisonRole = null;
  select.value = comparisonRole === null ? 'snapshot' : JSON.stringify(['asset', comparisonRole]); select.onchange = () => {if (!choices.has(select.value)) return; comparisonRole = choices.get(select.value); renderPairedComparison();};
  renderPairedComparison();
  state.project.directions.forEach((direction, index) => {details.append(snapshotFigure(direction, index)); print.append(snapshotFigure(direction, index, false));});
  setText('print-overview-title',`${state.project.project.title} / 已保存方向`);
  synchronize(); setText('compare-note', state.dirty ? '当前有未保存变化。主体与光场显示各方向已提交快照；其他维度为项目素材，不随实时参数变化。保存并重新生成海报后再比较。' : '先按共同维度并看，再展开依据。主体与光场来自已提交快照；其他维度为项目素材，不随实时参数变化，也不表示观看关系或制作可行性已通过。');
}
function renderReview() {
  const content = $('review-content'); content.replaceChildren(); const direction = currentDirection();
  function section(title) {const el = make('section', 'review-section'); el.append(make('h3', '', title)); content.append(el); return el;}
  function appendList(el, items, empty) {const ul = make('ul'); asArray(items).forEach((item) => ul.append(make('li', '', item))); if (!ul.childElementCount) ul.append(make('li', '', empty)); el.append(ul);}
  const contract = section('分别判断：研究对象 / HTML 承载体验');
  contract.append(make('p', '', '两类判断分别成立。网页的表现不抵消对象研究的不足，技术绘制也不证明视觉假设成立。'));
  contract.append(make('h3', '', '研究对象成功条件')); appendList(contract, state.project.brief?.objectSuccess, '尚未声明。');
  contract.append(make('h3', '', '承载体验成功条件')); appendList(contract, state.project.brief?.carrierSuccess, '尚未声明。');
  const locks = section('当前锁定与开放变量'); appendList(locks, state.project.brief?.locks, '尚未声明锁定；不因此获得修改原件的授权。'); appendList(locks, state.project.brief?.openVariables, '尚未声明开放变量。');
  const quality = section('当前方向的判断状态');
  for (const [key, label] of [['object', '研究对象'], ['carrier', '承载体验']]) {const value = direction.quality?.[key]; quality.append(make('p', 'review-status', `${label}：${value?.status || 'unverified'}`)); appendList(quality, value?.evidence, '没有可定位的本版判断依据。'); if (value?.issues?.length) appendList(quality, value.issues, '');}
  quality.append(make('p', '', '以上读取项目记录，不表示本网页自动验收。自检、独立审阅与用户接受分别记录。'));
  const references = section(`制作前比较依据 · ${state.project.benchmarks?.revision || '未指定版本'}`);
  for (const [key, label] of [['object', '研究对象'], ['carrier', '承载体验']]) {
    references.append(make('h3', '', label));
    const entries = asArray(state.project.benchmarks?.[key]);
    if (!entries.length) references.append(make('p', '', '未记录此类标杆。'));
    entries.forEach((benchmark) => {
      const url = sourceURL(benchmark.url); const p = make('p');
      if (url) {const link = make('a', '', benchmark.title || benchmark.id || url); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; p.append(link);} else p.textContent = benchmark.title || benchmark.id || '未提供可访问来源';
      references.append(p, make('p', '', `采用理由：${textOf(benchmark.reason)}`), make('p', '', `观察范围：${textOf(benchmark.observe) || '未声明'} · ${benchmark.observed ? '项目记录已观察' : '尚未实际观察'}`), make('p', '', `关键差距：${textOf(benchmark.criticalGap) || '未声明'}`));
    });
  }
  const sources = section('素材与派生边界');
  if (!direction.assets?.length) sources.append(make('p', '', '当前方向没有外部位图素材；程序画面为自编研究，仍需按实际视觉结果判断。'));
  for (const asset of asArray(direction.assets)) {
    sources.append(make('p', '', `${asset.caption || asset.title || asset.id || '素材'} · ${asset.role || '角色未声明'}`));
    const details = make('details'); details.append(make('summary', '', '来源、允许操作与转换链'), make('pre', '', JSON.stringify(asset, null, 2))); sources.append(details);
  }
  if (direction.studyComposition) {
    const layers = section('主体与光场的观看条件'); layers.append(make('p', '', direction.studyComposition.purpose));
    const details = make('details'); details.append(make('summary', '', '合成定义与纯 Shader 拆解'), make('pre', '', JSON.stringify({definition: direction.studyComposition, observation: getState().composition}, null, 2)));
    const raw = mediaURL(direction.poster); if (raw) {const img = make('img', 'review-shader-poster'); img.src = raw; img.alt = `${direction.title} · 纯 Shader 技术拆解，非主体合成`; details.append(img);}
    layers.append(details);
  }
  const runtime = section('实际运行与快照');
  const dl = make('dl'); const current = getState();
  for (const [label, value] of [['方向', current.directionId], ['配方', current.recipeId], ['快照', current.snapshot?.id || '尚未保存'], ['摘要', current.snapshot?.digest || '尚未绑定'], ['当前时间', `${current.timeSeconds.toFixed(3)} s`], ['未保存变化', current.dirty ? '有' : '无'], ['GPU状态', current.gpu?.status || 'unknown'], ['实际绘制', current.gpu?.drawCount ?? 'unknown'], ['视口', `${innerWidth} × ${innerHeight} / DPR ${devicePixelRatio}`]]) {dl.append(make('dt', '', label), make('dd', '', value));}
  runtime.append(dl); const details = make('details'); details.append(make('summary', '', '查看真实 GPU 观察与参数'), make('pre', '', JSON.stringify({gpu: current.gpu, failure: current.failure, composition: current.composition, parameters: current.parameters}, null, 2))); runtime.append(details);
}
async function recordObservation(event) {
  try {await requestJSON('/api/observation', {method: 'POST', body: JSON.stringify({event, ...getState(), browser: navigator.userAgent, observedAt: new Date().toISOString(), scope: 'browser_runtime_observation_not_quality_acceptance'})});}
  catch (error) {console.warn('[VEM] 运行观察未登记', error.message);}
}
async function preparePrint(options = {}) {
  if (state.exporting) return getState();
  requireComposition();
  printWasPlaying = !state.paused; exportFrozen = true; await pause();
  try {
    if (options.project) {state.project = validateProject(options.project); state.snapshot = clone(currentDirection()?.snapshot || state.snapshot);}
    else if (options.refresh !== false) {state.project = validateProject(await requestJSON('/api/project')); state.snapshot = clone(currentDirection()?.snapshot || state.snapshot);}
    synchronize();
    if (state.dirty) throw new Error('当前画面尚未保存。请先提交当前参数与选帧，再导出对应快照。');
    if (!renderer || state.failure || state.gpu?.status !== 'ready') throw new Error('当前 Shader 不可用，不能导出完整视觉总览。');
    for (const direction of state.project.directions) if (!direction.snapshot || !mediaURL(direction.poster) || !mediaURL(viewingPoster(direction))) throw new Error(`方向「${direction.title || direction.id}」缺少当前已保存快照或对应主体研究海报，不能导出完整总览。`);
    await renderer.renderAt(state.snapshot.timeSeconds); synchronize();
    const image = $('print-frame'); image.src = state.composition ? mediaURL(currentDirection().compositionPoster) : $('study-canvas').toDataURL('image/png'); await image.decode(); image.hidden = false;
    state.exporting = true; document.body.dataset.export = 'true'; $('print-overview').hidden = false; renderComparison(); updatePlayback();
    const images = [...document.querySelectorAll('#print-directions img')];
    await Promise.all(images.map(async (item) => {await item.decode(); if (!item.naturalWidth || !item.naturalHeight) throw new Error('导出所需素材或海报为空。');}));
    if (state.project.directions.length !== $('print-directions').querySelectorAll('.compare-poster').length) throw new Error('方向海报载入失败，不能导出完整总览。');
    const expectedAssets = state.project.directions.reduce((count, direction) => count + visibleAssets(direction).filter(asset=>asset.url).length, 0);
    if (expectedAssets !== $('print-directions').querySelectorAll('.compare-asset img').length) throw new Error('方向主体研究未完整载入，不能导出完整总览。');
    await document.fonts.ready; return getState();
  } catch (error) {
    state.exporting = false; exportFrozen = false; document.body.removeAttribute('data-export'); $('print-overview').hidden = true; $('print-frame').hidden = true; updatePlayback();
    throw error;
  }
}
async function finishPrint() {
  state.exporting = false; exportFrozen = false; document.body.removeAttribute('data-export'); $('print-overview').hidden = true; $('print-frame').hidden = true;
  if (printWasPlaying && !state.reducedMotion && renderer && !state.failure) await renderer.resume(); printWasPlaying = false; updatePlayback(); return getState();
}
async function downloadExport(format) {
  requireComposition();
  await pause(); synchronize();
  if (state.dirty) await commitSnapshot();
  state.exporting = true; updatePlayback(); toast('正在生成已保存方向总览…');
  try {
    const response = await fetch('/api/export', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({format}),cache: 'no-store'});
    if (!response.ok) {let data; try {data = await response.json();} catch {} throw new Error(textOf(data?.error?.message || data?.error || data?.message || `导出失败（${response.status}）`));}
    const expected = format === 'png' ? 'image/png' : 'application/pdf';
    if (!(response.headers.get('content-type') || '').includes(expected)) throw new Error('导出响应格式与请求不一致。');
    const blob = await response.blob(); if (!blob.size) throw new Error('导出文件为空。');
    const url = URL.createObjectURL(blob); const link = make('a'); link.href = url;
    const disposition = response.headers.get('content-disposition') || '';
    const match = /filename\*=UTF-8''([^;]+)|filename="([^"]+)"|filename=([^;]+)/i.exec(disposition);
    let filename = `visual-study.${format}`; try {if (match) filename = decodeURIComponent(match[1] || match[2] || match[3]);} catch {}
    link.download = filename; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);
    state.project = validateProject(await requestJSON('/api/project')); state.snapshot = clone(currentDirection()?.snapshot || state.snapshot); renderComparison();
    toast(`已导出 ${format.toUpperCase()} 总览。各方向引用自己的已保存快照。`);
  } finally {state.exporting = false; updatePlayback();}
}

const api = {
  ready: null, getState,
  setDirection: (id) => enqueue(() => loadDirection(id)),
  setParameters: (parameters) => enqueue(() => setParameters(parameters)),
  setCompositionEnabled: (enabled) => enqueue(() => setCompositionEnabled(enabled)),
  seek: (seconds) => enqueue(() => seek(seconds)), pause: () => enqueue(pause), resume: () => enqueue(resume), commitSnapshot: () => enqueue(commitSnapshot),
  preparePrint: (options) => enqueue(() => preparePrint(options)), finishPrint: () => enqueue(finishPrint),
  refreshProject: () => enqueue(async () => {const id = state.directionId; state.project = validateProject(await requestJSON('/api/project')); renderProject(); return loadDirection(id);}),
};
window.VEM = api;
$('play-toggle').addEventListener('click', () => act(() => getState().paused ? api.resume() : api.pause()));
$('restart').addEventListener('click', () => act(() => enqueue(async () => {await seek(0); if (!state.reducedMotion) await resume();})));
$('timeline').addEventListener('input', () => act(() => api.seek(Number($('timeline').value))));
$('save-snapshot').addEventListener('click', () => act(() => api.commitSnapshot()));
$('export-png').addEventListener('click', () => act(() => enqueue(() => downloadExport('png'))));
$('export-pdf').addEventListener('click', () => act(() => enqueue(() => downloadExport('pdf'))));
$('restore').addEventListener('click', () => act(() => enqueue(async () => {const direction = currentDirection(); drafts.delete(state.directionId); await setParameters(direction.snapshot?.parameters || direction.parameters || {}); await seek(direction.snapshot?.timeSeconds || 0); toast('已恢复此方向的已保存参数与选帧。');})));
$('reduced-motion').addEventListener('change', () => act(async () => {state.reducedMotion = $('reduced-motion').checked; if (state.reducedMotion) await api.pause(); else await api.resume();}));
$('composition-enabled').addEventListener('change', () => act(() => api.setCompositionEnabled($('composition-enabled').checked)));
$('compare-open').addEventListener('click', () => {if (!state.project) return; renderComparison(); $('compare-dialog').showModal();});
$('compare-close').addEventListener('click', () => $('compare-dialog').close());
$('compare-inspect').addEventListener('click',()=>openInspector(state.project.directions.map(d=>{const asset=comparisonRole===null?null:visibleAssets(d).find(a=>a.role===comparisonRole);return {url:comparisonRole===null?viewingPoster(d):asset?.url,title:d.title,caption:asset?.caption||(comparisonRole===null?'已保存主体与光场':'')};})));
$('inspect-close').addEventListener('click',()=>$('inspect-dialog').close());
$('inspect-dialog').addEventListener('close',()=>{if(inspectWasPlaying&&!state.reducedMotion)act(()=>api.resume());inspectWasPlaying=false;});
$('inspect-in').addEventListener('click',()=>{inspectZoom=Math.min(6,inspectZoom+.5);updateInspector();});
$('inspect-out').addEventListener('click',()=>{inspectZoom=Math.max(1,inspectZoom-.5);updateInspector();});
$('inspect-reset').addEventListener('click',()=>{inspectZoom=1;inspectPan={x:0,y:0};updateInspector();});
$('inspect-layout').addEventListener('click',()=>{const single=$('inspect-dialog').dataset.single!=='true';$('inspect-dialog').dataset.single=String(single);$('inspect-layout').textContent=single?'同步并看':'逐图细看';});
$('review-open').addEventListener('click', () => {if (!state.project) return; renderReview(); $('review-dialog').showModal();});
$('review-close').addEventListener('click', () => $('review-dialog').close());
for (const dialog of [$('compare-dialog'), $('review-dialog')]) dialog.addEventListener('click', (event) => {if (event.target === dialog) {const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();}});
$('direction-nav').addEventListener('keydown', (event) => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key) || !event.target.matches('.direction-tab')) return;
  const buttons = [...$('direction-nav').querySelectorAll('button')]; const index = buttons.indexOf(event.target);
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
  event.preventDefault(); act(async () => {await api.setDirection(buttons[next].dataset.directionId); $('direction-nav').querySelectorAll('button')[next].focus();});
});
document.addEventListener('keydown', (event) => {if (event.code !== 'Space' || event.target.matches('button,a,input,select,textarea,summary') || document.querySelector('dialog[open]')) return; event.preventDefault(); act(() => getState().paused ? api.resume() : api.pause());});
matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (event) => {state.reducedMotion = event.matches; if (event.matches) act(() => api.pause()); updatePlayback();});
document.addEventListener('visibilitychange', () => {if (document.hidden && renderer) {renderer.pause(); synchronize(); updatePlayback();}});
window.addEventListener('beforeunload', () => {renderer?.destroy();});
window.addEventListener('beforeprint', () => {if (!state.exporting) {toast('请使用已保存状态的导出入口，以保证 Shader 和所有方向海报完整。');}});
setInterval(() => {if (state.project && !state.loading) updatePlayback();}, 250);

// Move the actual controls, retaining listeners and DOM reading/focus order.
// Long support-asset sequences must not separate mobile parameters from the study.
const mobileStudyLayout=matchMedia('(max-width:760px)');
function arrangeStudyLayout(){
  const main=document.querySelector('.study-main'),aside=document.querySelector('.direction-aside');
  if(mobileStudyLayout.matches){main.prepend($('direction-heading'));main.insertBefore($('direction-tools'),$('asset-section'));}
  else aside.append($('direction-heading'),$('direction-tools'));
}
mobileStudyLayout.addEventListener('change',arrangeStudyLayout);arrangeStudyLayout();

api.ready = (async () => {
  try {
    state.project = validateProject(await requestJSON('/api/project')); renderProject();
    const requested = new URL(location.href).searchParams.get('direction');
    await loadDirection(state.project.directions.some((direction) => direction.id === requested) ? requested : state.project.directions[0].id);
    renderComparison(); return getState();
  } catch (error) {
    state.failure = {code: 'PROJECT_LOAD_FAILED', message: error.message}; setText('project-title', '研究暂未载入'); setText('decision', error.message); state.loading = false; updatePlayback();
    return getState();
  }
})();
