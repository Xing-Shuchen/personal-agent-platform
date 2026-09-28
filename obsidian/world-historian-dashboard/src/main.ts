import { App, FileSystemAdapter, ItemView, Modal, Notice, Plugin, PluginSettingTab, Setting, WorkspaceLeaf } from 'obsidian';
import { execFile } from 'node:child_process';
import { statSync } from 'node:fs';
import { join } from 'node:path';
import { mount, unmount } from 'svelte';
import Dashboard from './Dashboard.svelte';
import { Repository, type Ref, type SearchHit } from './model';

const VIEW_TYPE='world-historian-dashboard';
type Settings={database:string;output:string;projector:string;pythonExecutable:string;noteIndex:string;locationRegistry:string};
const defaults:Settings={database:'',output:'',projector:'',pythonExecutable:process.platform==='win32'?'python':'python3',noteIndex:'',locationRegistry:''};

class DashboardView extends ItemView {
  plugin:HistorianPlugin;
  component:ReturnType<typeof mount>|null=null;
  constructor(leaf:WorkspaceLeaf,plugin:HistorianPlugin){super(leaf);this.plugin=plugin}
  getViewType(){return VIEW_TYPE}
  getDisplayText(){return 'World Historian Dashboard'}
  getIcon(){return 'network'}
  async onOpen(){await this.render()}
  async onClose(){if(this.component){await unmount(this.component);this.component=null}}
  async render(){
    if(this.component){await unmount(this.component);this.component=null}
    const root=this.contentEl;root.empty();root.addClass('wh-dashboard-host');
    let repository:Repository|null=null;let error='';let stale=false;
    try{repository=Repository.open(this.plugin.settings.output);try{stale=statSync(this.plugin.settings.database).mtimeMs>Date.parse(repository.manifest.generated_at)}catch{repository.warning=repository.warning||'Chronicle database is unavailable; showing cached generation'}}catch(e){error=String(e)}
    try {
      this.component=mount(Dashboard,{target:root,props:{repository,error,stale,
        refresh:()=>this.plugin.refreshAndRender(),
        openNote:(path:string)=>this.plugin.openNote(path),
        openCanonical:(ref:Ref)=>this.plugin.openCanonical(ref),
        searchAll:this.plugin.settings.projector?(query:string)=>this.plugin.search(query):undefined,
        settings:()=>this.plugin.openSettings()}});
    } catch (cause) {
      root.textContent=`World Historian Dashboard failed to open: ${String(cause)}`;
      root.addClass('wh-alert');
      console.error('World Historian Dashboard failed to mount',cause);
    }
  }
}

export default class HistorianPlugin extends Plugin {
  settings:Settings=defaults;
  async onload(){
    this.settings=Object.assign({},defaults,await this.loadData());
    this.registerView(VIEW_TYPE,leaf=>new DashboardView(leaf,this));
    this.addRibbonIcon('network','World Historian Dashboard',()=>void this.activate());
    this.addCommand({id:'open-dashboard',name:'Open dashboard',callback:()=>void this.activate()});
    this.addCommand({id:'refresh-dashboard',name:'Refresh read model',callback:()=>void this.refreshAndRender()});
    this.addSettingTab(new DashboardSettings(this.app,this));
  }
  async activate(){
    let leaf=this.app.workspace.getLeavesOfType(VIEW_TYPE)[0];
    if(!leaf){leaf=this.app.workspace.getLeaf('tab');await leaf.setViewState({type:VIEW_TYPE,active:true})}
    await this.app.workspace.revealLeaf(leaf);
  }
  async refresh(){
    if(!this.settings.database||!this.settings.output||!this.settings.projector)throw Error('Configure database, output and projector paths in plugin settings');
    const args=[this.settings.projector,'--db',this.settings.database,'--output',this.settings.output];
    if(this.settings.noteIndex)args.push('--note-index',this.settings.noteIndex);
    if(this.settings.locationRegistry)args.push('--location-registry',this.settings.locationRegistry);
    if(this.app.vault.adapter instanceof FileSystemAdapter)args.push('--vault',this.app.vault.adapter.getBasePath());
    await new Promise<void>((resolve,reject)=>execFile(this.settings.pythonExecutable,args,{timeout:1800000,maxBuffer:1024*1024},(error,stdout,stderr)=>error?reject(new Error(stderr||error.message)):resolve()));
    new Notice('World Historian read model refreshed');
  }
  async refreshAndRender(){try{await this.refresh();for(const leaf of this.app.workspace.getLeavesOfType(VIEW_TYPE))await (leaf.view as DashboardView).render()}catch(e){new Notice(`Refresh failed: ${String(e)}`,10000)}}
  async search(query:string):Promise<SearchHit[]>{
    if(!this.settings.projector||!this.settings.output)return [];
    const args=[this.settings.projector,'--output',this.settings.output,'--search-query',query];
    const raw=await new Promise<string>((resolve,reject)=>execFile(this.settings.pythonExecutable,args,{timeout:15000,maxBuffer:256*1024},(error,stdout,stderr)=>error?reject(new Error(stderr||error.message)):resolve(stdout)));
    return JSON.parse(raw) as SearchHit[];
  }
  async openNote(path:string){const file=this.app.vault.getFileByPath(path);if(file)await this.app.workspace.getLeaf('tab').openFile(file);else new Notice(`Note missing: ${path}`)}
  async openCanonical(ref:Ref){
    if(ref.kind!=='chronicle'||!ref.table||!ref.id){new Notice('Canonical record is unavailable');return}
    try{
      const args=[this.settings.projector,'--db',this.settings.database,'--inspect-table',ref.table,'--inspect-id',ref.id];
      const raw=await new Promise<string>((resolve,reject)=>execFile(this.settings.pythonExecutable,args,{timeout:15000,maxBuffer:256*1024},(error,stdout,stderr)=>error?reject(new Error(stderr||error.message)):resolve(stdout)));
      const modal=new Modal(this.app);modal.titleEl.setText(`${ref.table} · ${ref.id}`);modal.contentEl.createEl('pre',{text:JSON.stringify(JSON.parse(raw).record,null,2)});modal.contentEl.addClass('wh-canonical-record');modal.open();
    }catch(e){new Notice(`Could not open canonical record: ${String(e)}`,10000)}
  }
  openSettings(){(this.app as App & {setting:{open:()=>void;openTabById:(id:string)=>void}}).setting.open();(this.app as App & {setting:{openTabById:(id:string)=>void}}).setting.openTabById(this.manifest.id)}
}

class DashboardSettings extends PluginSettingTab {
  plugin:HistorianPlugin;
  constructor(app:App,plugin:HistorianPlugin){super(app,plugin);this.plugin=plugin}
  display(){
    const el=this.containerEl;el.empty();el.createEl('h2',{text:'World Historian Dashboard'});
    for(const [key,label] of [['database','Chronicle SQLite file'],['output','Dashboard read model directory'],['projector','Projector script'],['pythonExecutable','Python executable'],['noteIndex','Obsidian thread note index'],['locationRegistry','Location registry JSON (optional)']] as const){
      new Setting(el).setName(label).addText(text=>text.setValue(this.plugin.settings[key]).onChange(async value=>{this.plugin.settings[key]=value;await this.plugin.saveData(this.plugin.settings)}));
    }
    new Setting(el).setName('Refresh').addButton(button=>button.setButtonText('Build read model').onClick(()=>void this.plugin.refreshAndRender()));
  }
}
