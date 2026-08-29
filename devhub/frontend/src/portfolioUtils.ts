export type PortfolioProjectLike={name:string;github_cache_json?:string|null};

type CacheShape={open_pr_count?:number;open_prs?:{created_at?:string;updated_at?:string}[];last_merged_pr?:{merged_at?:string}};

const cache=(project:PortfolioProjectLike):CacheShape=>{try{return project.github_cache_json?JSON.parse(project.github_cache_json):{}}catch{return {}}};

export const relativeTime=(value?:string|null,nowMs=Date.now())=>{
  if(!value)return 'Not yet';
  const parsed=Date.parse(value);
  if(Number.isNaN(parsed))return 'Unknown';
  const ms=nowMs-parsed;
  const mins=Math.max(0,Math.floor(ms/60000));
  if(mins<1)return 'just now';
  if(mins<60)return `${mins} min ago`;
  const hrs=Math.floor(mins/60);
  if(hrs<24)return `${hrs} ${hrs===1?'hour':'hours'} ago`;
  const days=Math.floor(hrs/24);
  if(days===1)return 'yesterday';
  return `${days} days ago`;
};

const oldestOpenPrTime=(project:PortfolioProjectLike)=>{
  const prs=cache(project).open_prs||[];
  const times=prs.map(pr=>Date.parse(pr.updated_at||pr.created_at||'')).filter(Number.isFinite);
  return times.length?Math.min(...times):Number.POSITIVE_INFINITY;
};

const lastMergedTime=(project:PortfolioProjectLike)=>{
  const value=cache(project).last_merged_pr?.merged_at;
  const parsed=value?Date.parse(value):Number.NaN;
  return Number.isFinite(parsed)?parsed:Number.POSITIVE_INFINITY;
};

export const sortPortfolioProjects=<T extends PortfolioProjectLike>(list:T[])=>[...list].sort((a,b)=>{
  const aOpen=(cache(a).open_pr_count||0)>0;
  const bOpen=(cache(b).open_pr_count||0)>0;
  if(aOpen!==bOpen)return aOpen?-1:1;
  const aTime=aOpen?oldestOpenPrTime(a):lastMergedTime(a);
  const bTime=bOpen?oldestOpenPrTime(b):lastMergedTime(b);
  if(aTime!==bTime)return aTime-bTime;
  return a.name.localeCompare(b.name);
});
