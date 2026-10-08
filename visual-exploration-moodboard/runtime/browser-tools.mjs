import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {chromium} from 'playwright';
import {startServer} from './server.mjs';
import {loadProject,projectFile,engineDigest,atomicJSON,fileReference,verifyReference,verifyFileReference,attachRender,withProjectLock,assert,now,ContractError,canonical,digest,validateSavedSnapshot} from './project-store.mjs';
import {AUTHORITY_RENDER_PROFILE,assertAuthorityRenderProfile,assertRenderEnvironment,resolveAuthorityRenderProfile,renderBinding} from './render-profile.mjs';
import {decodePNG} from './media-contract.mjs';

const imageDimensionCache=new Map();
// Decode the bound source independently of the saved receipt. Positive numbers
// in a receipt alone do not prove the actual image's intrinsic dimensions.
export async function decodeAssetDimensions(projectRoot,assets) {
  const sources=[];
  for(const asset of assets){const {bytes}=await verifyFileReference(projectRoot,asset.sourceRef),extension=path.extname(asset.sourceRef.path).toLowerCase(),mime={'.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.gif':'image/gif','.avif':'image/avif','.bmp':'image/bmp','.ico':'image/x-icon'}[extension];
    assert(mime,'COMPOSITION_IMAGE_FORMAT','Composition source must be a supported browser image');const key=`${asset.sourceRef.sha256}:${mime}`,cached=imageDimensionCache.get(key);if(cached){sources.push({key,result:cached});continue;}sources.push({key,data:`data:${mime};base64,${bytes.toString('base64')}`});}
  if(sources.some(source=>!source.result)){let browser;
    try {browser=await chromium.launch({headless:true,executablePath:await findChromium()});const page=await browser.newPage();
      for(const source of sources){if(source.result)continue;source.result=await deadline(page.evaluate(async data=>{const image=new Image();image.src=data;await image.decode();if(!image.complete||image.naturalWidth<=0||image.naturalHeight<=0)throw new Error('Bound composition source did not decode');return {width:image.naturalWidth,height:image.naturalHeight};},source.data),15000,'Composition source decoding exceeded 15 seconds');imageDimensionCache.set(source.key,source.result);if(imageDimensionCache.size>128)imageDimensionCache.delete(imageDimensionCache.keys().next().value);}
    } finally {if(browser)await browser.close();}}
  return sources.map(source=>({...source.result}));
}

export async function findChromium(explicit) {
  if(explicit||process.env.VEM_CHROMIUM_PATH) {const p=explicit||process.env.VEM_CHROMIUM_PATH;assert((await fs.stat(p)).isFile(),'BROWSER_MISSING','Chromium path must name an executable');return p;}
  try{await fs.access(chromium.executablePath());return chromium.executablePath();}catch{}
  const roots=[process.env.PLAYWRIGHT_BROWSERS_PATH,path.join(process.env.LOCALAPPDATA||path.join(os.homedir(),'AppData','Local'),'ms-playwright'),path.join(os.homedir(),'.cache','ms-playwright')].filter(x=>x&&x!=='0');
  for(const root of roots){let entries;try{entries=await fs.readdir(root);}catch{continue;}for(const entry of entries.filter(x=>/^chromium-\d+$/.test(x)).sort().reverse()){for(const name of ['chrome-win64/chrome.exe','chrome-win/chrome.exe','chrome-linux64/chrome','chrome-linux/chrome','chrome-mac/Chromium.app/Contents/MacOS/Chromium']){const candidate=path.join(root,entry,name);try{await fs.access(candidate);return candidate;}catch{}}}}
  throw new ContractError('BROWSER_MISSING','Install the pinned Playwright Chromium (npx playwright install chromium), or set VEM_CHROMIUM_PATH',2);
}
export async function withBrowser(projectRoot,{url,chromiumPath,viewport=AUTHORITY_RENDER_PROFILE.viewport,deviceScaleFactor=1,reducedMotion='reduce',colorScheme='light',renderProfile}={},callback) {
  let local,browser;
  try {
    if(!url){local=await startServer(projectRoot);url=local.url;}
    const executablePath=await findChromium(chromiumPath);
    browser=await chromium.launch({headless:true,executablePath,...(renderProfile?{args:['--force-color-profile=srgb']}:{})});
    const page=await browser.newPage({viewport,deviceScaleFactor,reducedMotion,colorScheme});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto(url,{waitUntil:'networkidle',timeout:60000});
    await page.waitForFunction(()=>!!window.VEM,{timeout:30000});
    await deadline(page.evaluate(()=>window.VEM.ready),45000,'GPU initialization exceeded 45 seconds');
    const state=await page.evaluate(()=>window.VEM.getState());assert(!state.failure,'BROWSER_RUNTIME_FAILED',state.failure?.message||'Runtime failed');
    return await deadline(callback({page,browser,executablePath,url,errors,renderProfile}),180000,'Browser operation exceeded 180 seconds');
  } finally {if(browser)await browser.close();if(local)await local.close();}
}
async function deadline(promise,milliseconds,message){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new ContractError('BROWSER_TIMEOUT',message,2)),milliseconds);})]);}finally{clearTimeout(timer);}}
async function selectSnapshot(page,direction) {
  assert(direction.snapshot,'SNAPSHOT_MISSING',`${direction.id}: commit before rendering`);
  const s=direction.snapshot;
  await page.evaluate(async({id,parameters,time,compositionRequired})=>{await window.VEM.setDirection(id);if(compositionRequired){if(typeof window.VEM.setCompositionEnabled!=='function')throw new Error('Composition controls are unavailable');await window.VEM.setCompositionEnabled(true);}await window.VEM.pause();await window.VEM.setParameters(parameters);await window.VEM.seek(time);},{id:direction.id,parameters:s.parameters,time:s.timeSeconds,compositionRequired:!!direction.studyComposition});
  // Upstream follows parent layout. Allow its ResizeObserver to settle, then read the final frame.
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  await page.evaluate(seconds=>window.VEM.seek(seconds),s.timeSeconds);
  const state=await page.evaluate(()=>window.VEM.getState());
  assert(!state.failure && state.gpu?.deviceCreated && state.gpu?.status==='ready' && state.gpu.currentFrameReadbackVerified,'NO_GPU_OUTPUT','Current GPU frame was not actually read back');
  assert(canonical(state.parameters)===canonical(s.parameters)&&Math.abs(state.timeSeconds-s.timeSeconds)<0.000001,'FRAME_MISMATCH','Browser frame differs from snapshot');
  return state;
}
async function observeRenderEnvironment(page,profile,pixels) {
  assertAuthorityRenderProfile(profile);
  const observed=await page.evaluate(()=>{
    const canvas=document.querySelector('#study-canvas'),configuration=canvas?.getContext('webgpu')?.getConfiguration?.();
    return {viewport:{width:innerWidth,height:innerHeight},deviceScaleFactor:devicePixelRatio,
      colorScheme:matchMedia('(prefers-color-scheme: light)').matches?'light':'dark',
      reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches?'reduce':'no-preference',
      dynamicRange:matchMedia('(dynamic-range: high)').matches?'hdr':'sdr',
      canvas:configuration?{colorSpace:configuration.colorSpace,toneMapping:configuration.toneMapping?.mode,format:configuration.format,width:canvas.width,height:canvas.height}:null};
  });
  return assertRenderEnvironment(profile,observed,pixels);
}
async function captureComposition(projectRoot,ctx,direction,state) {
  const scene=direction.studyComposition;
  if(!scene) {assert(!state.composition,'COMPOSITION_MISMATCH','Undeclared composition is active');return null;}
  const observation=state.composition;
  assert(observation?.enabled===true&&observation.decoded===true&&!observation.failure,'COMPOSITION_NOT_READY',`${direction.id}: enabled, decoded composition required`);
  const keys=['baseAssetId','maskAssetId','opacity','blendMode','aspectRatio','purpose'];
  assert(keys.every(key=>canonical(observation[key])===canonical(scene[key])),'COMPOSITION_MISMATCH',`${direction.id}: current composition differs from saved contract`);
  const base=direction.assets?.find(asset=>asset.id===scene.baseAssetId),mask=direction.assets?.find(asset=>asset.id===scene.maskAssetId);
  assert(base&&mask&&base.presentation==='composition-only'&&mask.presentation==='composition-only','COMPOSITION_ASSET_MISSING','Composition assets must be explicitly bound by id and presentation');
  const actual=await ctx.page.evaluate(async({base,mask})=>{
    const output={};
    for(const [role,selector,source] of [['base','#composition-base',base],['mask','#composition-mask-source',mask]]) {
      const image=document.querySelector(selector);
      if(!image||image.src!==new URL(source,location.href).href)throw new Error(`Composition ${role} source mismatch`);
      await image.decode();
      if(!image.complete||image.naturalWidth<=0||image.naturalHeight<=0)throw new Error(`Composition ${role} did not decode`);
      output[role]={src:image.src,width:image.naturalWidth,height:image.naturalHeight};
    }
    const canvas=document.querySelector('#study-canvas'),style=getComputedStyle(canvas),stage=document.querySelector('#shader-stage').getBoundingClientRect();
    output.styles={opacity:Number(style.opacity),blendMode:style.mixBlendMode,maskImage:style.maskImage,display:style.display,visibility:style.visibility};
    output.stage={width:stage.width,height:stage.height};
    return output;
  },{base:base.url,mask:mask.url});
  assert(actual.styles.display!=='none'&&actual.styles.visibility!=='hidden'&&Math.abs(actual.styles.opacity-scene.opacity)<0.000001&&actual.styles.blendMode===scene.blendMode&&actual.styles.maskImage.includes(actual.mask.src),'COMPOSITION_STYLE_MISMATCH','Actual canvas mask, opacity or blend differs from the scene contract');
  assert(actual.stage.width>0&&actual.stage.height>0&&Math.abs(actual.stage.width/actual.stage.height-scene.aspectRatio)<0.01,'COMPOSITION_STYLE_MISMATCH','Actual stage aspect ratio differs from the scene contract');
  assert(!(await ctx.page.locator('#stage-failure').isVisible()),'COMPOSITION_NOT_READY','Failure overlay cannot be captured as a composition');
  const relative=`compositions/${direction.snapshot.id}.png`,filename=await projectFile(projectRoot,relative);await fs.mkdir(path.dirname(filename),{recursive:true});
  const decorations=ctx.page.locator('#shader-stage .stage-mode, #shader-stage .stage-corner');
  const visibility=await decorations.evaluateAll(elements=>elements.map(element=>({value:element.style.getPropertyValue('visibility'),priority:element.style.getPropertyPriority('visibility')})));
  let bytes;
  try {await decorations.evaluateAll(elements=>elements.forEach(element=>element.style.setProperty('visibility','hidden','important')));bytes=await ctx.page.locator('#shader-stage').screenshot({path:filename,animations:'disabled'});}
  finally {await decorations.evaluateAll((elements,previous)=>elements.forEach((element,index)=>{const saved=previous[index];if(saved?.value)element.style.setProperty('visibility',saved.value,saved.priority);else element.style.removeProperty('visibility');}),visibility);}
  const decoded=decodePNG(bytes);assert(decoded.nonTransparent>0,'EMPTY_COMPOSITION','Actual composition capture is empty');
  return {enabled:true,sourceDigest:digest(scene),observation:structuredClone(observation),assets:actual,output:await fileReference(projectRoot,relative),pixels:{width:decoded.width,height:decoded.height,decodedDigest:decoded.pixelDigest}};
}
async function renderInBrowser(projectRoot,ctx,direction) {
  assertAuthorityRenderProfile(ctx.renderProfile);
  assertAuthorityRenderProfile(direction.snapshot?.renderProfile);
  assert(direction.snapshot?.engineDigest===await engineDigest(),'STALE_SNAPSHOT',`${direction.id}: save against the current runtime before rendering`);
  await validateSavedSnapshot(projectRoot,await loadProject(projectRoot),direction);
  const state=await selectSnapshot(ctx.page,direction);
  const renderEnvironment=await observeRenderEnvironment(ctx.page,ctx.renderProfile,{width:state.gpu.width,height:state.gpu.height});
  const composition=await captureComposition(projectRoot,ctx,direction,state);
  const relative=`posters/${direction.snapshot.id}.png`;const filename=await projectFile(projectRoot,relative);await fs.mkdir(path.dirname(filename),{recursive:true});
  // The canvas is the studied object; viewport decorations cannot replace its evidence.
  const png=await ctx.page.locator('#study-canvas').evaluate(canvas=>canvas.toDataURL('image/png'));
  assert(png.startsWith('data:image/png;base64,'),'PNG_CAPTURE_FAILED','Canvas did not return PNG bytes');
  await fs.writeFile(filename,Buffer.from(png.slice('data:image/png;base64,'.length),'base64'));
  const raw=state.gpu.lastReadback;
  const receipt={schemaVersion:1,kind:'actual-shader-frame',createdAt:now(),directionId:direction.id,snapshotDigest:direction.snapshot.digest,engineDigest:await engineDigest(),renderProfile:structuredClone(ctx.renderProfile),renderEnvironment,composition,browser:{executablePath:ctx.executablePath,version:ctx.browser.version()},gpu:{device:state.gpu.deviceCreated,observation:state.gpu},pixels:{nonTransparent:raw.opaquePixels,nonZero:raw.nonZeroPixels,decodedDigest:raw.pixelDigest,width:state.gpu.width,height:state.gpu.height},output:await fileReference(projectRoot,relative),scope:'Actual current GPU output and browser capture; not art-direction acceptance'};
  const receiptPath=`evidence/render-${direction.snapshot.id}.json`;await atomicJSON(await projectFile(projectRoot,receiptPath),receipt);
  await attachRender(projectRoot,direction.id,await fileReference(projectRoot,receiptPath),relative,composition?.output.path);return receipt;
}
export async function renderProject(projectRoot,options={}) {
  const renderProfile=resolveAuthorityRenderProfile(options);
  return withBrowser(projectRoot,{...options,renderProfile},async ctx=>{const project=await loadProject(projectRoot);const receipts=[];for(const direction of project.directions)receipts.push(await renderInBrowser(projectRoot,ctx,direction));assert(!ctx.errors.length,'BROWSER_ERRORS',ctx.errors.join('\n'));return receipts;});
}
// Chromium's PDF vector backend can change SVG blend/isolation behavior.
// Preserve the browser-decoded appearance, leaving editable source SVGs intact.
export async function rasterizePrintSVGs(projectRoot,{page}) {
  const rasters=await page.locator('#print-directions .compare-asset img').evaluateAll(async images=>{
    const output=[];
    for(const [index,image] of images.entries()) {
      const sourceURL=image.src;if(!new URL(sourceURL).pathname.toLowerCase().endsWith('.svg'))continue;
      await image.decode();const originalWidth=image.naturalWidth,originalHeight=image.naturalHeight;
      if(!(originalWidth>0&&originalHeight>0))throw new Error('PDF SVG source has no decoded dimensions');
      const scale=Math.min(1,4096/Math.max(originalWidth,originalHeight)),width=Math.max(1,Math.round(originalWidth*scale)),height=Math.max(1,Math.round(originalHeight*scale));
      const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
      const context=canvas.getContext('2d');if(!context)throw new Error('PDF image rasterization context unavailable');
      context.drawImage(image,0,0,width,height);const data=canvas.toDataURL('image/png');
      image.src=data;await image.decode();output.push({index,sourceURL,originalWidth,originalHeight,width,height,data});
    }
    return output;
  });
  const receipts=[];
  for(const raster of rasters) {
    const bytes=Buffer.from(raster.data.split(',')[1],'base64'),pixels=decodePNG(bytes);assert(pixels.width===raster.width&&pixels.height===raster.height&&pixels.nonTransparent>0,'PDF_RASTER_INVALID','PDF SVG raster is empty or has incorrect dimensions');
    const relative=`exports/pdf-assets/asset-${raster.index+1}-${digest(raster.sourceURL).slice(0,12)}.png`,filename=await projectFile(projectRoot,relative);await fs.mkdir(path.dirname(filename),{recursive:true});await fs.writeFile(filename,bytes);
    const {data,...observation}=raster;receipts.push({...observation,output:await fileReference(projectRoot,relative),decodedDigest:pixels.pixelDigest});
  }
  return receipts;
}
export async function exportProject(projectRoot,{format='png',...options}={}) {
  assert(['png','pdf'].includes(format),'UNSUPPORTED_EXPORT','Only PNG and PDF are supported in v1');
  const renderProfile=resolveAuthorityRenderProfile(options);
  return withBrowser(projectRoot,{...options,renderProfile},async ctx=>{
    let project=await loadProject(projectRoot);const current=await engineDigest();
    for(const direction of project.directions) {
      assert(direction.snapshot?.engineDigest===current,'STALE_SNAPSHOT',`${direction.id}: save against the current runtime before exporting`);
      await renderInBrowser(projectRoot,ctx,direction);
    }
    project=await loadProject(projectRoot);
    const renderBindings=await savedRenderBindings(projectRoot,project);
    await selectSnapshot(ctx.page,project.directions[0]);
    const renderEnvironment=await observeRenderEnvironment(ctx.page,renderProfile);
    await ctx.page.evaluate(project=>window.VEM.preparePrint({project}),project);
    const relative=`exports/overview.${format}`;const filename=await projectFile(projectRoot,relative);await fs.mkdir(path.dirname(filename),{recursive:true});
    const printAssetRasters=format==='pdf'?await rasterizePrintSVGs(projectRoot,ctx):[];
    if(format==='png')await ctx.page.screenshot({path:filename,fullPage:true});
    else await ctx.page.pdf({path:filename,format:'A3',printBackground:true,preferCSSPageSize:true,margin:{top:'12mm',bottom:'12mm',left:'12mm',right:'12mm'}});
    assert(!ctx.errors.length,'BROWSER_ERRORS',ctx.errors.join('\n'));
    const receipt={schemaVersion:1,kind:`${format}-overview`,createdAt:now(),engineDigest:current,renderProfile,renderEnvironment,renderBindings,snapshots:project.directions.map(d=>[d.id,d.snapshot.digest]),printAssetRasters,output:await fileReference(projectRoot,relative),browser:{executablePath:ctx.executablePath,version:ctx.browser.version()},scope:'Complete saved-state overview; PDF SVG assets preserve decoded screen appearance as PNGs up to 4096px; visual inspection separately recorded'};
    const receiptPath=`evidence/export-${format}.json`;await atomicJSON(await projectFile(projectRoot,receiptPath),receipt);
    await withProjectLock(projectRoot,async()=>{const latest=await loadProject(projectRoot);assert(canonical(latest.directions.map(d=>[d.id,d.snapshot?.digest]))===canonical(receipt.snapshots),'STALE_EXPORT','Project changed while exporting');for(const direction of latest.directions)await validateSavedSnapshot(projectRoot,latest,direction,current);assert(canonical(await savedRenderBindings(projectRoot,latest))===canonical(renderBindings),'STALE_EXPORT','Authoritative posters changed while exporting');latest.exports||={};latest.exports[format]=await fileReference(projectRoot,receiptPath);await atomicJSON(path.join(projectRoot,'project.json'),latest);});
    await ctx.page.evaluate(()=>window.VEM.finishPrint());return receipt;
  });
}
async function savedRenderBindings(root,project) {
  const bindings=[];
  for(const direction of project.directions) {
    assert(direction.render,'RENDER_MISSING',`${direction.id}: actual render missing`);
    const receipt=await verifyReference(root,direction.render);
    await verifyFileReference(root,receipt.output);
    if(receipt.composition)await verifyFileReference(root,receipt.composition.output);
    assert(receipt.directionId===direction.id&&receipt.snapshotDigest===direction.snapshot?.digest,'STALE_EXPORT',`${direction.id}: render does not match saved state`);
    bindings.push(renderBinding(receipt,direction.render));
  }
  return bindings;
}
