import test from 'node:test';
import assert from 'node:assert/strict';
import {recipeCatalog,getRecipe,validateParameters,validateRecipe,validateComponentTree,makePreset,createShaderStudy} from '../runtime/shader-adapter.mjs';

test('original catalog resolves complete bounded parameters and has distinct mechanisms',()=>{
  assert.equal(new Set(recipeCatalog.map(value=>value.mechanism)).size,recipeCatalog.length);
  for(const recipe of recipeCatalog){
    assert.equal(validateRecipe(recipe),recipe);
    assert.deepEqual(validateParameters(recipe.id,{}),Object.fromEntries(Object.entries(recipe.parameters).map(([key,c])=>[key,c.default])));
    assert.deepEqual(makePreset(recipe.id).components[0].props,recipe.componentTree.components[0].props);
    assert.equal(recipe.reconstruction.kind,'stateless-analytic');
  }
});

test('parameters reject unknown, poison, coercion, ranges and noninteger structure',()=>{
  const bad=[{typo:1},{tempo:NaN},{tempo:Infinity},{tempo:'1'},{tempo:null},{tempo:undefined},{tempo:-1},{tempo:100},{discipline:4.5}];
  for(const value of bad) assert.throws(()=>validateParameters('luminous-order',value));
  assert.throws(()=>validateParameters('luminous-order',[]));
  assert.throws(()=>validateParameters('missing',{}),/Unsupported recipe/);
  assert.throws(()=>validateParameters('luminous-order',JSON.parse('{"__proto__":{}}')),/not supported/);
});

test('strict tree cannot silently skip components, props, layers, resources or defaults',()=>{
  const recipe=getRecipe('luminous-order');
  const mutate=fn=>{const value=structuredClone(recipe.componentTree);fn(value);return value;};
  const bad=[
    mutate(value=>value.components[0].type='Fog'),
    mutate(value=>value.components[0].props.fill='cover'),
    mutate(value=>value.components[0].props.src='https://invalid.test/private.png'),
    mutate(value=>delete value.components[0].props.tempo),
    mutate(value=>value.components[0].props.tempo=NaN),
    mutate(value=>value.components[0].props.visible=false),
    mutate(value=>value.components[0].props.opacity=0),
    mutate(value=>value.components[0].id='preset-root'),
    mutate(value=>value.components.push(structuredClone(value.components[0]))),
    mutate(value=>value.components[0].children.push(structuredClone(value.components[0]))),
    mutate(value=>value.structureVersion=0),
  ];
  for(const tree of bad) assert.throws(()=>validateComponentTree(tree,recipe.id));
});

test('frozen recipe rejects version drift, changed trees, declared media and contract drift',()=>{
  for(const mutate of [value=>value.upstream.version='4.0.3',value=>value.revision=9,value=>value.adapterVersion='0',value=>value.resources=['a.png'],value=>value.componentTree.components[0].props.tempo=1,value=>value.parameters.tempo.min=-1]) {
    const recipe=structuredClone(recipeCatalog[0]);mutate(recipe);assert.throws(()=>validateRecipe(recipe));
  }
  assert.ok(Object.isFrozen(recipeCatalog[0].componentTree.components[0].props));
});

test('invalid canvas fails before GPU import or allocation',async()=>{
  await assert.rejects(createShaderStudy(null,recipeCatalog[0],{}),/HTML canvas/);
  await assert.rejects(createShaderStudy({getContext(){},toBlob(){},width:0,height:100},recipeCatalog[0],{}),/dimensions/);
});

// Opt in on a real WebGPU browser. This test starts a disposable loopback server,
// uses the installed dependency and inspects actual decoded pixels, not a mock renderer.
test('real core GPU draws distinct studies, restores state, pauses, and detects loss/empty output', {skip:process.env.VEM_GPU_TEST!=='1',timeout:120000},async()=>{
  const [{build},{chromium},{createServer},{once}]=await Promise.all([import('esbuild'),import('playwright'),import('node:http'),import('node:events')]);
  const {fileURLToPath}=await import('node:url');
  const {resolve,relative,isAbsolute}=await import('node:path');
  const {mkdir,writeFile}=await import('node:fs/promises');
  const {readFile}=await import('node:fs/promises');
  const {createHash}=await import('node:crypto');
  const packageRoot=fileURLToPath(new URL('..',import.meta.url));
  let artifactDirectory=null;
  if(process.env.VEM_GPU_ARTIFACT_DIR) {
    artifactDirectory=resolve(process.env.VEM_GPU_ARTIFACT_DIR);
    const rel=relative(packageRoot,artifactDirectory);
    if(!rel || (!rel.startsWith('..') && !isAbsolute(rel))) throw new Error('GPU media evidence must stay outside the public source package');
    await mkdir(artifactDirectory,{recursive:true});
  }
  const bundle=await build({stdin:{contents:`import * as adapter from './runtime/shader-adapter.mjs'; import {destroyDefaultGpuDevice} from 'shaders/core'; window.adapter=adapter; window.loseGpu=destroyDefaultGpuDevice; window.harnessReady=true;`,resolveDir:packageRoot},bundle:true,format:'esm',platform:'browser',write:false,logLevel:'silent'});
  const html='<!doctype html><meta charset="utf-8"><div style="width:800px;height:500px"><canvas id="study" width="800" height="500" style="width:100%;height:100%;display:block"></canvas></div><script type="module" src="/bundle.js"></script>';
  const server=createServer((request,response)=>{
    if(request.url==='/bundle.js'){response.writeHead(200,{'Content-Type':'text/javascript'});response.end(bundle.outputFiles[0].text);}
    else if(request.url==='/'){response.writeHead(200,{'Content-Type':'text/html'});response.end(html);}
    else {response.writeHead(404);response.end();}
  }).listen(0,'127.0.0.1');
  await once(server,'listening');
  const address=`http://127.0.0.1:${server.address().port}`;
  let browser;
  const observations=[];
  try {
    browser=await chromium.launch({headless:true,...(process.env.VEM_CHROMIUM_PATH?{executablePath:process.env.VEM_CHROMIUM_PATH}:{})});
    const context=await browser.newContext({viewport:{width:1000,height:700},deviceScaleFactor:1});
    await context.route('**/*',route=>new URL(route.request().url()).origin===address?route.continue():route.abort());
    const page=await context.newPage();
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto(address);await page.waitForFunction(()=>window.harnessReady);
    for(const recipe of recipeCatalog){
      const result=await page.evaluate(async id=>{
        const recipe=window.adapter.getRecipe(id),canvas=document.querySelector('canvas');
        window.study=await window.adapter.createShaderStudy(canvas,recipe,{});
        const initial=window.study.getState();
        if(initial.failure) return {initial};
        await window.study.renderAt(4.25);const first=window.study.getState();
        await window.study.renderAt(8);const later=window.study.getState();
        await window.study.renderAt(4.25);const restored=window.study.getState();
        window.study.resume();await new Promise(resolve=>setTimeout(resolve,250));await window.study.pause();
        const paused=window.study.getState();await new Promise(resolve=>setTimeout(resolve,150));const still=window.study.getState();
        await window.study.destroy();
        window.study=await window.adapter.createShaderStudy(canvas,recipe,{});await window.study.renderAt(4.25);const rebuilt=window.study.getState();
        const key=Object.keys(recipe.parameters).find(key=>key!=='tempo');
        await window.study.setParameters({...rebuilt.parameters,[key]:recipe.parameters[key].min});const changed=window.study.getState();
        return {initial,first,later,restored,paused,still,rebuilt,changed};
      },recipe.id);
      observations.push({recipeId:recipe.id,...result});
      assert.equal(result.initial.gpu.status,'ready',JSON.stringify(result.initial));
      assert.equal(result.initial.gpu.deviceCreated,true);
      assert.ok(result.initial.gpu.readbackCount>0);
      assert.notEqual(result.first.gpu.lastReadback.pixelDigest,result.later.gpu.lastReadback.pixelDigest,'Time must have a visible effect');
      assert.equal(result.first.gpu.lastReadback.pixelDigest,result.restored.gpu.lastReadback.pixelDigest,'Backward seek must restore the stateless frame');
      assert.equal(result.first.gpu.lastReadback.pixelDigest,result.rebuilt.gpu.lastReadback.pixelDigest,'Fresh reconstruction must restore the same supported frame');
      assert.equal(result.paused.timeSeconds,result.still.timeSeconds);
      assert.equal(result.paused.gpu.drawCount,result.still.gpu.drawCount);
      assert.notEqual(result.rebuilt.gpu.lastReadback.pixelDigest,result.changed.gpu.lastReadback.pixelDigest,'Art direction parameter must affect actual pixels');
      if(artifactDirectory) {
        await page.evaluate(async()=>{await window.study.renderAt(4.25);});
        await page.locator('canvas').screenshot({path:resolve(artifactDirectory,`${recipe.id}-changed-4.25s.png`)});
        await page.evaluate(async id=>{await window.study.setParameters(window.adapter.validateParameters(id,{}));await window.study.renderAt(4.25);},recipe.id);
        await page.locator('canvas').screenshot({path:resolve(artifactDirectory,`${recipe.id}-default-4.25s.png`)});
      }
      await page.evaluate(async()=>{await window.study.destroy();});
    }
    const empty=await page.evaluate(async()=>{
      const canvas=document.querySelector('canvas'),blank=document.createElement('canvas');blank.width=canvas.width;blank.height=canvas.height;
      const original=canvas.toBlob.bind(canvas);canvas.toBlob=blank.toBlob.bind(blank);
      const study=await window.adapter.createShaderStudy(canvas,window.adapter.recipeCatalog[0],{});const result=study.getState();await study.destroy();canvas.toBlob=original;return result;
    });
    assert.equal(empty.failure?.code,'EMPTY_GPU_OUTPUT');
    const loss=await page.evaluate(async()=>{
      window.study=await window.adapter.createShaderStudy(document.querySelector('canvas'),window.adapter.recipeCatalog[0],{});
      window.loseGpu();await new Promise(resolve=>setTimeout(resolve,100));return window.study.getState();
    });
    assert.equal(loss.gpu.status,'failed');assert.ok(loss.failure);
    const unavailableContext=await browser.newContext();
    await unavailableContext.addInitScript(()=>Object.defineProperty(navigator,'gpu',{value:undefined,configurable:true}));
    const noGpu=await unavailableContext.newPage();await noGpu.goto(address);await noGpu.waitForFunction(()=>window.harnessReady);
    const unavailable=await noGpu.evaluate(async()=>{
      const study=await window.adapter.createShaderStudy(document.querySelector('canvas'),window.adapter.recipeCatalog[0],{});return study.getState();
    });
    assert.equal(unavailable.gpu.status,'failed');assert.equal(unavailable.gpu.deviceCreated,false);assert.equal(unavailable.gpu.readbackCount,0);
    assert.deepEqual(errors,[]);
    const sourceHashes={};
    for(const filename of ['runtime/shader-adapter.mjs','assets/recipes/catalog.mjs','assets/recipes/original-fields.mjs','tests/shader-contract.test.mjs']) sourceHashes[filename]=createHash('sha256').update(await readFile(resolve(packageRoot,filename))).digest('hex');
    const report={recordedAt:new Date().toISOString(),sourceHashes,browser:browser.version(),gpu:observations,empty,loss,unavailable,scope:'Implementation self-check; pixel/state checks do not prove artistic quality or independent acceptance'};
    if(artifactDirectory) await writeFile(resolve(artifactDirectory,'shader-gpu-selfcheck.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify({browser:report.browser,studies:observations.map(({recipeId,initial,first,later,restored,rebuilt,paused,still,changed})=>({recipeId,gpuStatus:initial.gpu.status,actual:[initial.gpu.width,initial.gpu.height],readback:first.gpu.lastReadback,visibleTimeChange:first.gpu.lastReadback.pixelDigest!==later.gpu.lastReadback.pixelDigest,backwardSeekMatch:first.gpu.lastReadback.pixelDigest===restored.gpu.lastReadback.pixelDigest,rebuildMatch:first.gpu.lastReadback.pixelDigest===rebuilt.gpu.lastReadback.pixelDigest,pauseStable:paused.timeSeconds===still.timeSeconds,parameterVisible:first.gpu.lastReadback.pixelDigest!==changed.gpu.lastReadback.pixelDigest})),empty:empty.failure,loss:loss.failure,unavailable:unavailable.failure,artifactDirectory}));
  } finally {
    await browser?.close();server.close();await once(server,'close');
  }
});
