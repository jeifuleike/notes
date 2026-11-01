const app = dv.app;
const file = app.vault.getAbstractFileByPath(input.notePath || dv.currentFilePath);
if (!file) throw new Error("找不到当前日记");
const doc = dv.container.ownerDocument;
const root = doc.createElement("div");
root.className = "daily-log";
dv.container.append(root);
let entries = (app.metadataCache.getFileCache(file)?.frontmatter?.time_entries || []).map(x => ({ ...x }));
let queue = Promise.resolve();
function el(tag, cls, text, parent) {
  const node = doc.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  if (parent) parent.append(node);
  return node;
}
const header = el("div", "daily-log-heading", undefined, root);
el("span", "", "时间", header);
el("span", "", "内容", header);
const list = el("div", "daily-log-list", undefined, root);
const status = el("div", "daily-log-status", "", root);
status.setAttribute("role", "status");
function persist(mutate) {
  const job = queue.then(async () => {
    await app.fileManager.processFrontMatter(file, fm => {
      const rows = Array.isArray(fm.time_entries) ? fm.time_entries.map(x => ({ ...x })) : [];
      mutate(rows);
      fm.time_entries = rows;
    });
    status.textContent = "";
  });
  queue = job.catch(() => {});
  return job.catch(error => { status.textContent = "保存失败：" + error.message; throw error; });
}
function patch(entry, values) {
  return persist(rows => {
    const row = rows.find(x => x._id === entry._id);
    if (!row) throw new Error("记录已改变，请重新打开日记");
    Object.assign(row, values);
  });
}
let activePicker;
function renderRow(entry) {
  const item = el("div", "daily-log-item", undefined, list);
  const row = el("div", "daily-log-row", undefined, item);
  const time = el("button", "daily-log-time", entry.time || "选择时间", row);
  time.type = "button";
  time.setAttribute("aria-label", "选择时间");
  time.setAttribute("aria-expanded", "false");
  const content = el("input", "daily-log-content", undefined, row);
  content.type = "text";
  content.value = entry.content || "";
  content.placeholder = "记录这段时间做了什么";
  content.setAttribute("aria-label", "记录内容");
  content.addEventListener("change", () => {
    patch(entry, { content: content.value }).then(() => { entry.content = content.value; }).catch(() => {});
  });
  const remove = el("button", "daily-log-remove", "×", row);
  remove.type = "button";
  remove.setAttribute("aria-label", "删除这一行");
  remove.title = "删除这一行";
  remove.addEventListener("click", async () => {
    remove.disabled = true;
    try {
      await persist(rows => { const i = rows.findIndex(x => x._id === entry._id); if (i >= 0) rows.splice(i, 1); });
      entries = entries.filter(x => x._id !== entry._id);
      item.remove();
    } catch { remove.disabled = false; }
  });
  time.addEventListener("click", () => {
    if (activePicker) activePicker.close();
    const panel = el("div", "daily-log-picker", undefined, item);
    panel.setAttribute("role", "group");
    panel.setAttribute("aria-label", "选择小时和分钟");
    time.setAttribute("aria-expanded", "true");
    const values = /^(\d{2}):(\d{2})$/.exec(entry.time || "");
    const now = new Date();
    const controls = el("div", "daily-log-clock", undefined, panel);
    function wheelPicker(label, max, value) {
      const wrap = el("div", "daily-log-wheel-column", undefined, controls);
      el("span", "daily-log-wheel-label", label, wrap);
      const frame = el("div", "daily-log-wheel-frame", undefined, wrap);
      const wheel = el("div", "daily-log-wheel", undefined, frame);
      wheel.tabIndex = 0;
      wheel.setAttribute("role", "listbox");
      wheel.setAttribute("aria-label", label);
      const size = 36;
      let selected = Math.max(0, Math.min(max - 1, value));
      const buttons = [];
      function paint() {
        buttons.forEach((button, i) => {
          button.classList.toggle("is-selected", i === selected);
          button.setAttribute("aria-selected", String(i === selected));
        });
        wheel.setAttribute("aria-activedescendant", buttons[selected].id);
      }
      function choose(index) {
        selected = Math.max(0, Math.min(max - 1, index));
        wheel.scrollTop = selected * size;
        paint();
      }
      for (let i = 0; i < max; i++) {
        const button = el("div", "daily-log-wheel-value", String(i).padStart(2, "0"), wheel);
        button.id = "daily-time-" + crypto.randomUUID();
        button.setAttribute("role", "option");
        button.addEventListener("click", () => choose(i));
        buttons.push(button);
      }
      wheel.addEventListener("scroll", () => {
        selected = Math.max(0, Math.min(max - 1, Math.round(wheel.scrollTop / size)));
        paint();
      }, { passive: true });
      let drag;
      let suppressClick = false;
      wheel.addEventListener("pointerdown", event => {
        if (event.pointerType !== "mouse" || event.button !== 0) return;
        drag = { id: event.pointerId, y: event.clientY, scroll: wheel.scrollTop, moved: false };
        wheel.focus();
        event.preventDefault();
      });
      wheel.addEventListener("pointermove", event => {
        if (!drag || drag.id !== event.pointerId) return;
        const delta = event.clientY - drag.y;
        if (!drag.moved && Math.abs(delta) < 4) return;
        if (!drag.moved) {
          drag.moved = true;
          wheel.setPointerCapture(event.pointerId);
          wheel.classList.add("is-dragging");
        }
        suppressClick = true;
        wheel.scrollTop = Math.max(0, Math.min((max - 1) * size, drag.scroll - delta));
        selected = Math.round(wheel.scrollTop / size);
        paint();
        event.preventDefault();
      });
      function finishDrag(event) {
        if (!drag || drag.id !== event.pointerId) return;
        const moved = drag.moved;
        drag = undefined;
        wheel.classList.remove("is-dragging");
        if (wheel.hasPointerCapture(event.pointerId)) wheel.releasePointerCapture(event.pointerId);
        if (moved) choose(Math.round(wheel.scrollTop / size));
        doc.defaultView.setTimeout(() => { suppressClick = false; }, 0);
      }
      wheel.addEventListener("pointerup", finishDrag);
      wheel.addEventListener("pointercancel", finishDrag);
      wheel.addEventListener("lostpointercapture", finishDrag);
      wheel.addEventListener("pointerleave", () => { if (drag && !drag.moved) drag = undefined; });
      wheel.addEventListener("click", event => {
        if (suppressClick) { event.preventDefault(); event.stopPropagation(); }
      }, true);
      wheel.addEventListener("keydown", event => {
        const shifts = { ArrowUp: -1, ArrowDown: 1, PageUp: -5, PageDown: 5 };
        if (event.key in shifts) { event.preventDefault(); choose(selected + shifts[event.key]); }
        if (event.key === "Home") { event.preventDefault(); choose(0); }
        if (event.key === "End") { event.preventDefault(); choose(max - 1); }
      });
      paint();
      doc.defaultView.requestAnimationFrame(() => { wheel.scrollTop = selected * size; });
      return { get value() { return String(selected).padStart(2, "0"); }, focus() { wheel.focus(); } };
    }
    const hour = wheelPicker("小时", 24, values ? Number(values[1]) : now.getHours());
    el("span", "daily-log-wheel-colon", ":", controls);
    const minute = wheelPicker("分钟", 60, values ? Number(values[2]) : now.getMinutes());
    const actions = el("div", "daily-log-picker-actions", undefined, panel);
    const cancel = el("button", "daily-log-cancel", "取消", actions);
    const confirm = el("button", "daily-log-confirm", "确定", actions);
    cancel.type = confirm.type = "button";
    const state = { close() { panel.remove(); time.setAttribute("aria-expanded", "false"); if (activePicker === state) activePicker = undefined; } };
    activePicker = state;
    cancel.addEventListener("click", () => { state.close(); time.focus(); });
    confirm.addEventListener("click", async () => {
      const value = hour.value + ":" + minute.value;
      confirm.disabled = true;
      try { await patch(entry, { time: value }); entry.time = value; time.textContent = value; state.close(); time.focus(); }
      catch { confirm.disabled = false; }
    });
    panel.addEventListener("keydown", event => {
      if (event.key === "Escape") { event.preventDefault(); state.close(); time.focus(); }
      if (event.key === "Enter") { event.preventDefault(); confirm.click(); }
    });
    hour.focus();
  });
}
for (const entry of entries) renderRow(entry);
const add = el("button", "daily-log-add", "＋ 添加记录", root);
add.type = "button";
add.addEventListener("click", async () => {
  add.disabled = true;
  const entry = { _id: crypto.randomUUID(), time: "", content: "" };
  try { await persist(rows => rows.push(entry)); entries.push(entry); renderRow(entry); }
  catch {} finally { add.disabled = false; }
});
