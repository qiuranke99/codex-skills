import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { build } from 'esbuild';
import { packageRoot, loadProject, commitSnapshot, projectFile, atomicJSON, now, ContractError, assert, recipeFor, snapshotStates, engineDigest } from './project-store.mjs';
import {validateAsset} from './asset-contract.mjs';

const mime = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml','.pdf':'application/pdf','.woff2':'font/woff2'};
export async function startServer(projectRoot, {port=0}={}) {
  await loadProject(projectRoot);
  const servingEngine=await engineDigest();
  assert(Number.isInteger(port) && port >= 0 && port <= 65535, 'INVALID_PORT', 'Port must be 0..65535');
  const compiled = await build({entryPoints:[path.join(packageRoot,'runtime/board.mjs')],bundle:true,format:'esm',platform:'browser',write:false,target:'es2022',logLevel:'silent'});
  const bundle = compiled.outputFiles[0].contents; let baseURL; let exporting=false;
  const send = (res, status, body, type='application/json; charset=utf-8', headers={}) => {res.writeHead(status, {'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...headers});res.end(type.startsWith('application/json')?JSON.stringify(body):body);};
  const server = http.createServer(async(req,res)=>{
    try {
      if (req.headers.host !== new URL(baseURL).host) throw new ContractError('INVALID_HOST','Use the advertised loopback URL');
      const url=new URL(req.url,baseURL);
      if(url.pathname.startsWith('/api/')&&await engineDigest()!==servingEngine)throw new ContractError('SERVER_BUILD_STALE','Runtime/dependency source changed; restart this local service before continuing',2);
      if(req.method==='GET' && url.pathname==='/api/project') {const p=await loadProject(projectRoot);return send(res,200,{...p,_snapshotStates:await snapshotStates(projectRoot,p)});}
      if(req.method==='GET' && url.pathname.startsWith('/api/recipe/')) return send(res,200,await recipeFor(decodeURIComponent(url.pathname.slice(12))));
      if(req.method==='GET' && url.pathname==='/api/export') {
        return send(res,405,{error:'METHOD_NOT_ALLOWED',message:'Create exports with a same-origin POST; GET does not mutate projects'});
      }
      if(req.method==='POST') {
        assert(req.headers.origin===baseURL,'ORIGIN_REJECTED','Mutations require the local board origin');
        assert((req.headers['content-type']||'').startsWith('application/json'),'CONTENT_TYPE','Expected application/json');
        const chunks=[];let size=0;for await(const chunk of req){size+=chunk.length;assert(size<=1024*1024,'BODY_TOO_LARGE','Request exceeds 1 MiB');chunks.push(chunk);}
        let body;try{body=JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw new ContractError('INVALID_JSON','Invalid request JSON');}
        if(url.pathname==='/api/snapshot') {const saved=await commitSnapshot(projectRoot,body);saved.project._snapshotStates=await snapshotStates(projectRoot,saved.project);return send(res,200,saved);}
        if(url.pathname==='/api/export') {
          const format=body.format;assert(['png','pdf'].includes(format),'UNSUPPORTED_EXPORT','Only PNG and PDF are supported in v1');assert(!exporting,'EXPORT_BUSY','An export is already running');exporting=true;
          try{const {exportProject}=await import('./browser-tools.mjs');const receipt=await exportProject(projectRoot,{format,url:baseURL});const filename=await projectFile(projectRoot,receipt.output.path,{mustExist:true});return send(res,200,await fs.readFile(filename),mime[`.${format}`],{'Content-Disposition':`attachment; filename="moodboard.${format}"`});}finally{exporting=false;}
        }
        if(url.pathname==='/api/observation') {
          const filename=`evidence/runtime-${Date.now()}-${Math.random().toString(16).slice(2)}.json`;
          await atomicJSON(await projectFile(projectRoot,filename),{schemaVersion:1,receivedAt:now(),scope:'Observation only; not quality acceptance',observation:body}); return send(res,201,{recorded:true,path:filename});
        }
        return send(res,404,{error:'NOT_FOUND'});
      }
      if(req.method!=='GET'&&req.method!=='HEAD') return send(res,405,{error:'METHOD_NOT_ALLOWED'});
      let filename;
      if(url.pathname==='/'||url.pathname==='/index.html') filename=path.join(packageRoot,'runtime/board.html');
      else if(url.pathname==='/bundle/board.js') return send(res,200,bundle,mime['.js']);
      else if(url.pathname==='/runtime/board.css') filename=path.join(packageRoot,'runtime/board.css');
      else if(url.pathname.startsWith('/media/')) {
        let relative;try{relative=decodeURIComponent(url.pathname.slice(7));}catch{throw new ContractError('UNSAFE_PATH','Bad path encoding');}
        assert(/^(assets|posters|compositions|exports)\//.test(relative),'MEDIA_NOT_PUBLIC','Only assets, Shader posters, subject compositions and exports are served');
        filename=await projectFile(projectRoot,relative,{mustExist:true});
        const project=await loadProject(projectRoot);for(const asset of project.directions.flatMap(d=>d.assets||[])){if(asset.sourceRef?.path===relative){validateAsset(asset);assert(asset.url&&asset.rights.display&&asset.rights.redistribution,'ASSET_LINK_ONLY','This source is permitted only as a link');}}
        assert(mime[path.extname(filename).toLowerCase()],'MEDIA_TYPE','Unsupported media type');
      } else return send(res,404,{error:'NOT_FOUND'});
      const bytes=await fs.readFile(filename);return send(res,200,req.method==='HEAD'?Buffer.alloc(0):bytes,mime[path.extname(filename).toLowerCase()]||'application/octet-stream');
    } catch(error){send(res,error.code==='ORIGIN_REJECTED'||error.code==='INVALID_HOST'?403:error.code==='MISSING_FILE'?404:400,{error:error.code||'REQUEST_FAILED',message:error.message});}
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',()=>{server.off('error',reject);resolve();});});
  baseURL=`http://127.0.0.1:${server.address().port}`;
  return {url:baseURL,server,close:()=>new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()))};
}
