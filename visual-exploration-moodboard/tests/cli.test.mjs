import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {packageRoot} from '../runtime/project-store.mjs';
const run=promisify(execFile);

test('clean standalone package offers help/intake and accurately reports missing runtime dependencies',async t=>{
  const base=await fs.mkdtemp(path.join(os.tmpdir(),'vem-cli-'));t.after(()=>fs.rm(base,{recursive:true,force:true}));
  const isolated=path.join(base,'isolated');await fs.cp(packageRoot,isolated,{recursive:true,filter:filename=>!filename.split(path.sep).some(part=>['node_modules','.cache','.git','dist','output'].includes(part))});
  const cli=path.join(isolated,'scripts/moodboard.mjs');
  const help=await run(process.execPath,[cli,'--help'],{windowsHide:true});assert.match(help.stdout,/start --project/);assert.match(help.stdout,/video unsupported/);
  const probe=await run(process.execPath,[cli,'probe'],{windowsHide:true}).then(()=>assert.fail('Missing runtime passed'),error=>error);assert.equal(probe.code,2);assert.match(probe.stdout,/not_tested/);
  const brief=path.join(base,'brief 中文.md');await fs.writeFile(brief,'# 原始需求\n这是独立入口测试，不是正式艺术创作。');
  const project=path.join(base,'工程 空格');
  const intake=await run(process.execPath,[cli,'start','--project',project,'--brief',brief],{windowsHide:true}).then(()=>assert.fail('Preparation passed as execution'),error=>error);
  assert.equal(intake.code,2);assert.equal(JSON.parse(intake.stdout).status,'prepared');assert.match(await fs.readFile(path.join(project,'brief-source.md'),'utf8'),/原始需求/);
  const duplicate=await run(process.execPath,[cli,'start','--project',project,'--brief',brief],{windowsHide:true}).then(()=>assert.fail('Overwrote existing intake'),error=>error);assert.match(duplicate.stderr,/INTAKE_EXISTS/);
  const unsupported=await run(process.execPath,[cli,'export','--project',project,'--format','mp4'],{windowsHide:true}).then(()=>assert.fail('Unsupported video passed'),error=>error);assert.match(unsupported.stderr,/UNSUPPORTED_EXPORT/);
});
