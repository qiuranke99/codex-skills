#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {createProject,loadProject,commitSnapshot,checkProject,atomicJSON,now,ContractError,assert,packageRoot,withProjectLock,digest} from '../runtime/project-store.mjs';

const help=`Visual Exploration Moodboard v1 — local HTML + required Shaders
Usage: node scripts/moodboard.mjs <command> [options]
  probe                         Check pinned dependencies and Chromium; GPU requires a real render
  start --project DIR --brief FILE [--host native|codex-app-server] [--codex EXE] [--trace JSONL] [--timeout-ms 900000]
                                Freeze intake and execute/prove the actual Skill host; prepared is not executed
  init --project DIR --brief JSON
                                Create an agent-authored project contract; never overwrite
  resume --project DIR [--host native|codex-app-server] [--codex EXE] [--trace JSONL]
                                Inspect current dependencies and continue through the actual host
  serve --project DIR [--port 0] Local loopback HTML; Ctrl+C closes the service
  commit --project DIR --direction ID --time SECONDS [--parameters JSON_FILE]
                                Commit validated current parameters and analytic time; not approval
  render --project DIR          Actual GPU posters and version-bound receipts
  export --project DIR --format png|pdf
                                Render all current snapshots and export the complete overview
  check --project DIR --scope technical|delivery
                                Check real version-bound evidence; never certify aesthetic truth
Exit: 0 within declared scope; 1 failure; 2 incomplete/unsupported. PNG/PDF supported; video unsupported.
Set VEM_CHROMIUM_PATH to an installed Chromium executable when automatic discovery cannot find one.
Initial dependency setup: npm ci (in this Skill package). No account/cloud is required for the board.
`;
function argumentsOf(args){const options={};for(let i=0;i<args.length;i++){assert(args[i].startsWith('--'),'ARGUMENT_INVALID',`Unknown argument: ${args[i]}`);const key=args[i].slice(2);assert(!Object.hasOwn(options,key),'ARGUMENT_DUPLICATE',`Duplicate --${key}`);if(key==='help'){options.help=true;continue;}assert(args[i+1]&&!args[i+1].startsWith('--'),'ARGUMENT_MISSING',`Value required for --${key}`);options[key]=args[++i];}return options;}
function requireProject(options){assert(options.project,'PROJECT_ARGUMENT','--project is required');return path.resolve(options.project);}
async function main(){
  assert(Number(process.versions.node.split('.')[0])>=22,'NODE_VERSION','Node.js >=22 is required');
  const [command,...args]=process.argv.slice(2);const options=argumentsOf(args);
  if(!command||command==='--help'||command==='help'||options.help){process.stdout.write(help);return;}
  const accepted={probe:[],start:['project','brief','host','codex','trace','timeout-ms'],init:['project','brief'],resume:['project','host','codex','trace','timeout-ms'],serve:['project','port'],commit:['project','direction','time','parameters'],render:['project'],export:['project','format'],check:['project','scope']};
  assert(accepted[command],'COMMAND_UNSUPPORTED',`Unsupported command: ${command}`);for(const key of Object.keys(options))assert(accepted[command].includes(key),'OPTION_UNSUPPORTED',`${command}: --${key} is unsupported`);
  const report=value=>process.stdout.write(`${JSON.stringify(value,null,2)}\n`);
  if(command==='probe') {let browser;try{const {findChromium}=await runtime('../runtime/browser-tools.mjs');browser=await findChromium();}catch(e){browser={status:'unavailable',reason:e.message};}let shaders;try{shaders=JSON.parse(await fs.readFile(path.join(packageRoot,'node_modules/shaders/package.json'),'utf8')).version;}catch{shaders='missing; run npm ci in the Skill package';}report({node:process.version,packageRoot,shaders,chromium:browser,gpu:'not_tested_by_dependency_probe'});if(typeof browser!=='string'||shaders!=='4.0.2')process.exitCode=2;return;}
  const root=requireProject(options);
  if(command==='init'){assert(options.brief,'BRIEF_ARGUMENT','--brief project JSON required');report(await createProject(root,JSON.parse((await fs.readFile(path.resolve(options.brief),'utf8')).replace(/^\uFEFF/,''))));return;}
  if(command==='start'||command==='resume'){
    if(command==='start') {
      assert(options.brief,'BRIEF_ARGUMENT','--brief required');await fs.mkdir(root,{recursive:true});
      try{await fs.access(path.join(root,'intake.json'));throw new ContractError('INTAKE_EXISTS','Existing intake is never overwritten; use resume');}catch(e){if(e instanceof ContractError||e.code!=='ENOENT')throw e;}
      const original=path.resolve(options.brief);const bytes=await fs.readFile(original);assert(bytes.length>0,'BRIEF_EMPTY','Empty brief');
      await fs.writeFile(path.join(root,'brief-source'+path.extname(original)),bytes,{flag:'wx'});
      await atomicJSON(path.join(root,'intake.json'),{schemaVersion:1,createdAt:now(),originalBrief:original,briefCopy:'brief-source'+path.extname(original),briefDigest:digest(bytes),status:'prepared',scope:'Original intake; actual agent understanding/execution still required'});
      let data;try{data=JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));}catch{}if(data?.schemaVersion===1&&data.project&&data.directions)await createProject(root,data);
    } else {await loadProject(root);report(await checkProject(root,{scope:'technical'}));}
    const {executeHost}=await import('../runtime/host-adapter.mjs');
    const task=`Use the explicitly supplied visual-exploration-moodboard Skill to read the original brief/intake in ${root}. Act as visual creative director and art director; make actual object-specific visual judgments and an editable local HTML board, PNG overview, required meaningful Shaders per completed direction, honest evidence and adopt/exclude/unproven handoff. Read relevant reference contracts first. If no project exists, author a complete project JSON and run init; otherwise resume the same project and preserve locks. Choose and actually inspect relevant benchmarks before direction production. Use this package's CLI for commit, render, export, and check. Never call start recursively. Model must be gpt-6.1-sol with ultra. Do not claim independent review or user acceptance. Work only within this project and Skill scope; do not publish business work or submit paid generation without existing authorization.`;
    const timeoutMs=options['timeout-ms']===undefined?900000:Number(options['timeout-ms']);assert(Number.isInteger(timeoutMs)&&timeoutMs>=1000&&timeoutMs<=3600000,'INVALID_TIMEOUT','--timeout-ms must be 1000..3600000');
    const host=await executeHost({projectRoot:root,host:options.host||'native',codexPath:options.codex,tracePath:options.trace,task,timeoutMs});
    try {await fs.access(path.join(root,'project.json'));await withProjectLock(root,async()=>{const project=await loadProject(root);project.host={status:host.status,evidence:host.evidence};await atomicJSON(path.join(root,'project.json'),project);});}catch(error){if(error.code!=='ENOENT')throw error;}
    report(host);if(host.status!=='executed')process.exitCode=2;return;
  }
  if(command==='serve'){const {startServer}=await runtime('../runtime/server.mjs');const service=await startServer(root,{port:options.port===undefined?0:Number(options.port)});report({status:'serving',url:service.url,close:'Ctrl+C',scope:'Local editable board; does not imply delivery readiness'});for(const signal of ['SIGINT','SIGTERM'])process.once(signal,async()=>{await service.close();process.exit(0);});return;}
  if(command==='commit'){assert(options.direction&&options.time!==undefined,'COMMIT_ARGUMENTS','--direction and --time required');const p=await loadProject(root);const direction=p.directions.find(d=>d.id===options.direction);assert(direction,'UNKNOWN_DIRECTION',options.direction);const parameters=options.parameters?JSON.parse(await fs.readFile(path.resolve(options.parameters),'utf8')):direction.parameters;report(await commitSnapshot(root,{directionId:direction.id,parameters,timeSeconds:Number(options.time)}));return;}
  if(command==='render'){const {renderProject}=await runtime('../runtime/browser-tools.mjs');report(await renderProject(root));return;}
  if(command==='export'){assert(['png','pdf'].includes(options.format),'UNSUPPORTED_EXPORT','Only --format png|pdf is supported in v1');const {exportProject}=await runtime('../runtime/browser-tools.mjs');report(await exportProject(root,{format:options.format}));return;}
  if(command==='check'){assert(['technical','delivery'].includes(options.scope),'CHECK_SCOPE','--scope technical|delivery required');const result=await checkProject(root,{scope:options.scope});report(result);process.exitCode=result.status==='PASS'?0:result.status==='FAIL'?1:2;return;}
}
async function runtime(modulePath){try{return await import(modulePath);}catch(error){if(error.code==='ERR_MODULE_NOT_FOUND')throw new ContractError('DEPENDENCY_MISSING','Pinned runtime dependencies are missing; run npm ci in this Skill package',2);throw error;}}
main().catch(error=>{process.stderr.write(`${JSON.stringify({status:'failed',code:error.code||'UNEXPECTED_FAILURE',message:error.message})}\n`);process.exitCode=error.exitCode||1;});
