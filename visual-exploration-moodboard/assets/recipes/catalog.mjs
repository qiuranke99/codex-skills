// Original program studies authored for this package. No shaders.com Content is embedded.
export const ADAPTER_VERSION = '1.0.0';
export const SHADERS_VERSION = '4.0.2';

const number = (label, meaning, min, max, step, value) => ({type:'number',label,meaning,min,max,step,default:value});
const common = {
  revision: 1,
  upstream: {package:'shaders',version:SHADERS_VERSION},
  adapterVersion:ADAPTER_VERSION,
  resources:[],
  reconstruction:{kind:'stateless-analytic',clock:'host-seconds',initialState:'none',inputTrack:'none',seedBindings:[],crossGpuPixelIdentity:false},
  colorPolicy:'shaders-core-default / opaque-sdr / browser-canvas-png',
};
const entries = [
  {
    id:'luminous-order', recipeId:'luminous-order',title:'光的秩序',
    description:'平行光带在纵深中保持秩序，局部汇聚的光锋交替显露边缘与暗面。研究精密、留白与高光宽度的关系。',
    mechanism:'ordered-light-ribbons',componentType:'VemLuminousOrder',
    parameters:{
      discipline:number('秩序密度','改变结构层数与纵深，不改变整体注意力方向。',3,11,1,7),
      aperture:number('光带宽度','在窄边缘与柔和大面之间比较显露关系。',0.06,0.5,0.01,0.2),
      bend:number('曲面张力','控制平行结构的弯曲与空间压缩。',0,1,0.01,0.58),
      warmth:number('光色温度','在青白与暖银之间变化，属于本方向的色彩变体。',0,1,0.01,0.4),
      tempo:number('显露速度','控制光锋掠过结构的速度；零为固定状态。',0,1.5,0.01,0.65),
    },
  },
  {
    id:'envelop-reveal', recipeId:'envelop-reveal',title:'包裹与显露',
    description:'两层弯曲表面环抱中心负空间，开合让内部显露。研究保护、距离与揭示的先后关系。',
    mechanism:'occlusion-aperture',componentType:'VemEnvelopReveal',
    parameters:{
      opening:number('开口尺度','改变中心负空间与包裹表面的占比。',0.08,0.82,0.01,0.43),
      wrap:number('包裹深度','改变外层与内层之间的遮挡和深度线索。',0,1,0.01,0.67),
      softness:number('过渡柔度','在清晰薄边与宽柔曲面之间调节。',0.05,0.9,0.01,0.38),
      warmth:number('表面温度','在陶土、珊瑚与骨白表面之间比较色彩变体。',0,1,0.01,0.65),
      tempo:number('呼吸速度','控制包裹结构缓慢开合的完整周期。',0,1.5,0.01,0.45),
    },
  },
  {
    id:'affinity-field', recipeId:'affinity-field',title:'关系的聚合',
    description:'分离的节点围绕共同中心聚合，连线随距离衰减。研究个体、关系与中心的观看权重。',
    mechanism:'proximity-network',componentType:'VemAffinityField',
    parameters:{
      cohesion:number('聚合强度','改变独立节点向共同中心收拢的程度。',0,1,0.01,0.53),
      reach:number('关系距离','决定哪些节点之间出现可见连接，以及连接衰减。',0.1,1,0.01,0.72),
      scale:number('节点尺度','比较个体的质量感与网络整体的权重。',0.25,1,0.01,0.62),
      warmth:number('关系温度','只改变色彩，不把配色变化登记为新方向。',0,1,0.01,0.7),
      tempo:number('聚合速度','控制节点分离与汇聚的时间关系。',0,1.5,0.01,0.5),
    },
  },
];

export function deepFreeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const part of Object.values(value)) deepFreeze(part);
    Object.freeze(value);
  }
  return value;
}

export const recipeCatalog = deepFreeze(entries.map(entry => {
  const props = Object.fromEntries(Object.entries(entry.parameters).map(([key,value])=>[key,value.default]));
  return {...common,...entry,componentTree:{structureVersion:1,components:[{type:entry.componentType,id:`${entry.id}-field`,props:{...props,opacity:1,visible:true,blendMode:'normal'},children:[]}]}};
}));
