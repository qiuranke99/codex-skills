const operations=new Set(['display','layout-crop','background-composite','subject-color-material','geometry-change','generative-repaint','original-creation']);
function ensure(condition,code,message){if(!condition){const error=new Error(message);error.code=code;throw error;}}
const identifiers=value=>Array.isArray(value)&&value.every(x=>typeof x==='string'&&x.trim().length>0)&&new Set(value).size===value.length;
export function validateAsset(asset){
  ensure(asset&&typeof asset==='object','ASSET_CONTRACT','Asset must be an object');
  const rights=asset.rights,permission=asset.authorization,operation=asset.operation;
  ensure(rights&&['self-owned','licensed','reference-only'].includes(rights.status)&&typeof rights.display==='boolean'&&typeof rights.redistribution==='boolean'&&rights.evidenceRef,'ASSET_RIGHTS_MISSING','Asset rights and their hash-bound basis are required');
  if(rights.status==='reference-only'||!rights.display||!rights.redistribution||asset.license?.redistribution===false||asset.license?.allowedUse==='source-link-only')ensure(!asset.url,'ASSET_LINK_ONLY','Link-only/nonredistributable sources cannot be embedded or served as board assets');
  if(!asset.url)return asset;
  ensure(asset.sourceRef&&permission&&Array.isArray(permission.operations)&&Array.isArray(permission.regions)&&Array.isArray(permission.immutableProperties),'ASSET_AUTHORIZATION_MISSING','Embedded assets require operations, regions and immutable properties');
  ensure(identifiers(permission.operations)&&permission.operations.length>0&&permission.operations.every(x=>operations.has(x))&&identifiers(permission.regions)&&permission.regions.length>0&&identifiers(permission.immutableProperties),'ASSET_AUTHORIZATION_INVALID','Authorization requires unique supported operation and region/property identifiers');
  ensure(operation&&operations.has(operation.type)&&typeof operation.region==='string'&&operation.region.trim()&&operation.authorizationRef&&Array.isArray(operation.affectedProperties),'ASSET_OPERATION_MISSING','Actual operation, region, affected properties and authority reference are required');
  ensure(identifiers(operation.affectedProperties),'ASSET_OPERATION_INVALID','Affected properties must be unique nonempty identifiers');
  ensure(permission.operations.includes(operation.type)&&permission.regions.includes(operation.region),'ASSET_OPERATION_FORBIDDEN','Operation or region exceeds the recorded authorization');
  ensure(!operation.affectedProperties.some(value=>permission.immutableProperties.includes(value)),'ASSET_LOCK_VIOLATION','Operation changes an immutable property');
  if(['background-composite','subject-color-material','geometry-change','generative-repaint'].includes(operation.type))ensure(Array.isArray(operation.parentRefs)&&operation.parentRefs.length,'ASSET_PARENTS_MISSING','Modification requires hash-bound parent inputs');
  if(operation.region!=='whole-asset')ensure(operation.maskRef,'ASSET_MASK_MISSING','Partial-region modifications require a hash-bound mask/region definition');
  return asset;
}
export async function verifyAsset(root,asset,verifyFile){
  validateAsset(asset);await verifyFile(root,asset.rights.evidenceRef);
  if(asset.url){await verifyFile(root,asset.sourceRef);await verifyFile(root,asset.operation.authorizationRef);for(const ref of asset.operation.parentRefs||[])await verifyFile(root,ref);if(asset.operation.maskRef)await verifyFile(root,asset.operation.maskRef);}
}
