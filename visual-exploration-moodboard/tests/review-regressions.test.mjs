import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import * as store from '../runtime/project-store.mjs';
import {decodePNG} from '../runtime/media-contract.mjs';
import {validateAsset} from '../runtime/asset-contract.mjs';
import {dependencyIdentity} from '../runtime/dependency-contract.mjs';
import {authorityRenderProfile} from '../runtime/render-profile.mjs';
const input=()=>({schemaVersion:1,project:{id:'review-regression',title:'Independent finding regression'},brief:{decision:'Reject stale or contradictory evidence',objectSuccess:['Actual content'],carrierSuccess:['Current comparison'],locks:[],openVariables:[]},benchmarks:{revision:'baseline-1',object:[],carrier:[]},directions:[{id:'study',title:'Study',recipeId:'luminous-order',parameters:{},hypothesis:{question:'Does content match?',mechanism:'Ordered light',expected:'Current version',failure:'Mismatch'},handoff:{adopt:['Relationship'],exclude:['Identity'],unproven:['Production']},quality:{object:{status:'unverified'},carrier:{status:'unverified'}}}]});
async function fixture(t){const root=await fs.mkdtemp(path.join(os.tmpdir(),'vem-review-regression-'));t.after(async()=>{assert.ok(store.inside(os.tmpdir(),root)&&path.basename(root).startsWith('vem-review-regression-'));await fs.rm(root,{recursive:true,force:true});});return root;}
test('ordinary text cannot masquerade as PNG pixel evidence',()=>{assert.throws(()=>decodePNG(Buffer.from('NOT A PNG; NO GPU EXECUTION')),e=>e.code==='INVALID_PNG');assert.throws(()=>decodePNG(Buffer.from([137,80,78,71,13,10,26,10])),e=>e.code==='INVALID_PNG');});
test('delivery rejects hash-correct placeholder media, host and review order; missing baseline also fails',async t=>{
  const root=await fixture(t);await store.createProject(root,input());await store.commitSnapshot(root,{directionId:'study',parameters:{},timeSeconds:2});const p=await store.loadProject(root),engine=await store.engineDigest(),d=p.directions[0];
  const ref=async(relative,value)=>{await fs.mkdir(path.dirname(path.join(root,relative)),{recursive:true});await fs.writeFile(path.join(root,relative),typeof value==='string'?value:JSON.stringify(value));return store.fileReference(root,relative);};
  const output=await ref('posters/fake.png','NOT A PNG; NO GPU EXECUTION');
  d.render=await ref('evidence/render.json',{schemaVersion:1,kind:'actual-shader-frame',directionId:d.id,snapshotDigest:d.snapshot.digest,engineDigest:engine,renderProfile:authorityRenderProfile,renderEnvironment:{viewport:authorityRenderProfile.viewport,deviceScaleFactor:1,colorScheme:'light',reducedMotion:'reduce',dynamicRange:'sdr',canvas:{colorSpace:'srgb',toneMapping:'standard',width:1,height:1}},browser:{version:'synthetic'},gpu:{device:true,observation:{deviceCreated:true,status:'ready',drawCount:1,currentFrameReadbackVerified:true}},pixels:{nonTransparent:1,width:1,height:1},output});d.poster='/media/posters/fake.png';
  p.host={evidence:await ref('evidence/host.json',{status:'executed',actualModel:'gpt-6.1-sol',actualEffort:'ultra',actualToolActions:1,rawTrace:await ref('evidence/raw.jsonl','plain placeholder; no actual execution')})};
  p.review={evidence:await ref('evidence/review.json',{schemaVersion:1,kind:'independent-art-review',reviewer:'synthetic',participatedInProduction:false,initialReview:await ref('evidence/first.md','No actual review'),independentOrderEvidence:await ref('evidence/order.json',{synthetic:true})})};
  p.exports={png:await ref('evidence/export.json',{schemaVersion:1,kind:'png-overview',browser:{version:'synthetic'},engineDigest:engine,snapshots:[[d.id,d.snapshot.digest]],output})};await store.atomicJSON(path.join(root,'project.json'),p);
  let report=await store.checkProject(root,{scope:'delivery'});assert.equal(report.status,'FAIL');for(const code of ['INVALID_PNG','INVALID_HOST_EVIDENCE','REVIEW_ORDER_INVALID'])assert.ok(report.findings.some(f=>f.code===code),JSON.stringify(report));
  await fs.rm(path.join(root,p.baselineRef.path));report=await store.checkProject(root,{scope:'delivery'});assert.notEqual(report.status,'PASS');assert.ok(report.findings.some(f=>f.code==='MISSING_FILE'));
});
test('baseline binds actual initial content and project identity, and requires an explicit scoped change record',async t=>{
  const root=await fixture(t);await store.createProject(root,input());const project=await store.loadProject(root),baseline=await store.verifyReference(root,project.baselineRef);
  assert.equal(store.digest(baseline.initialProject),baseline.initialProjectDigest);await store.validateBaseline(root,project);
  const original=project.baselineRef;
  const malformed=structuredClone(baseline);delete malformed.initialProject.directions;malformed.initialProjectDigest=store.digest(malformed.initialProject);await store.atomicJSON(path.join(root,'evidence/incomplete.json'),malformed);project.baselineRef=await store.fileReference(root,'evidence/incomplete.json');await assert.rejects(store.validateBaseline(root,project),e=>e.code==='DIRECTIONS_MISSING');project.baselineRef=original;
  baseline.initialProjectDigest='0'.repeat(64);await store.atomicJSON(path.join(root,'evidence/foreign.json'),baseline);project.baselineRef=await store.fileReference(root,'evidence/foreign.json');
  await assert.rejects(store.validateBaseline(root,project),e=>e.code==='BASELINE_BINDING_MISMATCH');project.baselineRef=original;
  project.project.title='Another identity';await assert.rejects(store.validateBaseline(root,project),e=>e.code==='BASELINE_BINDING_MISMATCH');project.project.title=baseline.initialProject.project.title;
  project.brief.decision='Changed actual question';await assert.rejects(store.validateBaseline(root,project),e=>e.code==='BASELINE_CHANGE_MISSING');
  const change={schemaVersion:1,kind:'baseline-change',baselineSha256:original.sha256,previousBriefDigest:store.digest(baseline.brief),currentBriefDigest:store.digest(project.brief),previousBenchmarkDigest:store.digest(baseline.benchmarks),currentBenchmarkDigest:store.digest(project.benchmarks),reason:'A new user decision changes the scope',affectedScope:['object decision'],changedAt:store.now()};
  await store.atomicJSON(path.join(root,'evidence/change.json'),change);project.baselineChanges=[await store.fileReference(root,'evidence/change.json')];await store.validateBaseline(root,project);
  project.benchmarks.revision='different';await assert.rejects(store.validateBaseline(root,project),e=>e.code==='BASELINE_CHANGE_MISSING');
});
test('explicit source-link-only and immutable-region contradictions reject embedded assets',()=>{
  const ref={path:'authority.md',sha256:'a'.repeat(64)};
  const asset={url:'/media/assets/a.svg',sourceRef:ref,rights:{status:'self-owned',display:true,redistribution:true,evidenceRef:ref},authorization:{operations:['display'],regions:['whole-asset'],immutableProperties:['logo']},operation:{type:'display',region:'whole-asset',affectedProperties:[],authorizationRef:ref}};
  assert.equal(validateAsset(asset),asset);
  assert.throws(()=>validateAsset({...asset,license:{redistribution:false,allowedUse:'source-link-only'}}),e=>e.code==='ASSET_LINK_ONLY');
  assert.throws(()=>validateAsset({...asset,operation:{...asset.operation,type:'subject-color-material'}}),e=>e.code==='ASSET_OPERATION_FORBIDDEN');
  assert.throws(()=>validateAsset({...asset,operation:{...asset.operation,affectedProperties:['logo']}}),e=>e.code==='ASSET_LOCK_VIOLATION');
  assert.throws(()=>validateAsset({...asset,rights:undefined}),e=>e.code==='ASSET_RIGHTS_MISSING');
  assert.throws(()=>validateAsset({...asset,authorization:{...asset.authorization,immutableProperties:[{name:'logo'}]}}),e=>e.code==='ASSET_AUTHORIZATION_INVALID');
  assert.throws(()=>validateAsset({...asset,operation:{...asset.operation,affectedProperties:[{name:'logo'}]}}),e=>e.code==='ASSET_OPERATION_INVALID');
});
test('subject compositions require unique authorized sources and the exact affected-region mask',()=>{
  const d=input().directions[0],ref={path:'assets/base.svg',sha256:'a'.repeat(64)},mask={path:'assets/mask.svg',sha256:'b'.repeat(64)},authority={path:'evidence/authority.md',sha256:'c'.repeat(64)};
  const common={presentation:'composition-only',rights:{status:'self-owned',display:true,redistribution:true,evidenceRef:authority},authorization:{operations:['display','subject-color-material'],regions:['material'],immutableProperties:['logo']}};
  d.assets=[{...structuredClone(common),id:'base',url:'/media/assets/base.svg',sourceRef:ref,operation:{type:'subject-color-material',region:'material',affectedProperties:['light'],authorizationRef:authority,parentRefs:[ref],maskRef:mask}},{...structuredClone(common),id:'mask',url:'/media/assets/mask.svg',sourceRef:mask,operation:{type:'display',region:'material',affectedProperties:[],authorizationRef:authority,maskRef:mask}}];
  d.studyComposition={baseAssetId:'base',maskAssetId:'mask',opacity:.5,blendMode:'multiply',aspectRatio:1.5,purpose:'Test localized illumination while preserving the label'};store.validateStudyComposition(d);
  for(const mutate of [x=>x.studyComposition.opacity=0,x=>x.studyComposition.aspectRatio=NaN,x=>x.studyComposition.extra='ignored',x=>x.assets.push(structuredClone(x.assets[0])),x=>x.assets[0].operation.maskRef=ref]){const bad=structuredClone(d);mutate(bad);assert.throws(()=>store.validateStudyComposition(bad));}
});
test('caption edits and damaged idempotent snapshots invalidate current state',async t=>{
  const root=await fixture(t);await store.createProject(root,input());let saved=await store.commitSnapshot(root,{directionId:'study',parameters:{},timeSeconds:2});
  const p=await store.loadProject(root);p.directions[0].caption='Changed visible explanation';await store.atomicJSON(path.join(root,'project.json'),p);
  assert.equal((await store.snapshotStates(root,await store.loadProject(root))).study.status,'stale');
  saved=await store.commitSnapshot(root,{directionId:'study',parameters:p.directions[0].parameters,timeSeconds:2});
  await fs.writeFile(path.join(root,`snapshots/${saved.snapshot.id}.json`),'{}');
  await assert.rejects(store.commitSnapshot(root,{directionId:'study',parameters:saved.snapshot.parameters,timeSeconds:2}),e=>e.code==='SNAPSHOT_MISMATCH');
});
test('project manifest follows the same real-path containment boundary as evidence',async t=>{
  const root=await fixture(t),inside=path.join(root,'project'),outside=path.join(root,'outside');await fs.mkdir(inside);await fs.mkdir(outside);await fs.writeFile(path.join(outside,'project.json'),JSON.stringify(input()));
  try{await fs.symlink(path.join(outside,'project.json'),path.join(inside,'project.json'),'file');}catch(e){if(['EPERM','EACCES','ENOTSUP'].includes(e.code)){t.skip('File symlink unavailable on this host');return;}throw e;}
  await assert.rejects(store.loadProject(inside),e=>e.code==='UNSAFE_PATH');
});
test('actual installed dependency version and code bytes are checked, including repeated calls',async t=>{
  const root=await fixture(t);await fs.writeFile(path.join(root,'package.json'),JSON.stringify({dependencies:{shaders:'4.0.2',esbuild:'0.28.2',playwright:'1.64.0'}}));
  for(const [name,version] of [['shaders','4.0.2'],['esbuild','0.28.2'],['playwright','1.64.0'],['playwright-core','1.64.0']]){const dir=path.join(root,'node_modules',name);await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,'package.json'),JSON.stringify({name,version}));await fs.writeFile(path.join(dir,'index.js'),'// original synthetic code');}
  const before=await dependencyIdentity(root);await fs.writeFile(path.join(root,'node_modules/shaders/index.js'),'// changed synthetic code');const after=await dependencyIdentity(root);assert.notEqual(before[0].contentDigest,after[0].contentDigest);
  await fs.writeFile(path.join(root,'node_modules/shaders/package.json'),JSON.stringify({name:'shaders',version:'999.0.0-SYNTHETIC-DRIFT'}));await assert.rejects(dependencyIdentity(root),e=>e.code==='DEPENDENCY_VERSION');
});
