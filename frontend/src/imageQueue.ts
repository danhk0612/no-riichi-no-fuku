import {useSyncExternalStore} from 'react'
import {apiRequest} from './api'

const listeners = new Set<()=>void>()
const pending = new Map<string,Promise<unknown>>()
let tail:Promise<unknown> = Promise.resolve()
let active = '', revision = 0
function publish() { revision++; for (const listener of listeners) listener() }
export function useImageQueue() {
  useSyncExternalStore(listener=>{listeners.add(listener);return ()=>{listeners.delete(listener)}},()=>revision)
  return {active,count:pending.size,waiting:Math.max(0,pending.size-(active?1:0)),pending}
}
export function queueImage<T>(key:string, work:()=>Promise<T>):Promise<T> {
  const existing=pending.get(key)
  if(existing) return existing as Promise<T>
  const job=tail.then(async()=>{active=key;publish();return work()}).finally(()=>{
    pending.delete(key);active='';publish()
  })
  tail=job.catch(()=>undefined)
  pending.set(key,job);publish()
  return job
}
export type ImageStatus={state:string;attempt?:string}
export async function pollImage(path:string,query='',retry?:string) {
  const params=new URLSearchParams(query)
  if(retry)params.set('retry',retry)
  for(;;){
    const result=await apiRequest<ImageStatus>(path+'?'+params,{method:'POST'})
    if(result.state!=='pending')return result
    params.delete('retry');params.delete('regenerate')
    await new Promise(resolve=>setTimeout(resolve,1500))
  }
}
