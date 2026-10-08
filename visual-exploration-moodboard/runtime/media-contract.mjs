import {inflateSync} from 'node:zlib';
import {createHash} from 'node:crypto';

function require(condition,message){if(!condition){const error=new Error(message);error.code='INVALID_PNG';throw error;}}
// Captured PNGs use 8-bit, noninterlaced RGB/RGBA. Decode the actual pixels;
// a filename or a caller-supplied nonTransparent count is not media evidence.
export function decodePNG(bytes){
  require(Buffer.isBuffer(bytes)&&bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])),'PNG signature missing');
  let offset=8,width,height,channels,ended=false;const parts=[];
  while(offset<bytes.length){require(offset+12<=bytes.length,'Truncated PNG chunk');const length=bytes.readUInt32BE(offset),type=bytes.toString('ascii',offset+4,offset+8);require(offset+length+12<=bytes.length,'Truncated PNG data');const data=bytes.subarray(offset+8,offset+8+length);
    if(type==='IHDR'){require(width===undefined&&length===13,'Invalid IHDR');width=data.readUInt32BE(0);height=data.readUInt32BE(4);channels=data[9]===6?4:data[9]===2?3:0;require(width>0&&height>0&&width*height<=40000000&&data[8]===8&&channels&&data[10]===0&&data[11]===0&&data[12]===0,'Unsupported PNG dimensions/format');}
    else if(type==='IDAT'){require(width!==undefined,'PNG data precedes header');parts.push(data);}
    else if(type==='IEND'){require(length===0,'Invalid IEND');ended=true;offset+=12;break;}
    offset+=length+12;
  }
  require(ended&&offset===bytes.length&&parts.length,'Incomplete PNG');const rowBytes=width*channels;let raw;
  try{raw=inflateSync(Buffer.concat(parts),{maxOutputLength:(rowBytes+1)*height});}catch{require(false,'Invalid PNG compressed data');}
  require(raw.length===(rowBytes+1)*height,'PNG decompressed size mismatch');
  const decoded=Buffer.alloc(rowBytes*height);const paeth=(a,b,c)=>{const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;};
  for(let y=0;y<height;y++){const start=y*(rowBytes+1),filter=raw[start];require(filter<=4,'Invalid PNG filter');for(let x=0;x<rowBytes;x++){const a=x>=channels?decoded[y*rowBytes+x-channels]:0,b=y?decoded[(y-1)*rowBytes+x]:0,c=y&&x>=channels?decoded[(y-1)*rowBytes+x-channels]:0;decoded[y*rowBytes+x]=(raw[start+1+x]+[0,a,b,Math.floor((a+b)/2),paeth(a,b,c)][filter])&255;}}
  const rgba=channels===4?decoded:Buffer.alloc(width*height*4);if(channels===3)for(let i=0,j=0;i<decoded.length;i+=3,j+=4){rgba[j]=decoded[i];rgba[j+1]=decoded[i+1];rgba[j+2]=decoded[i+2];rgba[j+3]=255;}
  let nonTransparent=0,nonZero=0;for(let i=0;i<rgba.length;i+=4){if(rgba[i+3])nonTransparent++;if(rgba[i]||rgba[i+1]||rgba[i+2])nonZero++;}
  return {width,height,nonTransparent,nonZero,pixelDigest:createHash('sha256').update(rgba).digest('hex')};
}
