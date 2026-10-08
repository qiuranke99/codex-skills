import {recipeCatalog,ADAPTER_VERSION,SHADERS_VERSION} from '../assets/recipes/catalog.mjs';
export {recipeCatalog,ADAPTER_VERSION,SHADERS_VERSION};

export class ShaderStudyError extends Error {
  constructor(code,message) { super(message); this.name='ShaderStudyError'; this.code=code; }
}
const fail = (code,message) => { throw new ShaderStudyError(code,message); };
const record = value => !!value && typeof value==='object' && !Array.isArray(value) && (Object.getPrototypeOf(value)===Object.prototype || Object.getPrototypeOf(value)===null);
const own = (object,key) => Object.prototype.hasOwnProperty.call(object,key);
const clone = value => JSON.parse(JSON.stringify(value));
const exactKeys = (value,allowed,path) => {
  if (!record(value)) fail('INVALID_OBJECT',`${path} must be a plain object`);
  for (const key of Object.keys(value)) if(!allowed.includes(key)) fail('UNKNOWN_FIELD',`${path}.${key} is not supported`);
};

export function getRecipe(recipeId) {
  const recipe = recipeCatalog.find(value=>value.id===recipeId);
  if(!recipe) fail('UNKNOWN_RECIPE',`Unsupported recipe: ${String(recipeId)}`);
  return recipe;
}

/** Resolve every default, reject poison values before touching GPU or persisted state. */
export function validateParameters(recipeId,parameters={}) {
  const recipe = getRecipe(recipeId);
  exactKeys(parameters,Object.keys(recipe.parameters),'parameters');
  const resolved = {};
  for(const [key,contract] of Object.entries(recipe.parameters)) {
    const value = own(parameters,key) ? parameters[key] : contract.default;
    if(typeof value!=='number' || !Number.isFinite(value)) fail('INVALID_PARAMETER',`${recipe.id}.${key} must be a finite number`);
    if(value<contract.min || value>contract.max) fail('PARAMETER_RANGE',`${recipe.id}.${key} must be in [${contract.min}, ${contract.max}]`);
    if(contract.step===1 && !Number.isInteger(value)) fail('INVALID_PARAMETER',`${recipe.id}.${key} must be an integer`);
    resolved[key]=value;
  }
  return resolved;
}

/** The supported tree is deliberately narrow: original opaque generators, no media or hidden drivers. */
export function validateComponentTree(tree,recipeId) {
  const recipe=getRecipe(recipeId);
  exactKeys(tree,['structureVersion','components'],'componentTree');
  if(tree.structureVersion!==1) fail('STRUCTURE_VERSION','componentTree.structureVersion must be 1');
  if(!Array.isArray(tree.components) || tree.components.length!==1) fail('COMPONENT_COUNT','The stateless study contract requires one root generator');
  const ids=new Set();
  const inspect=(node,path)=>{
    exactKeys(node,['type','id','props','children'],path);
    if(typeof node.id!=='string' || !node.id || node.id==='preset-root' || ids.has(node.id)) fail('INVALID_COMPONENT_ID',`${path}.id is empty, reserved or duplicated`);
    ids.add(node.id);
    if(node.type!==recipe.componentType) fail('UNKNOWN_COMPONENT',`${path}.type is not supported for ${recipe.id}`);
    exactKeys(node.props,[...Object.keys(recipe.parameters),'opacity','visible','blendMode'],`${path}.props`);
    for(const key of Object.keys(recipe.parameters)) if(!own(node.props,key)) fail('UNRESOLVED_DEFAULT',`${path}.props.${key} must be explicit`);
    validateParameters(recipe.id,Object.fromEntries(Object.keys(recipe.parameters).map(key=>[key,node.props[key]])));
    if(node.props.opacity!==1 || node.props.visible!==true || node.props.blendMode!=='normal') fail('UNSUPPORTED_COMPOSITING','Opaque, visible, normal composition must be explicit');
    if(!Array.isArray(node.children)) fail('INVALID_CHILDREN',`${path}.children must be explicit`);
    for(let i=0;i<node.children.length;i++) inspect(node.children[i],`${path}.children[${i}]`);
    if(node.children.length) fail('UNSUPPORTED_CHILDREN','Original study generators do not accept children');
  };
  inspect(tree.components[0],'componentTree.components[0]');
  return clone(tree);
}

export function validateRecipe(recipe) {
  if(!record(recipe)) fail('INVALID_RECIPE','recipe must be an object from the catalog');
  const canonical=getRecipe(recipe.recipeId ?? recipe.id);
  if(recipe.id!==canonical.id || recipe.recipeId!==canonical.id || recipe.revision!==canonical.revision) fail('RECIPE_VERSION','Recipe identity/revision does not match the supported catalog');
  if(recipe.adapterVersion!==ADAPTER_VERSION || recipe.upstream?.package!=='shaders' || recipe.upstream?.version!==SHADERS_VERSION) fail('UPSTREAM_VERSION','Recipe requires another adapter or Shaders version');
  if(!Array.isArray(recipe.resources) || recipe.resources.length!==0) fail('UNSUPPORTED_RESOURCE','These original studies accept no image, video, font or network resources');
  if(JSON.stringify(recipe.parameters)!==JSON.stringify(canonical.parameters)) fail('PARAMETER_CONTRACT','Recipe parameter contract differs from this adapter');
  const tree=validateComponentTree(recipe.componentTree,canonical.id);
  if(JSON.stringify(tree)!==JSON.stringify(canonical.componentTree)) fail('RECIPE_TREE_MISMATCH','Catalog component tree was modified; use supported parameters instead');
  return canonical;
}

export function makePreset(recipeId,parameters={}) {
  const recipe=getRecipe(recipeId);
  const tree=clone(recipe.componentTree);
  Object.assign(tree.components[0].props,validateParameters(recipeId,parameters));
  return validateComponentTree(tree,recipeId);
}

function validateTime(seconds) {
  if(typeof seconds!=='number' || !Number.isFinite(seconds) || seconds<0 || seconds>86400) fail('INVALID_TIME','timeSeconds must be finite and in [0, 86400]');
}

function observeDeviceLoss(device,callback) {
  const subscription={callback};
  device.lost.then(info=>{subscription.callback?.(info);subscription.callback=null;});
  // A shared device lives longer than an individual board direction. Releasing
  // this callback prevents its pending lost Promise retaining a destroyed study.
  return ()=>{subscription.callback=null;};
}

/** Browser-only. The same core preset renderer drives the preview and the capture path. */
export async function createShaderStudy(canvas,recipe,parameters={}) {
  recipe=validateRecipe(recipe);
  let effective=validateParameters(recipe.id,parameters);
  if(!canvas || typeof canvas.getContext!=='function' || typeof canvas.toBlob!=='function') fail('INVALID_CANVAS','An HTML canvas with PNG readback is required');
  if(!Number.isInteger(canvas.width) || !Number.isInteger(canvas.height) || canvas.width<=0 || canvas.height<=0) fail('INVALID_SIZE','Canvas dimensions must be positive integers');
  const state={recipeId:recipe.id,adapterVersion:ADAPTER_VERSION,upstreamVersion:SHADERS_VERSION,parameters:{...effective},timeSeconds:0,paused:true,destroyed:false,
    reconstruction:clone(recipe.reconstruction),failure:null,
    gpu:{status:'initializing',deviceCreated:false,drawCount:0,readbackCount:0,requestedWidth:canvas.width,requestedHeight:canvas.height,width:canvas.width,height:canvas.height,lastReadback:null,frameTimeMs:null,adapterInfo:null}};
  let renderer=null,device=null,raf=null,lastTick=null,serial=Promise.resolve(),stopObservingLoss=null,errorHandler=null;
  let rendererTime=0;
  const onFailure=(code,error)=>{
    if(state.destroyed) return;
    state.failure={code,message:String(error?.message ?? error)};
    state.gpu.status='failed'; state.paused=true;
    if(raf!==null) cancelAnimationFrame(raf);
    raf=null;
  };
  const assertLive=()=>{
    if(state.destroyed) fail('DESTROYED','This Shader study was destroyed');
    if(state.failure) fail(state.failure.code,state.failure.message);
  };
  const enqueue=work=>{
    const next=serial.then(work);
    serial=next.catch(()=>{});
    return next;
  };

  async function readback() {
    const blob=await new Promise((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(new ShaderStudyError('READBACK_FAILED','Canvas PNG readback returned null')),'image/png'));
    const bitmap=await createImageBitmap(blob);
    const scratch=document.createElement('canvas');scratch.width=bitmap.width;scratch.height=bitmap.height;
    const context=scratch.getContext('2d',{willReadFrequently:true});
    if(!context) {bitmap.close();fail('READBACK_FAILED','2D pixel inspection is unavailable');}
    context.drawImage(bitmap,0,0);bitmap.close();
    const pixels=context.getImageData(0,0,scratch.width,scratch.height).data;
    let nonZeroPixels=0,opaquePixels=0,min=255,max=0,checksum=2166136261;
    const unique=new Set();
    for(let i=0;i<pixels.length;i+=4) {
      if(pixels[i+3] && (pixels[i] || pixels[i+1] || pixels[i+2])) nonZeroPixels++;
      if(pixels[i+3]===255) opaquePixels++;
      min=Math.min(min,pixels[i],pixels[i+1],pixels[i+2]);max=Math.max(max,pixels[i],pixels[i+1],pixels[i+2]);
      if(i%64===0) {unique.add((pixels[i]<<16)|(pixels[i+1]<<8)|pixels[i+2]);checksum=Math.imul(checksum^pixels[i],16777619);checksum=Math.imul(checksum^pixels[i+1],16777619);checksum=Math.imul(checksum^pixels[i+2],16777619);}
    }
    const pixelDigest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',pixels)),value=>value.toString(16).padStart(2,'0')).join('');
    const observation={width:scratch.width,height:scratch.height,nonZeroPixels,opaquePixels,sampledUniqueColors:unique.size,minChannel:min,maxChannel:max,pixelDigest,hashAlgorithm:'sha256-decoded-rgba',sampledColorChecksum:(checksum>>>0).toString(16).padStart(8,'0'),parameters:{...effective},timeSeconds:state.timeSeconds,readback:'canvas-png-decoded-rgba',blobBytes:blob.size};
    if(!nonZeroPixels || unique.size<2 || max-min<2) fail('EMPTY_GPU_OUTPUT','Shader readback is empty or uniform; initialization is insufficient evidence');
    if(observation.width!==canvas.width || observation.height!==canvas.height) fail('SIZE_MISMATCH',`Canvas output dimensions changed during readback: PNG ${observation.width}x${observation.height}, canvas ${canvas.width}x${canvas.height}`);
    state.gpu.lastReadback=observation;state.gpu.readbackCount++;state.gpu.width=observation.width;state.gpu.height=observation.height;
    return observation;
  }

  async function drawAt(seconds,inspectPixels=true) {
    assertLive();validateTime(seconds);
    const started=performance.now();
    for(let attempt=0;attempt<3;attempt++) {
      device.pushErrorScope('validation');
      let drawError=null;
      try {
        await renderer.renderFrame({deltaSeconds:seconds-rendererTime,waitForGpu:true});
        rendererTime=seconds;
      } catch(error) {drawError=error;}
      const gpuError=await device.popErrorScope();
      const reason=renderer.getFailureReason();
      if(drawError || gpuError || reason) fail('GPU_DRAW_FAILED',drawError?.message ?? gpuError?.message ?? JSON.stringify(reason));
      assertLive();state.timeSeconds=seconds;state.gpu.drawCount++;
      if(inspectPixels) {
        try {await readback();}
        catch(error) {
          if(error.code==='SIZE_MISMATCH' && attempt<2) {
            // The upstream renderer observes the canvas's parent. A layout change
            // can land while toBlob is decoding; redraw that same time at the new size.
            await new Promise(resolve=>requestAnimationFrame(resolve));
            continue;
          }
          throw error;
        }
      }
      break;
    }
    state.gpu.frameTimeMs=performance.now()-started;
    if(state.gpu.readbackCount>0) state.gpu.status='ready';
    return getState();
  }

  function getState() {
    const result=clone(state),last=state.gpu.lastReadback;
    result.gpu.currentCanvasWidth=canvas.width;result.gpu.currentCanvasHeight=canvas.height;
    result.gpu.currentFrameReadbackVerified=!!last && !state.failure && !state.destroyed && last.timeSeconds===state.timeSeconds && last.width===canvas.width && last.height===canvas.height && JSON.stringify(last.parameters)===JSON.stringify(effective);
    return result;
  }
  const renderAt=seconds=>{
    validateTime(seconds);
    return enqueue(async()=>{try{return await drawAt(seconds,true);}catch(error){onFailure(error.code ?? 'RENDER_FAILED',error);throw error;}});
  };
  const setParameters=parameters=>{
    const next=validateParameters(recipe.id,parameters);
    return enqueue(async()=>{
      assertLive();
      try {renderer.updatePreset(makePreset(recipe.id,next));effective=next;state.parameters={...next};return await drawAt(state.timeSeconds,true);}
      catch(error){onFailure(error.code ?? 'PARAMETER_RENDER_FAILED',error);throw error;}
    });
  };
  function pause() {
    state.paused=true;lastTick=null;
    if(raf!==null) cancelAnimationFrame(raf);
    raf=null;
    return serial.then(getState);
  }
  function schedule() {
    if(state.paused || state.destroyed || state.failure || raf!==null) return;
    raf=requestAnimationFrame(tick);
  }
  async function tick(now) {
    raf=null;
    if(state.paused || state.destroyed || state.failure) return;
    const delta=lastTick===null?0:Math.min((now-lastTick)/1000,0.1);lastTick=now;
    try {await enqueue(()=>drawAt(Math.min(86400,state.timeSeconds+delta),false));}
    catch(error){onFailure(error.code ?? 'ANIMATION_FAILED',error);}
    schedule();
  }
  function resume() {assertLive();state.paused=false;lastTick=null;schedule();return getState();}
  function destroy() {
    if(state.destroyed) return serial;
    state.destroyed=true;state.paused=true;
    if(raf!==null) cancelAnimationFrame(raf);raf=null;
    if(device && errorHandler) device.removeEventListener('uncapturederror',errorHandler);
    stopObservingLoss?.();stopObservingLoss=null;
    return enqueue(()=>{renderer?.dispose();renderer=null;state.gpu.status='destroyed';});
  }

  try {
    const [{createRendererFromJSON},{originalDefinitions}]=await Promise.all([import('shaders/core'),import('../assets/recipes/original-fields.mjs')]);
    renderer=createRendererFromJSON(makePreset(recipe.id,effective),{components:originalDefinitions,forceFullFrameRate:true,enablePerformanceTracking:false});
    renderer.setOnUnavailable(reason=>onFailure('GPU_UNAVAILABLE',JSON.stringify(reason)));
    await renderer.initialize(canvas);
    const gpuContext=renderer.getGPUContext();
    device=gpuContext?.device;
    if(!device || !device.queue || renderer.getFailureReason() || state.failure) fail('GPU_UNAVAILABLE',state.failure?.message ?? JSON.stringify(renderer.getFailureReason()) ?? 'No GPUDevice was created');
    state.gpu.deviceCreated=true;
    const info=gpuContext.adapter?.info ?? device.adapterInfo;
    if(info) state.gpu.adapterInfo={vendor:info.vendor,architecture:info.architecture,device:info.device,description:info.description};
    errorHandler=event=>onFailure('GPU_UNCAPTURED_ERROR',event.error);
    device.addEventListener('uncapturederror',errorHandler);
    stopObservingLoss=observeDeviceLoss(device,info=>onFailure('GPU_DEVICE_LOST',`${info.reason}: ${info.message}`));
    // Let the upstream parent ResizeObserver settle before the first verified frame.
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    await drawAt(0,true);
  } catch(error) {
    onFailure(error.code ?? 'INITIALIZE_FAILED',error);
    renderer?.dispose();renderer=null;
    if(device && errorHandler) device.removeEventListener('uncapturederror',errorHandler);
    stopObservingLoss?.();stopObservingLoss=null;
    // Failure remains inspectable; UI can show static material without claiming dynamic success.
  }
  return {setParameters,renderAt,pause,resume,destroy,getState};
}
