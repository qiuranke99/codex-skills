import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createServer} from 'node:net';
import {once} from 'node:events';
import {request as httpRequest} from 'node:http';
import {recipeCatalog,validateParameters} from '../runtime/shader-adapter.mjs';
import {createProject,commitSnapshot,loadProject,checkProject,verifyFileReference,engineDigest} from '../runtime/project-store.mjs';
import {startServer} from '../runtime/server.mjs';
import {renderProject,exportProject,withBrowser} from '../runtime/browser-tools.mjs';

export function syntheticProject() {
  return {schemaVersion:1,project:{id:'synthetic-integration',title:'合成工程 · 视觉关系研究',subtitle:'功能与状态绑定自检，未作商业或获奖品质判断',medium:'synthetic-functional-study'},
    brief:{decision:'核对三种程序关系能否从保存状态重开并准确导出。',objectSuccess:['当前状态真实GPU绘制','三套关系具有不同空间组织'],carrierSuccess:['能够调参、暂停、保存和导出','中英文与方向说明可读'],locks:['这是明确标记的合成测试，不作真人批准记录'],openVariables:['已定义参数','分析时钟']},
    benchmarks:{revision:'synthetic-baseline-1',object:[{id:'synthetic-object',url:'https://example.invalid/synthetic-object',reason:'故意未观察的合成基线',observe:'未观察',criticalGap:'不用于艺术质量结论',observed:false}],carrier:[{id:'synthetic-carrier',url:'https://example.invalid/synthetic-carrier',reason:'故意未观察的合成基线',observe:'未观察',criticalGap:'不用于艺术质量结论',observed:false}]},
    directions:recipeCatalog.map((recipe,index)=>({id:`study-${index+1}`,title:recipe.title,subtitle:recipe.mechanism,description:recipe.description,claim:'仅作程序关系与功能验证',hypothesis:{question:'保存状态是否对应实际输出？',mechanism:recipe.mechanism,expected:'时间、参数和图像绑定当前快照',failure:'空画面、状态漂移或错误引用'},handoff:{adopt:['可重建的程序关系及有效参数'],exclude:['未知产品、人物和品牌身份'],unproven:['获奖品质、最终生产与用户接受']},recipeId:recipe.id,parameters:validateParameters(recipe.id,{}),quality:{object:{status:'unverified',evidence:[],issues:['未独立审阅']},carrier:{status:'unverified',evidence:[],issues:['未独立审阅']}},palette:['#173331','#dfc39e','#f2e8d4']})),
  };
}

async function fixture(t) {
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'vem-server-export-'));
  t.after(async()=>{assert.ok(path.basename(directory).startsWith('vem-server-export-'));await fs.rm(directory,{recursive:true,force:true});});
  await createProject(directory,syntheticProject());return directory;
}

test('loopback routes expose the board and supported recipes, protect mutations and media paths',async t=>{
  const root=await fixture(t),service=await startServer(root);t.after(()=>service.close());
  const request=(route,options={})=>fetch(`${service.url}${route}`,options);
  const project=await request('/api/project');assert.equal(project.status,200);assert.equal((await project.json()).project.id,'synthetic-integration');
  const recipe=await request(`/api/recipe/${recipeCatalog[0].id}`);assert.equal(recipe.status,200);assert.equal((await recipe.json()).id,recipeCatalog[0].id);
  assert.equal((await request('/api/recipe/unknown')).status,400);
  const board=await request('/');assert.equal(board.status,200);assert.match(await board.text(),/study-canvas/);
  const bundle=await request('/bundle/board.js');assert.equal(bundle.status,200);assert.ok((await bundle.arrayBuffer()).byteLength>1000);
  const head=await request('/',{method:'HEAD'});assert.equal(head.status,200);assert.equal(await head.text(),'');
  const hostileHost=await new Promise((resolve,reject)=>{
    const req=httpRequest(`${service.url}/api/project`,{headers:{Host:'attacker.invalid'}},response=>{response.resume();resolve(response.statusCode);});req.on('error',reject);req.end();
  });
  assert.equal(hostileHost,403);
  for(const origin of [null,'https://attacker.invalid']) {
    const headers={'Content-Type':'application/json',...(origin?{Origin:origin}:{})};
    const rejected=await request('/api/snapshot',{method:'POST',headers,body:JSON.stringify({directionId:'study-1',parameters:{},timeSeconds:1})});assert.equal(rejected.status,403);
  }
  const accepted=await request('/api/snapshot',{method:'POST',headers:{'Content-Type':'application/json',Origin:service.url},body:JSON.stringify({directionId:'study-1',parameters:{},timeSeconds:1})});assert.equal(accepted.status,200);assert.ok((await accepted.json()).snapshot.digest);
  const invalidJSON=await request('/api/snapshot',{method:'POST',headers:{'Content-Type':'application/json',Origin:service.url},body:'{bad'});assert.equal(invalidJSON.status,400);
  const wrongType=await request('/api/snapshot',{method:'POST',headers:{'Content-Type':'text/plain',Origin:service.url},body:'{}'});assert.equal(wrongType.status,400);
  const unknown=await request('/api/snapshot',{method:'POST',headers:{'Content-Type':'application/json',Origin:service.url},body:JSON.stringify({directionId:'study-1',parameters:{unknown:1},timeSeconds:1})});assert.equal(unknown.status,400);
  const observation=await request('/api/observation',{method:'POST',headers:{'Content-Type':'application/json',Origin:service.url},body:JSON.stringify({synthetic:true,scope:'mechanical self-check'})});assert.equal(observation.status,201);
  assert.equal((await request('/media/evidence/baseline-1.json')).status,400);
  assert.equal((await request('/media/assets/%2e%2e%2f%2e%2e%2foutside.png')).status,400);
  assert.equal((await request('/api/export?format=png',{headers:{Origin:'https://attacker.invalid'}})).status,405);
  assert.equal((await request('/api/export',{method:'POST',headers:{'Content-Type':'application/json',Origin:'https://attacker.invalid'},body:'{"format":"png"}'})).status,403);
  assert.equal((await request('/missing')).status,404);
});

test('explicit port conflict fails clearly and default launch can choose a free port',async t=>{
  const root=await fixture(t),occupied=createServer().listen(0,'127.0.0.1');await once(occupied,'listening');
  t.after(()=>new Promise(resolve=>occupied.close(resolve)));
  await assert.rejects(startServer(root,{port:occupied.address().port}),error=>error.code==='EADDRINUSE');
  const service=await startServer(root);t.after(()=>service.close());assert.notEqual(new URL(service.url).port,String(occupied.address().port));
});

test('synthetic integration uses actual GPU posters and produces bound PNG and PDF exports',{skip:process.env.VEM_INTEGRATION_TEST!=='1',timeout:120000},async()=>{
  assert.ok(process.env.VEM_INTEGRATION_DIR,'Set an external VEM_INTEGRATION_DIR for private run artifacts');
  const base=path.resolve(process.env.VEM_INTEGRATION_DIR);await fs.mkdir(base,{recursive:true});
  const root=await fs.mkdtemp(path.join(base,'run-'));
  await fs.mkdir(path.join(root,'assets'),{recursive:true});
  const input=syntheticProject();
  for (const [index,direction] of input.directions.entries()) {
    const relative=`assets/object-${index+1}.svg`;
    await fs.writeFile(path.join(root,relative),`<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><rect width="800" height="400" fill="${['#cec2a3','#a7c8bf','#c7bcce'][index]}"/><text x="60" y="230" font-size="54">Object ${index+1}</text></svg>`);
    const {fileReference}=await import('../runtime/project-store.mjs');
    const sourceRef=await fileReference(root,relative);
    direction.assets=[{url:`/media/${relative}`,role:'synthetic object study',caption:`Distinct subject ${index+1}`,sourceRef,rights:{status:'self-owned',display:true,redistribution:true,evidenceRef:sourceRef},authorization:{operations:['display'],regions:['whole-asset'],immutableProperties:[]},operation:{type:'display',region:'whole-asset',affectedProperties:[],authorizationRef:sourceRef}}];
  }
  await createProject(root,input);
  for(const direction of (await loadProject(root)).directions) await commitSnapshot(root,{directionId:direction.id,parameters:direction.parameters,timeSeconds:4.25});
  const build=await engineDigest();
  const rendered=await renderProject(root);
  assert.equal(rendered.length,3);
  for(const receipt of rendered) {
    assert.equal(receipt.engineDigest,build);assert.equal(receipt.gpu.device,true);assert.ok(receipt.pixels.nonTransparent>0);assert.ok(receipt.gpu.observation.currentFrameReadbackVerified);
    const checked=await verifyFileReference(root,receipt.output);assert.deepEqual([...checked.bytes.subarray(0,8)],[137,80,78,71,13,10,26,10]);
  }
  await withBrowser(root,{},async({page})=>{
    await page.evaluate(()=>window.VEM.preparePrint());
    assert.equal(await page.locator('#print-directions .compare-poster').count(),3);
    assert.equal(await page.locator('#print-directions .compare-asset img').count(),3);
    for(let i=1;i<=3;i++)assert.equal(await page.locator(`#print-directions img[src$="/media/assets/object-${i}.svg"]`).count(),1);
    await page.evaluate(()=>window.VEM.finishPrint());
  });
  const png=await exportProject(root,{format:'png'}),pdf=await exportProject(root,{format:'pdf'});
  for(const receipt of [png,pdf]) {assert.equal(receipt.engineDigest,build);assert.equal(receipt.snapshots.length,3);assert.ok((await verifyFileReference(root,receipt.output)).bytes.length>1000);}
  assert.deepEqual([...(await verifyFileReference(root,png.output)).bytes.subarray(0,8)],[137,80,78,71,13,10,26,10]);
  assert.equal((await verifyFileReference(root,pdf.output)).bytes.subarray(0,4).toString(),'%PDF');
  const technical=await checkProject(root,{scope:'technical'}),delivery=await checkProject(root,{scope:'delivery'});
  assert.equal(technical.status,'PASS',JSON.stringify(technical));assert.notEqual(delivery.status,'PASS');
  const result={root,engineDigest:build,posters:rendered.map(receipt=>receipt.output),png,pdf,technical,delivery,scope:'Synthetic functional integration self-check; not independent review, award quality or a real cross-media user task'};
  await fs.writeFile(path.join(root,'integration-selfcheck.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  // A nonfirst direction must not silently disappear from the saved overview.
  const broken=await loadProject(root),second=broken.directions[1];const {fileReference,atomicJSON}=await import('../runtime/project-store.mjs');
  await fs.writeFile(path.join(root,'assets/corrupt.png'),'SYNTHETIC NON-PNG; never valid media');
  second.assets[0].url='/media/assets/corrupt.png';second.assets[0].sourceRef=await fileReference(root,'assets/corrupt.png');
  await atomicJSON(path.join(root,'project.json'),broken);await commitSnapshot(root,{directionId:second.id,parameters:second.parameters,timeSeconds:second.snapshot.timeSeconds});
  await assert.rejects(exportProject(root,{format:'png'}));
  await fs.writeFile(path.join(root,'corrupt-nonfirst-asset-rejected.json'),JSON.stringify({schemaVersion:1,engineDigest:build,nonfirstDirection:second.id,rejected:true,scope:'Actual browser decode rejects an invalid nonfirst subject asset; earlier successful integration receipts remain bound to their earlier valid snapshots'},null,2));
});
