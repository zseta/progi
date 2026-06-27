function boardView() {
  return {
    modalOpen: false,

    init() {
      // Deep-link: auto-open modal if URL is /tasks/{id}
      const match = window.location.pathname.match(/\/tasks\/(\d+)/);
      if (match) {
        this.openTask(parseInt(match[1]));
      }
      window.addEventListener('refresh-board', () => this.refreshBoard());
    },

    closeModal() {
      this.modalOpen = false;
      history.replaceState(null, '', '/');
    },

    async refreshBoard() {
      const board = document.getElementById('board');
      if (!board) return;
      const resp = await fetch('/board', { headers: { 'X-Alpine-Request': '1' } });
      const html = await resp.text();
      board.outerHTML = html;
    },

    async openTask(taskId) {
      this.modalOpen = true;
      await this.$nextTick();
      const container = document.getElementById('task-detail');
      const resp = await fetch(`/tasks/${taskId}`, {
        headers: { 'X-Partial': '1' },
      });
      const html = await resp.text();
      container.innerHTML = html;
      Alpine.initTree(container);
      history.replaceState(null, '', `/tasks/${taskId}`);
    },
  };
}

function taskDetail() {
  return {
    task: null,
    stepInstances: [],

    init() {
      const data = JSON.parse(document.getElementById('task-detail-data').textContent);
      this.task = data.task;
      this.stepInstances = data.stepInstances;
    },

    async deleteTask(taskId) {
      if (!confirm('Delete this task permanently? This cannot be undone.')) return;
      const resp = await fetch(`/tasks/${taskId}`, { method: 'DELETE' });
      if (resp.ok) {
        this.$dispatch('close-modal');
        this.$dispatch('refresh-board');
      }
    },
  };
}

function workflowEditor() {
  return {
    workflows: [],
    activeId: null,
    activeWorkflow: null,
    modalOpen: false,
    openMenuId: null,
    renamingId: null,
    renameValue: '',
    zoom: 1,
    panX: 0,
    panY: 0,
    _drag: null,   // { startX, startY, originX, originY } while dragging

    init() {
      this.workflows = JSON.parse(document.getElementById('workflows-data').textContent);

      // Configure Mermaid with dark theme matching design tokens
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        themeVariables: {
          background:        '#000000',   // surface-0
          mainBkg:           '#111111',   // surface-2 (node fill)
          nodeBorder:        'rgba(255,255,255,0.08)',
          clusterBkg:        '#0a0a0a',
          titleColor:        '#fafafa',   // text-primary
          edgeLabelBackground: '#0a0a0a',
          lineColor:         '#00a3ff',   // accent
          primaryTextColor:  '#fafafa',
          secondaryTextColor:'#a1a1aa',  // text-secondary
          tertiaryTextColor: '#71717a',  // text-muted
          fontSize:          '12px',
        },
        flowchart: {
          curve: 'basis',
          useMaxWidth: false,
        },
        securityLevel: 'loose', // needed so we can attach click handlers
      });

      // Deep-link: /workflows/{id}/steps/{id} or just /workflows/{id}
      const stepMatch = window.location.pathname.match(/\/workflows\/(\d+)\/steps\/(\d+)/);
      const wfMatch  = window.location.pathname.match(/\/workflows\/(\d+)(?:\/|$)/);
      if (stepMatch) {
        const wfId = parseInt(stepMatch[1]);
        const stepId = parseInt(stepMatch[2]);
        this.selectWorkflow(wfId).then(() => {
          this.openStep(wfId, stepId);
        });
      } else if (wfMatch) {
        this.selectWorkflow(parseInt(wfMatch[1]));
      }
    },

    closeModal() {
      this.modalOpen = false;
      history.replaceState(null, '', `/workflows/${this.activeId}`);
    },

    async selectWorkflow(id) {
      if (this.activeId === id) return;
      this.activeId = id;
      this.modalOpen = false;
      history.pushState(null, '', `/workflows/${id}`);

      const resp = await fetch(`/workflows/${id}/graph`);
      const wf = await resp.json();
      this.activeWorkflow = wf;
      await this._renderMermaid(wf.steps, wf.edges || []);
    },

    async openStep(workflowId, stepId) {
      this.modalOpen = true;
      await this.$nextTick();
      const container = document.getElementById('step-detail');
      const resp = await fetch(`/workflows/${workflowId}/steps/${stepId}`, {
        headers: { 'X-Partial': '1' },
      });
      const html = await resp.text();
      container.innerHTML = html;
      Alpine.initTree(container);
      history.pushState(null, '', `/workflows/${workflowId}/steps/${stepId}`);
    },

    startRename(wf) {
      this.renamingId = wf.id;
      this.renameValue = wf.name;
      this.openMenuId = null;
      this.$nextTick(() => {
        const input = document.getElementById(`rename-input-${wf.id}`);
        if (input) { input.focus(); input.select(); }
      });
    },

    cancelRename() {
      this.renamingId = null;
      this.renameValue = '';
    },

    async commitRename(id) {
      const name = this.renameValue.trim();
      if (!name) { this.cancelRename(); return; }
      const wf = this.workflows.find(w => w.id === id);
      if (wf && name === wf.name) { this.cancelRename(); return; }

      const resp = await fetch(`/workflows/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (resp.ok) {
        const updated = await resp.json();
        this.workflows = this.workflows.map(w => w.id === id ? { ...w, name: updated.name } : w);
        if (this.activeWorkflow && this.activeWorkflow.id === id) {
          this.activeWorkflow = { ...this.activeWorkflow, name: updated.name };
        }
      }
      this.cancelRename();
    },

    async copyWorkflow(id) {
      const resp = await fetch(`/workflows/${id}/export`);
      if (!resp.ok) return;
      const text = await resp.text();
      await navigator.clipboard.writeText(text);
      this.openMenuId = null;
    },

    async deleteWorkflow(id) {
      if (!confirm('Are you sure you want to delete this workflow? All tasks associated with it will also be permanently deleted. This cannot be undone.')) return;
      const resp = await fetch(`/workflows/${id}`, { method: 'DELETE' });
      if (resp.ok) {
        this.workflows = this.workflows.filter(wf => wf.id !== id);
        if (this.activeId === id) {
          this.activeId = null;
          this.activeWorkflow = null;
          document.getElementById('mermaid-container').innerHTML = '';
          history.replaceState(null, '', '/workflows');
        }
      }
      this.openMenuId = null;
    },

    zoomBy(delta) {
      this.zoom = Math.min(4, Math.max(0.2, this.zoom + delta));
      this._applyTransform();
    },

    resetZoom() {
      const container = document.getElementById('mermaid-container');
      const svgEl = container && container.querySelector('svg');
      if (svgEl) {
        const diagramW = parseFloat(svgEl.style.width)  || svgEl.getBoundingClientRect().width;
        const diagramH = parseFloat(svgEl.style.height) || svgEl.getBoundingClientRect().height;
        const padding = 48;
        const scale = Math.min(
          (container.clientWidth  - padding) / diagramW,
          (container.clientHeight - padding) / diagramH,
          1
        );
        this.zoom = scale;
        this.panX = (container.clientWidth  - diagramW * scale) / 2;
        this.panY = (container.clientHeight - diagramH * scale) / 2;
      } else {
        this.zoom = 1;
        this.panX = 0;
        this.panY = 0;
      }
      this._applyTransform();
    },

    onWheel(e) {
      const container = document.getElementById('mermaid-container');
      const rect = container.getBoundingClientRect();
      // Mouse position relative to container
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      // Point in diagram space under the cursor before zoom
      const diagramX = (mouseX - this.panX) / this.zoom;
      const diagramY = (mouseY - this.panY) / this.zoom;

      const delta = e.deltaY < 0 ? 0.1 : -0.1;
      this.zoom = Math.min(4, Math.max(0.2, this.zoom + delta));

      // Adjust pan so the same diagram point stays under the cursor
      this.panX = mouseX - diagramX * this.zoom;
      this.panY = mouseY - diagramY * this.zoom;
      this._applyTransform();
    },

    onDragStart(e) {
      if (e.button !== 0) return;
      this._drag = { startX: e.clientX, startY: e.clientY, originX: this.panX, originY: this.panY, moved: false };
    },

    onDragMove(e) {
      if (!this._drag) return;
      const dx = e.clientX - this._drag.startX;
      const dy = e.clientY - this._drag.startY;
      // Only commit to a drag once the mouse has moved a few pixels
      if (!this._drag.moved && Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
      if (!this._drag.moved) {
        // Confirmed drag — disable SVG pointer events so mousemove stays on the container
        this._drag.moved = true;
        const container = document.getElementById('mermaid-container');
        container.style.cursor = 'grabbing';
        const svg = container.querySelector('svg');
        if (svg) svg.style.pointerEvents = 'none';
      }
      this.panX = this._drag.originX + dx;
      this.panY = this._drag.originY + dy;
      this._applyTransform();
    },

    onDragEnd(e) {
      if (!this._drag) return;
      const wasDrag = this._drag.moved;
      this._drag = null;
      const container = document.getElementById('mermaid-container');
      container.style.cursor = 'grab';
      const svg = container.querySelector('svg');
      if (svg) svg.style.pointerEvents = '';
      // Suppress the upcoming click only when the mouse actually dragged
      if (wasDrag) {
        container.addEventListener('click', e => e.stopPropagation(), { capture: true, once: true });
      }
    },

    _applyTransform() {
      const svg = document.querySelector('#mermaid-container svg');
      if (svg) svg.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.zoom})`;
    },

    async _renderMermaid(steps, edges) {
      const container = document.getElementById('mermaid-container');
      container.innerHTML = '';
      this.zoom = 1;
      this.panX = 0;
      this.panY = 0;

      if (!steps || steps.length === 0) return;

      // Build step id → step lookup
      const stepById = {};
      steps.forEach(s => { stepById[s.id] = s; });

      // Build Mermaid flowchart definition (top-to-bottom)
      let def = 'flowchart TB\n';

      // Add nodes — sanitize names for Mermaid IDs
      steps.forEach(s => {
        const nodeId = `step_${s.id}`;
        const label = escapeHtml(s.name);
        def += `  ${nodeId}["${label}"]\n`;
      });

      // Add edges
      if (edges.length > 0) {
        edges.forEach(e => {
          const from = `step_${e.from_step_id}`;
          const to   = `step_${e.to_step_id}`;
          if (e.condition) {
            const label = _conditionLabel(e.condition);
            def += `  ${from} -->|"${label}"| ${to}\n`;
          } else {
            def += `  ${from} --> ${to}\n`;
          }
        });
      } else {
        // Fallback: linear by order
        const ordered = [...steps].sort((a, b) => a.order - b.order);
        for (let i = 0; i < ordered.length - 1; i++) {
          def += `  step_${ordered[i].id} --> step_${ordered[i+1].id}\n`;
        }
      }

      // Render to SVG
      const { svg } = await mermaid.render('mermaid-graph', def);
      container.innerHTML = svg;

      // Fit SVG to container at natural size, centered
      const svgEl = container.querySelector('svg');
      if (!svgEl) return;

      // Read the natural diagram dimensions from the viewBox
      const vb = svgEl.viewBox.baseVal;
      const diagramW = vb.width  || svgEl.getBoundingClientRect().width;
      const diagramH = vb.height || svgEl.getBoundingClientRect().height;

      // Leave the SVG at its natural size so transform-origin: 0 0 works cleanly
      svgEl.removeAttribute('width');
      svgEl.removeAttribute('height');
      svgEl.style.width  = diagramW + 'px';
      svgEl.style.height = diagramH + 'px';

      // Scale to fit the container with some padding
      const containerW = container.clientWidth;
      const containerH = container.clientHeight;
      const padding = 48;
      const scale = Math.min(
        (containerW - padding) / diagramW,
        (containerH - padding) / diagramH,
        1  // never scale up beyond natural size
      );

      // Center the scaled diagram
      this.zoom = scale;
      this.panX = (containerW - diagramW * scale) / 2;
      this.panY = (containerH - diagramH * scale) / 2;
      this._applyTransform();

      steps.forEach(s => {
        // Mermaid 11 generates g elements with id "flowchart-step_{id}-{n}" OR
        // just "flowchart-step_{id}" — match both with a prefix that ends in
        // the id followed by either "-" or end-of-string (via two selectors).
        const nodeEls = svgEl.querySelectorAll(`g[id*="step_${s.id}"]`);
        nodeEls.forEach(el => {
          el.style.cursor = 'pointer';
          el.addEventListener('click', () => {
            this.openStep(this.activeId, s.id);
          });
        });
      });
    },
  };
}

function stepDetail() {
  return {
    workflowId: null,
    stepId: null,
    stepName: '',
    playbook: '',
    prevSteps: [],
    nextSteps: [],
    libraryEntryId: null,
    editing: { playbook: false },
    drafts:  { playbook: '' },
    errors:  {},

    init() {
      const data = JSON.parse(document.getElementById('step-detail-data').textContent);
      Object.assign(this, data);
    },

    startEdit(field, value) {
      this.drafts[field] = value ?? '';
      this.errors[field] = '';
      this.editing[field] = true;
    },

    cancelEdit(field) {
      this.editing[field] = false;
      this.errors[field] = '';
    },

    async saveEdit(field) {
      const body = { [field]: this.drafts[field] };

      const resp = await fetch(`/workflows/${this.workflowId}/steps/${this.stepId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (resp.ok) {
        if (field === 'playbook') this.playbook = body.playbook;
        this.editing[field] = false;
      }
    },

    async navigateStep(targetStepId) {
      const container = document.getElementById('step-detail');
      const resp = await fetch(`/workflows/${this.workflowId}/steps/${targetStepId}`, {
        headers: { 'X-Partial': '1' },
      });
      const html = await resp.text();
      container.innerHTML = html;
      Alpine.initTree(container);
      history.replaceState(null, '', `/workflows/${this.workflowId}/steps/${targetStepId}`);
    },

    renderMarkdown(content) {
      return marked.parse(content || '');
    },
  };
}

function libraryView() {
  return {
    entries: [],
    modalOpen: false,
    newFormOpen: false,
    newForm: { name: '', description: '', playbook: '', error: '' },
    _prefillFromStep: null,

    init() {
      const data = JSON.parse(document.getElementById('library-data').textContent);
      this.entries = data.entries || [];


      // Pre-fill new form if ?new=1&from_step=N is in the URL
      const params = new URLSearchParams(window.location.search);
      if (params.get('new') === '1' && params.get('from_step')) {
        this._prefillFromStep = parseInt(params.get('from_step'));
        this.openNewForm();
      } else if (data.openEntryId) {
        // Deep-link: /library/{id} — open modal for that entry
        this.openEntry(data.openEntryId);
      }
    },

    async openNewForm() {
      this.newForm = { name: '', description: '', playbook: '', error: '' };
      if (this._prefillFromStep) {
        try {
          const resp = await fetch(`/library/prefill?from_step=${this._prefillFromStep}`);
          if (resp.ok) {
            const data = await resp.json();
            this.newForm.name = data.name || '';
            this.newForm.playbook = data.playbook || '';
          }
        } catch (_) {}
      }
      this.newFormOpen = true;
    },

    closeNewForm() {
      this.newFormOpen = false;
      this._prefillFromStep = null;
    },

    async saveNewEntry() {
      const name = this.newForm.name.trim();
      if (!name) return;
      const body = {
        name,
        description: this.newForm.description.trim(),
        playbook: this.newForm.playbook.trim(),
      };
      if (this._prefillFromStep) {
        body.from_step = this._prefillFromStep;
      }
      const resp = await fetch('/library', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (resp.ok) {
        const entry = await resp.json();
        this.entries = [...this.entries, entry].sort((a, b) => a.name.localeCompare(b.name));
        this.closeNewForm();
        this.openEntry(entry.id);
      } else {
        const err = await resp.json().catch(() => ({}));
        this.newForm.error = err.detail || 'Failed to save entry.';
      }
    },

    async openEntry(entryId) {
      this.modalOpen = true;
      await this.$nextTick();
      const container = document.getElementById('library-entry-detail');
      const resp = await fetch(`/library/${entryId}/detail`);
      const html = await resp.text();
      container.innerHTML = html;
      Alpine.initTree(container);
      history.replaceState(null, '', `/library/${entryId}`);
    },

    closeModal() {
      this.modalOpen = false;
      history.replaceState(null, '', '/library');
    },

    async deleteEntry(entryId) {
      if (!confirm('Delete this library entry? Steps that used it will keep their playbook — only the library link is removed.')) return;
      const resp = await fetch(`/library/${entryId}`, { method: 'DELETE' });
      if (resp.ok) {
        this.entries = this.entries.filter(e => e.id !== entryId);
        if (this.modalOpen) this.closeModal();
      }
    },

    async copyPlaybook(entry) {
      const text = entry.playbook || '';
      await navigator.clipboard.writeText(text);
      entry._copied = true;
      this.entries = this.entries.map(e => e.id === entry.id ? { ...e, _copied: true } : e);
      setTimeout(() => {
        this.entries = this.entries.map(e => e.id === entry.id ? { ...e, _copied: false } : e);
      }, 1500);
    },
  };
}

function libraryEntryDetail() {
  return {
    entry: null,
    usedBy: [],
    editing: { name: false, description: false, playbook: false },
    drafts:  { name: '',    description: '',    playbook: ''    },
    errors:  { name: '',    description: '',    playbook: ''    },

    init() {
      const data = JSON.parse(document.getElementById('library-entry-detail-data').textContent);
      this.entry = data.entry;
      this.usedBy = data.usedBy || [];
    },

    startEdit(field, value) {
      this.drafts[field] = value ?? '';
      this.errors[field] = '';
      this.editing[field] = true;
    },

    cancelEdit(field) {
      this.editing[field] = false;
      this.errors[field] = '';
    },

    async saveEdit(field) {
      const body = { [field]: this.drafts[field] };
      const resp = await fetch(`/library/${this.entry.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (resp.ok) {
        this.entry = { ...this.entry, [field]: this.drafts[field] };
        this.editing[field] = false;
        this.errors[field] = '';
        // Notify the parent libraryView to update its card list
        this.$dispatch('library-entry-updated', { id: this.entry.id, field, value: this.drafts[field] });
      } else {
        const err = await resp.json().catch(() => ({}));
        this.errors[field] = err.detail || 'Failed to save.';
      }
    },

    renderMarkdown(content) {
      return marked.parse(content || '');
    },

    deleteEntry(entryId) {
      this.$dispatch('delete-library-entry', { id: entryId });
    },
  };
}

function _conditionLabel(condition) {
  if (!condition) return '';
  const opMap = { eq: '=', neq: '≠', in: 'in', not_in: 'not in' };
  const op = opMap[condition.operator] || condition.operator;
  return `${condition.field} ${op} ${JSON.stringify(condition.value)}`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
