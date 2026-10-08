import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import * as store from '../runtime/project-store.mjs';
import {recipeCatalog,validateParameters} from '../runtime/shader-adapter.mjs';

// These fixtures are synthetic. Their receipts exercise data binding only and
// are never evidence of a real GPU render, independent judgment or human acceptance.
function input() {
  return {
    schemaVersion:1,
    project:{id:'synthetic-store',title:'合成契约测试',medium:'brand-study'},
    brief:{decision:'比较秩序与包裹的关系',objectSuccess:['关系可辨'],carrierSuccess:['可比较和接续'],locks:['主体身份'],openVariables:['高光宽度']},
    benchmarks:{revision:'baseline-1',object:[{id:'object-synthetic',reason:'合成测试基线',observed:false}],carrier:[{id:'carrier-synthetic',reason:'合成测试基线',observed:false}]},
    directions:recipeCatalog.slice(0,2).map((recipe,index)=>({
      id:`direction-${index+1}`,title:recipe.title,recipeId:recipe.id,parameters:validateParameters(recipe.id,{}),
      hypothesis:{question:'如何建立关系',mechanism:recipe.mechanism,expected:'可以看到明确关系',failure:'关系消失'},
      handoff:{adopt:['关系'],exclude:['未知身份'],unproven:['最终生产可行性']},
      quality:{object:{status:'unverified',evidence:[],issues:[]},carrier:{status:'unverified',evidence:[],issues:[]}},
    })),
  };
}

async function fixture(t,{create=true}={}) {
  const parent=await fs.mkdtemp(path.join(os.tmpdir(),'vem-project-store-'));
  const root=path.join(parent,'中文 工程'),outside=path.join(parent,'outside');
  await fs.mkdir(root);await fs.mkdir(outside);
  t.after(async()=>{
    const actual=path.resolve(parent),temp=path.resolve(os.tmpdir());
    assert.ok(store.inside(temp,actual) && path.basename(actual).startsWith('vem-project-store-'));
    await fs.rm(actual,{recursive:true,force:true});
  });
  if(create) await store.createProject(root,input());
  return {root,outside,parent};
}

async function commitAll(root) {
  const project=await store.loadProject(root);
  for(const direction of project.directions) await store.commitSnapshot(root,{directionId:direction.id,parameters:direction.parameters,timeSeconds:4.25});
  return store.loadProject(root);
}
async function editProject(root,mutate) {
  const project=await store.loadProject(root);mutate(project);
  await store.atomicJSON(path.join(root,'project.json'),project);
  return project;
}
const has=(report,code)=>report.findings.some(finding=>finding.code===code && finding.status!=='PASS');

test('project creation freezes baseline, strips supplied success claims and refuses overwrite',async t=>{
  const {root}=await fixture(t,{create:false});
  const supplied=input();supplied.directions[0].snapshot={digest:'fake'};supplied.directions[0].poster='fake.png';supplied.directions[0].render={path:'fake.json'};
  const created=await store.createProject(root,supplied);
  assert.equal(created.revision,1);assert.equal(created.directions[0].status,'draft');assert.equal(created.directions[0].snapshot,undefined);assert.equal(created.directions[0].poster,undefined);assert.equal(created.directions[0].render,undefined);
  const baseline=await store.readJSON(path.join(root,'evidence','baseline-1.json'));
  const {baselineRef,...initialProject}=created;
  assert.equal(baseline.initialProjectDigest,store.digest(initialProject));assert.deepEqual(baseline.brief,created.brief);assert.equal((await store.verifyReference(root,baselineRef)).kind,'project-baseline');
  await assert.rejects(store.createProject(root,input()),error=>error.code==='PROJECT_EXISTS');
  assert.equal((await store.loadProject(root)).revision,1);
});

test('snapshots are content-bound, idempotent and invalidate only the changed direction',async t=>{
  const {root}=await fixture(t);let project=await commitAll(root);
  const first=project.directions[0].snapshot,other=project.directions[1].snapshot;
  const revision=project.revision;
  const same=await store.commitSnapshot(root,{directionId:'direction-1',parameters:project.directions[0].parameters,timeSeconds:4.25});
  assert.equal(same.snapshot.digest,first.digest);assert.equal(same.project.revision,revision);
  await editProject(root,p=>{p.directions[0].poster='/media/old.png';p.directions[0].render={path:'old.json',sha256:'0'.repeat(64)};p.directions[1].quality.object.status='supported';});
  const changed=await store.commitSnapshot(root,{directionId:'direction-1',parameters:{...project.directions[0].parameters,aperture:0.3},timeSeconds:6});
  assert.notEqual(changed.snapshot.digest,first.digest);assert.equal(changed.snapshot.revision,first.revision+1);assert.equal(changed.project.directions[0].poster,null);assert.equal(changed.project.directions[0].render,undefined);assert.equal(changed.project.directions[0].quality.object.status,'unverified');
  assert.deepEqual(changed.project.directions[1].snapshot,other);assert.equal(changed.project.directions[1].quality.object.status,'supported');
  assert.deepEqual(await store.readJSON(path.join(root,'snapshots',`${first.id}.json`)),first);
});

test('snapshot requests reject unknown direction, parameter poison, and invalid time without writing',async t=>{
  const {root}=await fixture(t);const before=store.digest(await store.loadProject(root));
  for(const request of [
    {directionId:'missing',parameters:{},timeSeconds:1},
    {directionId:'direction-1',parameters:{tempo:NaN},timeSeconds:1},
    {directionId:'direction-1',parameters:{typo:1},timeSeconds:1},
    {directionId:'direction-1',parameters:{},timeSeconds:Infinity},
    {directionId:'direction-1',parameters:{},timeSeconds:-1},
    {directionId:'direction-1',parameters:{},timeSeconds:'1'},
  ]) await assert.rejects(store.commitSnapshot(root,request));
  assert.equal(store.digest(await store.loadProject(root)),before);
});

test('changed hypothesis, handoff and brief invalidate previous snapshot evidence',async t=>{
  for(const mutate of [p=>p.directions[0].hypothesis.expected='新的观看目标',p=>p.directions[0].handoff.adopt.push('新关系'),p=>p.brief.objectSuccess.push('新的对象目标')]) {
    const {root}=await fixture(t);await commitAll(root);await editProject(root,mutate);
    const report=await store.checkProject(root);assert.ok(has(report,'STALE_CREATIVE_CONTRACT'),JSON.stringify(report));
  }
});

test('benchmark content changes invalidate evidence even if an editor forgot to bump revision',async t=>{
  const {root}=await fixture(t);await commitAll(root);
  await editProject(root,p=>{p.benchmarks.object[0].reason='实际比较基线已经变化';});
  const report=await store.checkProject(root);assert.ok(has(report,'STALE_CREATIVE_CONTRACT'),JSON.stringify(report));
});

test('current manifest parameters cannot disagree with the saved snapshot',async t=>{
  const {root}=await fixture(t);await commitAll(root);
  await editProject(root,p=>{p.directions[0].parameters.aperture=0.31;});
  const report=await store.checkProject(root);assert.ok(has(report,'SNAPSHOT_BINDING_MISMATCH'),JSON.stringify(report));
});

test('a valid snapshot from another direction cannot be rebound by copying manifest fields',async t=>{
  const {root}=await fixture(t);await commitAll(root);
  await editProject(root,p=>{
    const [first,second]=p.directions;second.recipeId=first.recipeId;second.parameters=structuredClone(first.parameters);second.hypothesis=structuredClone(first.hypothesis);second.handoff=structuredClone(first.handoff);second.snapshot=structuredClone(first.snapshot);
  });
  const report=await store.checkProject(root);assert.ok(has(report,'SNAPSHOT_BINDING_MISMATCH'),JSON.stringify(report));
});

test('changed saved snapshot file and missing snapshot fail instead of silently restoring approval',async t=>{
  const {root}=await fixture(t);const project=await commitAll(root);const snapshot=project.directions[0].snapshot;
  await store.atomicJSON(path.join(root,'snapshots',`${snapshot.id}.json`),{...snapshot,timeSeconds:4.5});
  const mismatch=await store.checkProject(root);assert.ok(has(mismatch,'SNAPSHOT_MISMATCH'));
  await fs.rm(path.join(root,'snapshots',`${snapshot.id}.json`));
  const missing=await store.checkProject(root);assert.ok(has(missing,'MISSING_FILE'));
});

test('project-relative resolution rejects traversal, absolute paths, NUL and escaped symlink parents',async t=>{
  const {root,outside}=await fixture(t);
  for(const filename of ['../outside/secret.json','..\\outside\\secret.json',path.join(outside,'secret.json'),'C:\\outside\\secret.json','C:outside/secret.json','\\\\server\\share\\secret.json','bad\0name']) await assert.rejects(store.projectFile(root,filename),error=>error.code==='UNSAFE_PATH');
  await fs.writeFile(path.join(outside,'secret.json'),'{}');
  await fs.symlink(outside,path.join(root,'escape'),process.platform==='win32'?'junction':'dir');
  await assert.rejects(store.projectFile(root,'escape/secret.json',{mustExist:true}),error=>error.code==='UNSAFE_PATH');
  await assert.rejects(store.projectFile(root,'escape/not-yet-created.json'),error=>error.code==='UNSAFE_PATH');
  const safe=await store.projectFile(root,'新文件夹/子项.json');assert.ok(store.inside(await fs.realpath(root),safe));
});

test('baseline creation cannot follow an existing evidence junction outside the project',async t=>{
  const {root,outside}=await fixture(t,{create:false});
  await fs.symlink(outside,path.join(root,'evidence'),process.platform==='win32'?'junction':'dir');
  await assert.rejects(store.createProject(root,input()),error=>error.code==='UNSAFE_PATH');
  await assert.rejects(fs.access(path.join(outside,'baseline-1.json')));
});

test('file evidence supports binary/Markdown/JSONL while JSON references still parse JSON',async t=>{
  const {root}=await fixture(t);
  assert.equal(typeof store.verifyFileReference,'function','The byte/hash verifier must be separate from JSON parsing');
  const files=[['evidence/sample.png',Buffer.from([137,80,78,71,13,10,26,10,1,2,3,4])],['evidence/review.md',Buffer.from('# 合成首评\n')],['evidence/trace.jsonl',Buffer.from('{"type":"turn"}\n{"type":"tool"}\n')]];
  for(const [filename,bytes] of files) {
    await fs.writeFile(path.join(root,filename),bytes);const ref=await store.fileReference(root,filename);
    const verified=await store.verifyFileReference(root,ref);assert.equal(verified.absolute,await fs.realpath(path.join(root,filename)));
    assert.equal(verified.sha256,store.digest(bytes));assert.deepEqual(verified.bytes,bytes);
    await assert.rejects(store.verifyReference(root,ref),error=>error.code==='INVALID_JSON');
    await fs.appendFile(path.join(root,filename),'x');await assert.rejects(store.verifyFileReference(root,ref),error=>error.code==='STALE_EVIDENCE');
  }
  await store.atomicJSON(path.join(root,'evidence','record.json'),{synthetic:true});const json=await store.fileReference(root,'evidence/record.json');assert.deepEqual(await store.verifyReference(root,json),{synthetic:true});
});

test('empty, missing and unbound evidence are rejected; metadata cannot override identity',async t=>{
  const {root}=await fixture(t);assert.equal(typeof store.verifyFileReference,'function');
  await fs.writeFile(path.join(root,'evidence','empty.bin'),Buffer.alloc(0));
  const empty=await store.fileReference(root,'evidence/empty.bin');
  await assert.rejects(store.verifyFileReference(root,empty),error=>error.code==='EMPTY_EVIDENCE' || error.code==='EMPTY_FILE');
  await assert.rejects(store.verifyFileReference(root,{path:'evidence/missing.bin',sha256:'0'.repeat(64)}),error=>error.code==='MISSING_FILE');
  await assert.rejects(store.verifyFileReference(root,{path:'evidence/empty.bin'}),error=>error.code==='EVIDENCE_REFERENCE_INVALID');
  await fs.writeFile(path.join(root,'evidence','real.bin'),'real');
  const ref=await store.fileReference(root,'evidence/real.bin',{path:'../outside/fake.bin',sha256:'0'.repeat(64),note:'synthetic metadata'});
  assert.equal(ref.path,'evidence/real.bin');assert.equal(ref.sha256,store.digest('real'));assert.equal(ref.note,'synthetic metadata');
});

test('delivery never passes without actual host, review, benchmark and export evidence',async t=>{
  const {root}=await fixture(t);await commitAll(root);
  const report=await store.checkProject(root,{scope:'delivery'});
  assert.notEqual(report.status,'PASS');
  for(const code of ['HOST_EXECUTION_MISSING','REVIEW_MISSING','BENCHMARK_UNOBSERVED','EXPORT_MISSING']) assert.ok(has(report,code),`${code}: ${JSON.stringify(report)}`);
  assert.equal(report.boundaries.aestheticCertification,false);assert.equal(report.boundaries.userAcceptance,'not_inferred');
});

test('project write lock rejects concurrent mutation and releases after a failed operation',async t=>{
  const {root}=await fixture(t);let release,entered;
  const started=new Promise(resolve=>entered=resolve),hold=new Promise(resolve=>release=resolve);
  const first=store.withProjectLock(root,async()=>{entered();await hold;throw new Error('synthetic operation failure');});
  await started;await assert.rejects(store.commitSnapshot(root,{directionId:'direction-1',parameters:{},timeSeconds:1}),error=>error.code==='PROJECT_BUSY');
  release();await assert.rejects(first,/synthetic operation failure/);
  const committed=await store.commitSnapshot(root,{directionId:'direction-1',parameters:{},timeSeconds:1});assert.ok(committed.snapshot.digest);
});
