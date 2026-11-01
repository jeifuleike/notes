const app = dv.app;
const path = dv.currentFilePath;
const file = app.vault.getAbstractFileByPath(path);
const scope = dv.container.closest('.markdown-preview-view, .markdown-source-view');
const pattern = /^> \[!growth-card\][-+]?([^\n]*)\n[\s\S]*?(?=^> \[!growth-card\]|^## |$(?![\s\S]))/gm;
function filled(v) {
  if (v == null || v === false) return false;
  if (typeof v === 'boolean') return v;
  if (typeof v === 'number') return v !== 0;
  if (typeof v === 'string') return !['', '未选择', '未记录', '未填写'].includes(v.trim());
  if (Array.isArray(v)) return v.some(filled);
  if (typeof v === 'object') return Object.entries(v).some(([k,x]) => k !== '_id' && filled(x));
  return false;
}
function keys(block) {
  const result = [...block.matchAll(/INPUT\[[^\n]*?:([a-zA-Z_0-9]+)\]/g)].map(x => x[1]);
  if (block.includes('组件/时间记录')) result.push('time_entries');
  return result;
}
function titleKey(s) { return s.replace(/[^\p{L}\p{N}]/gu, ''); }
let stopped = false;
let timer;
let running = false;
let again = false;
async function update() {
  if (stopped) return;
  if (running) { again = true; return; }
  running = true;
  try {
    const source = await app.vault.read(file);
    const data = app.metadataCache.getFileCache(file)?.frontmatter;
    if (!data) return;
    const states = new Map();
    const revised = source.replace(pattern, (block, title) => {
      const expand = keys(block).some(k => filled(data[k]));
      states.set(titleKey(title), expand);
      return block.replace(/^(> \[!growth-card\])[-+]?/, '$1' + (expand ? '+' : '-'));
    });
    if (revised !== source && !stopped) {
      await app.vault.process(file, current => current === source ? revised : current);
    }
    if (scope && !stopped) {
      for (const card of scope.querySelectorAll('.callout[data-callout="growth-card"]')) {
        const label = card.querySelector('.callout-title-inner');
        const expand = states.get(titleKey(label?.textContent || ''));
        if (expand === undefined) continue;
        const state = String(expand);
        if (card.dataset.contentFoldState === state) continue;
        card.dataset.contentFoldState = state;
        if (card.classList.contains('is-collapsed') === expand) card.querySelector('.callout-title')?.click();
      }
    }
  } catch (e) { console.error('日报卡片折叠更新失败', e); }
  finally { running = false; if (again) { again = false; schedule(); } }
}
function schedule() {
  if (stopped) return;
  dv.container.ownerDocument.defaultView.clearTimeout(timer);
  timer = dv.container.ownerDocument.defaultView.setTimeout(update, 180);
}
dv.component.registerEvent(app.metadataCache.on('changed', changed => { if (changed.path === path) schedule(); }));
if (scope) {
  const observer = new dv.container.ownerDocument.defaultView.MutationObserver(schedule);
  observer.observe(scope, { childList:true, subtree:true });
  dv.component.register(() => observer.disconnect());
}
dv.component.register(() => { stopped = true; dv.container.ownerDocument.defaultView.clearTimeout(timer); });
await update();
