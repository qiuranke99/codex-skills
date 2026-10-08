import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {AUTHORITY_RENDER_PROFILE,authorityRenderProfile,assertAuthorityRenderProfile,assertRenderEnvironment,resolveAuthorityRenderProfile,renderBinding} from '../runtime/render-profile.mjs';
import {renderProject,exportProject,withBrowser} from '../runtime/browser-tools.mjs';
import {recipeCatalog,validateParameters} from '../runtime/shader-adapter.mjs';
import {createProject,commitSnapshot,loadProject,engineDigest,fileReference,verifyReference,verifyFileReference,checkProject,atomicJSON} from '../runtime/project-store.mjs';
import {decodePNG} from '../runtime/media-contract.mjs';

const rejected=error=>error.code==='RENDER_PROFILE_MISMATCH';
const hash=char=>char.repeat(64);
const environment=()=>({viewport:{width:1440,height:1000},deviceScaleFactor:1,colorScheme:'light',reducedMotion:'reduce',dynamicRange:'sdr',canvas:{width:961,height:649,colorSpace:'srgb',toneMapping:'standard',format:'bgra8unorm'}});
function receipt() {
  return {schemaVersion:1,kind:'actual-shader-frame',directionId:'synthetic-study',snapshotDigest:hash('a'),engineDigest:hash('b'),renderProfile:structuredClone(AUTHORITY_RENDER_PROFILE),output:{path:'posters/synthetic.png',sha256:hash('c')},pixels:{width:961,height:649,decodedDigest:hash('d')}};
}

test('authority profile is immutable and resolution returns an isolated complete value',()=>{
  assert.equal(authorityRenderProfile,AUTHORITY_RENDER_PROFILE);
  assert.ok(Object.isFrozen(AUTHORITY_RENDER_PROFILE));assert.ok(Object.isFrozen(AUTHORITY_RENDER_PROFILE.viewport));
  const resolved=resolveAuthorityRenderProfile();assert.deepEqual(resolved,AUTHORITY_RENDER_PROFILE);
  resolved.viewport.width=390;assert.equal(AUTHORITY_RENDER_PROFILE.viewport.width,1440);
  assert.deepEqual(resolveAuthorityRenderProfile({url:'http://127.0.0.1:1234',chromiumPath:'synthetic-browser',renderProfile:structuredClone(AUTHORITY_RENDER_PROFILE),viewport:{width:1440,height:1000},deviceScaleFactor:1,colorScheme:'light',reducedMotion:'reduce',dynamicRange:'sdr',colorSpace:'srgb'}),AUTHORITY_RENDER_PROFILE);
});

test('authority settings reject responsive sizes, alternate DPR/preferences/color and silently ignored options',()=>{
  for(const options of [{viewport:{width:390,height:844}},{viewport:{width:1440,height:1000,extra:1}},{viewport:{width:NaN,height:1000}},{deviceScaleFactor:2},{deviceScaleFactor:undefined},{colorScheme:'dark'},{reducedMotion:'no-preference'},{dynamicRange:'hdr'},{colorSpace:'display-p3'},{dpr:1},{isMobile:true},{renderProfile:undefined},null,[]]) assert.throws(()=>resolveAuthorityRenderProfile(options),rejected,JSON.stringify(options));
});

test('stored profiles require all fields and reject unknown, malformed or changed version values',()=>{
  for(const change of [{schemaVersion:2},{id:'different-layout'},{viewport:null},{deviceScaleFactor:Infinity},{extra:'unrecorded'}]) assert.throws(()=>assertAuthorityRenderProfile({...AUTHORITY_RENDER_PROFILE,...change}),rejected);
  const missing=structuredClone(AUTHORITY_RENDER_PROFILE);delete missing.colorSpace;assert.throws(()=>assertAuthorityRenderProfile(missing),rejected);
  assert.throws(()=>assertAuthorityRenderProfile(null),rejected);
});

test('actual render environment must agree with declared profile and decoded canvas dimensions',()=>{
  const profile=structuredClone(AUTHORITY_RENDER_PROFILE),actual=environment();assert.deepEqual(assertRenderEnvironment(profile,actual,{width:961,height:649}),actual);
  assert.doesNotThrow(()=>assertRenderEnvironment(profile,actual));
  for(const change of [e=>{e.viewport={width:390,height:844};},e=>{e.deviceScaleFactor=2;},e=>{e.colorScheme='dark';},e=>{e.reducedMotion='no-preference';},e=>{e.dynamicRange='hdr';},e=>{e.canvas.colorSpace='display-p3';},e=>{e.canvas.toneMapping='extended';},e=>{e.canvas.width=0;},e=>{e.canvas.height=NaN;},e=>{e.canvas.width=962;},e=>{delete e.canvas;}]) {
    const value=environment();change(value);assert.throws(()=>assertRenderEnvironment(profile,value,{width:961,height:649}),rejected);
  }
  assert.throws(()=>assertRenderEnvironment(profile,actual,{width:961,height:Infinity}),rejected);
  assert.throws(()=>assertRenderEnvironment(profile,null),rejected);
});

test('render bindings preserve stable output identity across identical re-captures without aliasing',()=>{
  const input=receipt(),ref={path:'evidence/render-synthetic.json',sha256:hash('e')},binding=renderBinding(input,ref);
  assert.deepEqual(binding,{directionId:input.directionId,snapshotDigest:input.snapshotDigest,engineDigest:input.engineDigest,renderProfile:AUTHORITY_RENDER_PROFILE,output:input.output,pixels:input.pixels,composition:null});
  assert.deepEqual(renderBinding({...input,createdAt:'another-capture-time'},{...ref,sha256:hash('f')}),binding);
  input.renderProfile.viewport.width=390;input.output.sha256=hash('f');ref.sha256=hash('f');
  assert.equal(binding.renderProfile.viewport.width,1440);assert.equal(binding.output.sha256,hash('c'));
});

test('composition bindings include actual output, pixel and scene identities and require enabled complete evidence',()=>{
  const value=receipt();value.composition={enabled:true,sourceDigest:hash('e'),output:{path:'compositions/synthetic.png',sha256:hash('f')},pixels:{width:961,height:649,decodedDigest:hash('a')}};
  const binding=renderBinding(value);assert.deepEqual(binding.composition,{enabled:true,sceneDigest:hash('e'),output:value.composition.output,pixels:value.composition.pixels});
  value.composition.pixels.width=800;assert.equal(binding.composition.pixels.width,961);assert.notDeepEqual(renderBinding(value),binding);
  for(const mutate of [r=>{r.composition.enabled=false;},r=>{r.composition.sourceDigest='';},r=>{r.composition.output.sha256='';},r=>{r.composition.pixels.decodedDigest='';},r=>{r.composition.pixels.height=0;}]) {const r=structuredClone(value);mutate(r);assert.throws(()=>renderBinding(r),rejected);}
});

test('render bindings reject incomplete output hashes, pixel hashes or dimensions',()=>{
  for(const mutate of [r=>{r.output.sha256='';},r=>{r.pixels.decodedDigest='not-a-sha256';},r=>{r.pixels.width=0;},r=>{r.pixels.height=NaN;},r=>{r.engineDigest=undefined;},r=>{r.renderProfile.viewport.width=390;},r=>{r.kind='declared-frame';}]) {
    const value=receipt();mutate(value);assert.throws(()=>renderBinding(value,{path:'evidence/render.json',sha256:hash('e')}),rejected);
  }
});

test('authority entry points reject a different profile before filesystem access or browser launch',async()=>{
  const absent=path.resolve('this-project-does-not-exist-render-profile-selfcheck');
  for(const options of [{viewport:{width:390,height:844}},{deviceScaleFactor:2},{colorScheme:'dark'},{renderProfile:{...AUTHORITY_RENDER_PROFILE,colorSpace:'display-p3'}}]) {
    await assert.rejects(renderProject(absent,options),rejected);
    await assert.rejects(exportProject(absent,{format:'png',...options}),rejected);
    await assert.rejects(exportProject(absent,{format:'pdf',...options}),rejected);
  }
});

function syntheticProject() {
  return {schemaVersion:1,project:{id:'synthetic-authority-profile',title:'合成测试 · 固定权威采集规格',medium:'synthetic-functional-study'},
    brief:{decision:'核对响应式预览不能覆盖权威保存画面。',objectSuccess:['真实GPU输出与像素绑定'],carrierSuccess:['规范采集尺寸固定且变更明确失败'],locks:['仅作功能自检'],openVariables:['有限参数']},
    benchmarks:{revision:'synthetic-profile-1',object:[],carrier:[]},
    directions:recipeCatalog.map((recipe,index)=>({id:`study-${index+1}`,title:recipe.title,subtitle:recipe.mechanism,description:recipe.description,claim:'合成测试',caption:`Synthetic profile study ${index+1}`,recipeId:recipe.id,parameters:validateParameters(recipe.id,{}),hypothesis:{question:'权威画面是否固定？',mechanism:recipe.mechanism,expected:'受控viewport与像素绑定',failure:'响应式预览污染保存状态'},handoff:{adopt:['固定规格和实际像素证据'],exclude:['商业品质结论'],unproven:['独立验收和用户接受']},quality:{object:{status:'unverified'},carrier:{status:'unverified'}}})),
  };
}

test('actual GPU authority rejects mobile overwrite, permits responsive preview, and invalidates a replaced render binding',{skip:process.env.VEM_RENDER_PROFILE_TEST!=='1',timeout:180000},async()=>{
  assert.ok(process.env.VEM_RENDER_PROFILE_DIR,'Set an external VEM_RENDER_PROFILE_DIR for private artifacts');
  const base=path.resolve(process.env.VEM_RENDER_PROFILE_DIR);await fs.mkdir(base,{recursive:true});
  const root=await fs.mkdtemp(path.join(base,'run-'));await createProject(root,syntheticProject());
  for(const direction of (await loadProject(root)).directions) await commitSnapshot(root,{directionId:direction.id,parameters:direction.parameters,timeSeconds:3.75});
  const build=await engineDigest();
  const rendered=await renderProject(root,{viewport:{width:1440,height:1000},renderProfile:structuredClone(AUTHORITY_RENDER_PROFILE)});
  for(const r of rendered) {assert.deepEqual(r.renderProfile,AUTHORITY_RENDER_PROFILE);assert.equal(r.renderEnvironment.deviceScaleFactor,1);assert.equal(r.renderEnvironment.canvas.colorSpace,'srgb');assert.equal(r.renderEnvironment.canvas.toneMapping,'standard');assert.ok(r.gpu.observation.currentFrameReadbackVerified);}
  const before=await loadProject(root),poster=(await verifyReference(root,before.directions[0].render)).output.path;
  const observedContradictions=[];
  for(const mutate of [r=>{r.renderEnvironment.viewport={width:390,height:844};r.renderEnvironment.deviceScaleFactor=2;},r=>{r.renderEnvironment.canvas.width+=1;}]) {
    const changed=await loadProject(root),direction=changed.directions[0],original=await verifyReference(root,direction.render),invalid=structuredClone(original);mutate(invalid);
    await atomicJSON(path.join(root,direction.render.path),invalid);direction.render=await fileReference(root,direction.render.path);await atomicJSON(path.join(root,'project.json'),changed);
    const checks=await checkProject(root,{scope:'technical'});assert.equal(checks.status,'FAIL');assert.ok(checks.findings.some(f=>f.code==='RENDER_PROFILE_MISMATCH'));observedContradictions.push(checks);
    await atomicJSON(path.join(root,direction.render.path),original);direction.render=await fileReference(root,direction.render.path);await atomicJSON(path.join(root,'project.json'),changed);
  }
  const bytes=await fs.readFile(path.join(root,poster)),beforeHash=createHash('sha256').update(bytes).digest('hex');
  await assert.rejects(renderProject(root,{viewport:{width:390,height:844}}),rejected);
  await assert.rejects(exportProject(root,{format:'png',viewport:{width:390,height:844}}),rejected);
  const preview=await withBrowser(root,{viewport:{width:390,height:844}},async({page})=>page.evaluate(()=>({viewport:{width:innerWidth,height:innerHeight},canvas:{width:document.querySelector('#study-canvas').width,height:document.querySelector('#study-canvas').height}})));
  assert.deepEqual(preview.viewport,{width:390,height:844});assert.notEqual(preview.canvas.width,rendered[0].pixels.width);
  assert.equal(createHash('sha256').update(await fs.readFile(path.join(root,poster))).digest('hex'),beforeHash);
  const overviewText=await withBrowser(root,{},async({page})=>{
    await page.evaluate(()=>window.VEM.preparePrint());
    const figures=await page.locator('#print-directions .compare-item').allTextContents();
    const comparisons=await page.locator('#compare-details .compare-item').allTextContents();
    await page.evaluate(()=>window.VEM.finishPrint());return {figures,comparisons};
  });
  for(const texts of [overviewText.figures,overviewText.comparisons]) {
    assert.equal(texts.length,3);
    for(const [index,direction] of before.directions.entries()) {assert.ok(texts[index].includes(direction.caption));assert.ok(texts[index].includes(direction.description));}
  }
  const exported=await exportProject(root,{format:'png',deviceScaleFactor:1,colorScheme:'light',reducedMotion:'reduce',dynamicRange:'sdr',colorSpace:'srgb'});
  const pdf=await exportProject(root,{format:'pdf',renderProfile:structuredClone(AUTHORITY_RENDER_PROFILE)});
  assert.deepEqual(pdf.renderProfile,AUTHORITY_RENDER_PROFILE);assert.deepEqual(pdf.renderBindings,exported.renderBindings);
  assert.equal((await verifyFileReference(root,pdf.output)).bytes.subarray(0,4).toString(),'%PDF');
  const project=await loadProject(root),bindings=[];
  for(const direction of project.directions) {const saved=await verifyReference(root,direction.render);await verifyFileReference(root,saved.output);bindings.push(renderBinding(saved,direction.render));}
  assert.deepEqual(exported.renderProfile,AUTHORITY_RENDER_PROFILE);assert.deepEqual(exported.renderBindings,bindings);
  const checks=await checkProject(root,{scope:'technical'});assert.equal(checks.status,'PASS',JSON.stringify(checks));
  const delivery=await checkProject(root,{scope:'delivery'});assert.equal(delivery.findings.find(f=>f.code==='PNG_EXPORT')?.status,'PASS',JSON.stringify(delivery));
  await renderProject(root);
  const repeated=await checkProject(root,{scope:'delivery'});assert.equal(repeated.findings.find(f=>f.code==='PNG_EXPORT')?.status,'PASS',JSON.stringify(repeated));
  // A distinct captured GPU image cannot replace a direction's poster under its old export.
  const latest=await loadProject(root),direction=latest.directions[0],saved=await verifyReference(root,direction.render),alternate=await verifyReference(root,latest.directions[1].render);
  saved.output=alternate.output;saved.pixels=alternate.pixels;saved.gpu=alternate.gpu;saved.scope='Deliberate synthetic replacement with a distinct actual GPU output; this is invalid evidence';
  await atomicJSON(path.join(root,direction.render.path),saved);direction.render=await fileReference(root,direction.render.path);await atomicJSON(path.join(root,'project.json'),latest);
  const stale=await checkProject(root,{scope:'delivery'}),pngCheck=stale.findings.find(check=>check.code==='STALE_EXPORT');
  assert.ok(pngCheck,JSON.stringify(stale));
  assert.equal(pngCheck.status,'FAIL');assert.equal(pngCheck.code,'STALE_EXPORT');
  const result={root,engineDigest:build,renderProfile:AUTHORITY_RENDER_PROFILE,rendered,observedContradictions,preview,overviewText,exported,pdf,checks,identicalRecapture:repeated,replacedRenderBinding:pngCheck,scope:'Synthetic implementer functional self-check; not independent review or user acceptance'};
  await fs.writeFile(path.join(root,'render-profile-selfcheck.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({root,engineDigest:build,rendered:rendered.length,png:exported.output,stale:pngCheck}));
});

test('actual object and Shader composition is enabled, decoded, visibly toggleable and bound through PNG/PDF',{skip:process.env.VEM_COMPOSITION_TEST!=='1',timeout:180000},async()=>{
  assert.ok(process.env.VEM_RENDER_PROFILE_DIR,'Set an external VEM_RENDER_PROFILE_DIR for private artifacts');
  const base=path.resolve(process.env.VEM_RENDER_PROFILE_DIR);await fs.mkdir(base,{recursive:true});const root=await fs.mkdtemp(path.join(base,'composition-'));
  const input=syntheticProject();input.project.id='synthetic-object-field';input.project.title='合成测试 · 对象与程序光同场';await fs.mkdir(path.join(root,'assets'));
  for(const [index,direction] of input.directions.entries()) {
    direction.assets=[];
    for(const role of ['base','mask']) {
      const id=`${role}-${index+1}`,relative=`assets/${id}.svg`;
      const svg=role==='mask'?'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="540"><rect width="800" height="540" fill="black"/><rect x="280" y="125" width="240" height="310" rx="35" fill="white"/><rect x="305" y="250" width="190" height="106" rx="4" fill="black"/></svg>':`<svg xmlns="http://www.w3.org/2000/svg" width="800" height="540"><defs><linearGradient id="body"><stop stop-color="#647a70"/><stop offset=".5" stop-color="#adbbab"/><stop offset="1" stop-color="#5b7064"/></linearGradient></defs><rect width="800" height="540" fill="#e6e2d4"/><ellipse cx="400" cy="454" rx="170" ry="22" fill="#9a9e90"/><rect x="280" y="125" width="240" height="310" rx="35" fill="url(#body)"/><rect x="292" y="84" width="216" height="65" rx="8" fill="#535c57"/><rect x="305" y="250" width="190" height="106" rx="4" fill="#f1eee2"/><text x="400" y="297" text-anchor="middle" font-size="24" fill="#36413b">SYNTHETIC</text><text x="400" y="328" text-anchor="middle" font-size="18" fill="#36413b">STUDY ${index+1}</text></svg>`;
      await fs.writeFile(path.join(root,relative),svg);const sourceRef=await fileReference(root,relative);
      direction.assets.push({id,url:`/media/${relative}`,role:`synthetic composition ${role}`,caption:`Synthetic ${role} ${index+1}`,presentation:'composition-only',sourceRef,rights:{status:'self-owned',display:true,redistribution:true,evidenceRef:sourceRef},authorization:{operations:['display'],regions:['whole-asset'],immutableProperties:[]},operation:{type:'display',region:'whole-asset',affectedProperties:[],authorizationRef:sourceRef}});
    }
    const subject=direction.assets[0],mask=direction.assets[1];
    subject.authorization={operations:['subject-color-material'],regions:['body'],immutableProperties:['geometry']};
    subject.operation={type:'subject-color-material',region:'body',affectedProperties:['body-light'],authorizationRef:subject.sourceRef,parentRefs:[subject.sourceRef],maskRef:mask.sourceRef};
    direction.studyComposition={baseAssetId:`base-${index+1}`,maskAssetId:`mask-${index+1}`,opacity:0.65,blendMode:'multiply',aspectRatio:800/540,purpose:'合成测试：把真实程序光限制在对象身体区域'};
  }
  await createProject(root,input);for(const direction of (await loadProject(root)).directions) await commitSnapshot(root,{directionId:direction.id,parameters:direction.parameters,timeSeconds:3.75});
  const build=await engineDigest(),rendered=await renderProject(root);
  for(const r of rendered) {assert.equal(r.composition.enabled,true);assert.equal(r.composition.observation.decoded,true);assert.equal(r.composition.assets.base.width,800);assert.equal(r.composition.assets.mask.height,540);assert.notEqual(r.composition.pixels.decodedDigest,r.pixels.decodedDigest);await verifyFileReference(root,r.composition.output);}
  const project=await loadProject(root);for(const direction of project.directions) assert.ok(direction.compositionPoster?.startsWith('/media/compositions/'));
  const compositionContradictions=[];
  for(const mutate of [r=>{r.composition.observation.decoded=false;},r=>{r.composition.assets.base.width=0;},r=>{r.composition.assets.base.width=1;r.composition.assets.base.height=1;},r=>{r.composition.assets.mask.width+=1;},r=>{r.composition.assets.styles.opacity=0;},r=>{r.composition.assets.stage.width+=10;}]) {
    const changed=await loadProject(root),direction=changed.directions[0],original=await verifyReference(root,direction.render),invalid=structuredClone(original);mutate(invalid);
    await atomicJSON(path.join(root,direction.render.path),invalid);direction.render=await fileReference(root,direction.render.path);await atomicJSON(path.join(root,'project.json'),changed);
    const checks=await checkProject(root,{scope:'technical'});assert.equal(checks.status,'FAIL',JSON.stringify(checks));assert.ok(checks.findings.some(f=>f.code.startsWith('COMPOSITION_')&&f.status==='FAIL'));compositionContradictions.push(checks);
    await atomicJSON(path.join(root,direction.render.path),original);direction.render=await fileReference(root,direction.render.path);await atomicJSON(path.join(root,'project.json'),changed);
  }
  const toggle=await withBrowser(root,{},async({page})=>{
    const direction=project.directions[0];await page.evaluate(async d=>{await window.VEM.setDirection(d.id);await window.VEM.pause();await window.VEM.setParameters(d.snapshot.parameters);await window.VEM.seek(d.snapshot.timeSeconds);document.querySelectorAll('#shader-stage .stage-mode,#shader-stage .stage-corner').forEach(el=>el.style.visibility='hidden');window.__compositionCanvas=document.querySelector('#study-canvas');},direction);
    await page.evaluate(()=>window.VEM.setCompositionEnabled(true));const onState=await page.evaluate(()=>window.VEM.getState());const on=decodePNG(await page.locator('#shader-stage').screenshot());
    await page.evaluate(()=>window.VEM.setCompositionEnabled(false));const offState=await page.evaluate(()=>window.VEM.getState());const offBytes=await page.locator('#shader-stage').screenshot(),off=decodePNG(offBytes);await fs.writeFile(path.join(root,'composition-toggle-off.png'),offBytes);
    const sameCanvas=await page.evaluate(()=>window.__compositionCanvas===document.querySelector('#study-canvas'));await page.evaluate(()=>window.VEM.setCompositionEnabled(true));
    assert.equal(onState.composition.enabled,true);assert.equal(offState.composition.enabled,false);assert.equal(sameCanvas,true);assert.notEqual(on.pixelDigest,off.pixelDigest);assert.equal(onState.gpu.lastReadback.pixelDigest,offState.gpu.lastReadback.pixelDigest);
    return {on:{width:on.width,height:on.height,decodedDigest:on.pixelDigest},off:{width:off.width,height:off.height,decodedDigest:off.pixelDigest},sameCanvas};
  });
  const captureRefs=project.directions.map(d=>structuredClone(d.render));
  const png=await exportProject(root,{format:'png'}),pdf=await exportProject(root,{format:'pdf'});assert.deepEqual(png.renderBindings,pdf.renderBindings);assert.ok(png.renderBindings.every(row=>row.composition?.sceneDigest&&row.composition.output.sha256));
  assert.deepEqual((await loadProject(root)).directions.map(d=>d.render),captureRefs,'Changing export format must not recapture valid authoritative frames');
  const technical=await checkProject(root,{scope:'technical'});assert.equal(technical.status,'PASS',JSON.stringify(technical));const delivery=await checkProject(root,{scope:'delivery'});assert.equal(delivery.findings.find(f=>f.code==='PNG_EXPORT')?.status,'PASS',JSON.stringify(delivery));
  const latest=await loadProject(root),first=latest.directions[0],current=await verifyReference(root,first.render),alternate=await verifyReference(root,latest.directions[1].render);current.composition.output=alternate.composition.output;current.composition.pixels=alternate.composition.pixels;
  await atomicJSON(path.join(root,first.render.path),current);first.render=await fileReference(root,first.render.path);await atomicJSON(path.join(root,'project.json'),latest);
  const stale=await checkProject(root,{scope:'delivery'});assert.ok(stale.findings.some(f=>f.code==='STALE_EXPORT'&&f.status==='FAIL'),JSON.stringify(stale));
  // Malformed existing evidence cannot be silently regenerated by export.
  current.composition.assets.base.width=1;await atomicJSON(path.join(root,first.render.path),current);first.render=await fileReference(root,first.render.path);await atomicJSON(path.join(root,'project.json'),latest);
  const damagedRef=structuredClone(first.render);await assert.rejects(exportProject(root,{format:'png'}),error=>error.code==='COMPOSITION_MISMATCH');
  assert.deepEqual((await loadProject(root)).directions[0].render,damagedRef);
  const result={root,engineDigest:build,rendered,compositionContradictions,toggle,png,pdf,technical,delivery,compositionReplacement:stale,scope:'Synthetic participating implementation self-check; final project deliberately contains invalid replacement evidence'};await fs.writeFile(path.join(root,'composition-selfcheck.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({root,engineDigest:build,rendered:rendered.length,png:png.output,pdf:pdf.output,toggle}));
});
