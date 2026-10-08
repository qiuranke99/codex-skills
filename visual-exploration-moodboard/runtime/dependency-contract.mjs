import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const cache=new Map();
function failure(code,message){const error=new Error(message);error.code=code;error.exitCode=2;return error;}
export async function dependencyIdentity(packageDirectory=root){
  const config=JSON.parse(await fs.readFile(path.join(packageDirectory,'package.json'),'utf8'));
  const identities=[];
  for(const name of ['shaders','esbuild','playwright','playwright-core']){
    const version=name==='playwright-core'?config.dependencies.playwright:config.dependencies[name];
    const directory=path.join(packageDirectory,'node_modules',name);let metadata;
    try{metadata=JSON.parse(await fs.readFile(path.join(directory,'package.json'),'utf8'));}catch{throw failure('DEPENDENCY_MISSING',`${name}: run npm ci in this Skill package`);}
    if(metadata.name!==name||metadata.version!==version)throw failure('DEPENDENCY_VERSION',`${name}: installed ${metadata.version}; required ${version}`);
    // Bind actual installed code, not only lockfile/version claims. No provider
    // attestation is inferred from this local content identity.
    const files=[];async function visit(folder){for(const entry of (await fs.readdir(folder,{withFileTypes:true})).sort((a,b)=>a.name.localeCompare(b.name))){const filename=path.join(folder,entry.name);if(entry.isSymbolicLink())throw failure('DEPENDENCY_REDIRECTED',`${name}: unexpected dependency symlink`);if(entry.isDirectory()&&entry.name!=='node_modules')await visit(filename);else if(entry.isFile()&&/\.(?:m?js|json|wgsl|wasm)$/.test(entry.name)){const stat=await fs.stat(filename),key=`${stat.size}:${stat.mtimeMs}:${stat.ctimeMs}:${stat.ino}`;let item=cache.get(filename);if(!item||item.key!==key){item={key,sha:createHash('sha256').update(await fs.readFile(filename)).digest('hex')};cache.set(filename,item);}files.push([path.relative(directory,filename).replaceAll('\\','/'),item.sha]);}}}
    await visit(directory);if(!files.length)throw failure('DEPENDENCY_EMPTY',`${name}: no installed code`);
    identities.push({name,version:metadata.version,contentDigest:createHash('sha256').update(JSON.stringify(files)).digest('hex')});
  }
  return identities;
}
