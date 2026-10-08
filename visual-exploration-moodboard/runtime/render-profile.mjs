// Authority captures are reproducible layout studies. Responsive previews may use other sizes.
export const AUTHORITY_RENDER_PROFILE = Object.freeze({
  schemaVersion: 1,
  id: 'vem-sdr-srgb-1440x1000-v1',
  viewport: Object.freeze({width: 1440, height: 1000}),
  deviceScaleFactor: 1,
  colorScheme: 'light',
  reducedMotion: 'reduce',
  dynamicRange: 'sdr',
  colorSpace: 'srgb',
});
export const authorityRenderProfile = AUTHORITY_RENDER_PROFILE;

export class RenderProfileError extends Error {
  constructor(message) {
    super(message);
    this.name = 'RenderProfileError';
    this.code = 'RENDER_PROFILE_MISMATCH';
    this.exitCode = 1;
  }
}
const plain = value => !!value && typeof value === 'object' && !Array.isArray(value) && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
const stable = value => JSON.stringify(value, function (_key, item) {
  return plain(item) ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item;
});
function requireValue(condition, message) {if (!condition) throw new RenderProfileError(message);}
const sha256 = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const positiveInteger = value => Number.isSafeInteger(value) && value > 0;

export function assertAuthorityRenderProfile(profile) {
  requireValue(plain(profile), 'A complete authority render profile is required');
  requireValue(Object.keys(profile).length === Object.keys(AUTHORITY_RENDER_PROFILE).length && Object.keys(profile).every(key => Object.hasOwn(AUTHORITY_RENDER_PROFILE,key)), 'Unknown or missing authority profile fields');
  requireValue(plain(profile.viewport) && Object.keys(profile.viewport).length === 2 && Object.hasOwn(profile.viewport,'width') && Object.hasOwn(profile.viewport,'height'), 'Authority viewport must contain only width and height');
  requireValue(stable(profile) === stable(AUTHORITY_RENDER_PROFILE), 'Authority captures require 1440×1000, DPR 1, light, reduced motion, SDR sRGB');
  return structuredClone(AUTHORITY_RENDER_PROFILE);
}

// Explicit capture settings are checked, never silently replaced by defaults.
export function resolveAuthorityRenderProfile(options = {}) {
  requireValue(plain(options), 'Capture options must be an object');
  const allowed = new Set(['url','chromiumPath','renderProfile','viewport','deviceScaleFactor','colorScheme','reducedMotion','dynamicRange','colorSpace']);
  requireValue(Object.keys(options).every(key => allowed.has(key)), 'Unsupported authority capture option');
  if (Object.hasOwn(options,'renderProfile')) assertAuthorityRenderProfile(options.renderProfile);
  for (const key of ['viewport','deviceScaleFactor','colorScheme','reducedMotion','dynamicRange','colorSpace']) {
    if (Object.hasOwn(options,key)) {
      if (key === 'viewport') assertAuthorityRenderProfile({...AUTHORITY_RENDER_PROFILE,viewport:options.viewport});
      else requireValue(options[key] === AUTHORITY_RENDER_PROFILE[key], `Authority ${key} must equal ${AUTHORITY_RENDER_PROFILE[key]}`);
    }
  }
  return structuredClone(AUTHORITY_RENDER_PROFILE);
}

export function assertRenderEnvironment(profile, environment, pixels) {
  assertAuthorityRenderProfile(profile);
  requireValue(plain(environment) && plain(environment.viewport), 'Actual browser render environment is required');
  requireValue(stable(environment.viewport) === stable(profile.viewport), 'Observed viewport differs from the authority profile');
  for (const key of ['deviceScaleFactor','colorScheme','reducedMotion','dynamicRange']) requireValue(environment[key] === profile[key], `Observed ${key} differs from the authority profile`);
  const canvas = environment.canvas;
  requireValue(plain(canvas) && canvas.colorSpace === profile.colorSpace && canvas.toneMapping === 'standard', 'Observed WebGPU canvas requires SDR sRGB output');
  requireValue(positiveInteger(canvas.width) && positiveInteger(canvas.height), 'Observed canvas dimensions must be positive integers');
  if (pixels !== undefined) requireValue(plain(pixels) && positiveInteger(pixels.width) && positiveInteger(pixels.height) && canvas.width === pixels.width && canvas.height === pixels.height, 'Observed canvas dimensions differ from actual decoded pixels');
  return structuredClone(environment);
}

function reference(value, label) {
  requireValue(plain(value) && typeof value.path === 'string' && value.path.length > 0 && sha256(value.sha256), `${label} requires a path and SHA256`);
  return {path:value.path,sha256:value.sha256};
}

// Stable pixel identity survives identical re-captures (e.g. PNG followed by PDF).
// Receipt timestamps are deliberately absent; output/profile changes remain observable.
export function renderBinding(receipt) {
  requireValue(plain(receipt) && receipt.schemaVersion === 1 && receipt.kind === 'actual-shader-frame', 'An actual shader render receipt is required');
  requireValue(typeof receipt.directionId === 'string' && receipt.directionId.length > 0, 'Render direction is required');
  requireValue(sha256(receipt.snapshotDigest) && sha256(receipt.engineDigest), 'Render snapshot and engine digests are required');
  const renderProfile = assertAuthorityRenderProfile(receipt.renderProfile);
  const pixels = receipt.pixels;
  requireValue(plain(pixels) && positiveInteger(pixels.width) && positiveInteger(pixels.height) && sha256(pixels.decodedDigest), 'Render dimensions and decoded pixel SHA256 are required');
  let composition = null;
  if (receipt.composition !== undefined && receipt.composition !== null) {
    const scene = receipt.composition;
    requireValue(plain(scene) && scene.enabled === true && sha256(scene.sourceDigest), 'Enabled composition and scene source SHA256 are required');
    requireValue(plain(scene.pixels) && positiveInteger(scene.pixels.width) && positiveInteger(scene.pixels.height) && sha256(scene.pixels.decodedDigest), 'Composition dimensions and decoded pixel SHA256 are required');
    composition = {enabled:true,sceneDigest:scene.sourceDigest,output:reference(scene.output,'Composition output'),pixels:{width:scene.pixels.width,height:scene.pixels.height,decodedDigest:scene.pixels.decodedDigest}};
  }
  return {directionId:receipt.directionId,snapshotDigest:receipt.snapshotDigest,engineDigest:receipt.engineDigest,renderProfile,
    output:reference(receipt.output,'Render output'),
    pixels:{width:pixels.width,height:pixels.height,decodedDigest:pixels.decodedDigest},composition};
}
