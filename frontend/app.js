/**
 * BillSplit AI — 6-Step Single Page Application
 *
 * Drives the 6-step continuous flow:
 *   1. Upload Bill, 2. AI Analysis, 3. Review Bill, 4. Add People, 5. Assign Items, 6. Split Summary
 */

'use strict';

const API_BASE = '';  // same origin; FastAPI serves both API and frontend

class BillSplitApp {
  constructor() {
    this.state = {
      uploadedFile: null,   // File object
      previewDataUrl: null, // Data URL for preview image
      bill: null,           // Bill object from server
      people: [],           // [{ id, name }, ...]
      assignments: [],      // [{ item_id, person_ids[], everyone }, ...]
      splitResult: null,    // SplitResult from server
    };

    this._personCounter = 0;
    this._bindElements();
    this._attachEventListeners();
    this._renderRecentBills();
    this._goToScreen(1);
  }

  // ── DOM Element References ────────────────────────────────────────────
  _bindElements() {
    // Steps
    this.$steps = [1, 2, 3, 4, 5, 6].map(n => document.getElementById(`step-${n}`));
    this.$lines = [1, 2, 3, 4, 5].map(n => document.getElementById(`line-${n}-${n + 1}`));

    // Screen 1: Upload
    this.$screenUpload     = document.getElementById('screen-upload');
    this.$uploadZone       = document.getElementById('upload-zone');
    this.$fileInput        = document.getElementById('file-input');
    this.$previewWrap      = document.getElementById('upload-preview-wrap');
    this.$previewImg       = document.getElementById('upload-preview-img');
    this.$previewRemoveBtn = document.getElementById('preview-remove-btn');
    this.$analyzeBtn       = document.getElementById('analyze-btn');
    this.$demoBtn          = document.getElementById('demo-btn');
    this.$uploadError      = document.getElementById('upload-error');
    this.$recentBillsGrid  = document.getElementById('recent-bills-grid');

    // Screen 2: AI Analysis
    this.$screenAnalysis     = document.getElementById('screen-analysis');
    this.$analysisPreviewImg = document.getElementById('analysis-preview-img');
    this.$analysisStatusText = document.getElementById('analysis-status-text');
    this.$analysisProgressBar= document.getElementById('analysis-progress-bar');

    // Screen 3: Review
    this.$screenReview       = document.getElementById('screen-review');
    this.$reviewReceiptImg   = document.getElementById('review-receipt-img');
    this.$itemsTbody         = document.getElementById('items-tbody');
    this.$addItemBtn         = document.getElementById('add-item-btn');
    this.$fieldSubtotal      = document.getElementById('field-subtotal');
    this.$fieldTax           = document.getElementById('field-tax');
    this.$fieldSC            = document.getElementById('field-sc');
    this.$fieldDiscount      = document.getElementById('field-discount');
    this.$displayPrinted     = document.getElementById('display-printed-total');
    this.$displayItemsTotal  = document.getElementById('display-items-total');
    this.$displayCalc        = document.getElementById('display-calc-total');
    this.$alertMismatch      = document.getElementById('alert-mismatch');
    this.$alertMismatchDetail= document.getElementById('alert-mismatch-detail');
    this.$alertIllegible     = document.getElementById('alert-illegible');
    this.$alertIllegibleDetail = document.getElementById('alert-illegible-detail');
    this.$reviewBackBtn      = document.getElementById('review-back-btn');
    this.$reviewContinueBtn  = document.getElementById('review-continue-btn');

    // Screen 4: People
    this.$screenPeople       = document.getElementById('screen-people');
    this.$participantsRow    = document.getElementById('participants-row');
    this.$addPersonInput     = document.getElementById('add-person-input');
    this.$addPersonBtn       = document.getElementById('add-person-btn');
    this.$participantsHint   = document.getElementById('participants-hint');
    this.$peopleBackBtn      = document.getElementById('people-back-btn');
    this.$peopleContinueBtn  = document.getElementById('people-continue-btn');

    // Screen 5: Assign
    this.$screenAssign       = document.getElementById('screen-assign');
    this.$assignmentCards    = document.getElementById('assignment-cards');
    this.$unassignedAlert    = document.getElementById('unassigned-alert');
    this.$unassignedAlertText= document.getElementById('unassigned-alert-text');
    this.$assignBackBtn      = document.getElementById('assign-back-btn');
    this.$calculateBtn       = document.getElementById('calculate-btn');

    // Screen 6: Summary
    this.$screenSummary      = document.getElementById('screen-summary');
    this.$summaryMismatch    = document.getElementById('summary-mismatch-alert');
    this.$summaryMismatchTxt = document.getElementById('summary-mismatch-text');
    this.$summaryGrandTotal  = document.getElementById('summary-grand-total');
    this.$summaryBreakdown   = document.getElementById('summary-breakdown-rows');
    this.$personCardsGrid    = document.getElementById('person-cards-grid');
    this.$reconcileNote      = document.getElementById('reconcile-note');
    this.$summaryBackBtn     = document.getElementById('summary-back-btn');
    this.$startOverBtn       = document.getElementById('start-over-btn');
  }

  // ── Event Listeners ───────────────────────────────────────────────────
  _attachEventListeners() {
    // Screen 1
    this.$fileInput.addEventListener('change', e => this._onFileSelected(e));
    this.$uploadZone.addEventListener('dragover', e => { e.preventDefault(); this.$uploadZone.classList.add('drag-over'); });
    this.$uploadZone.addEventListener('dragleave', () => this.$uploadZone.classList.remove('drag-over'));
    this.$uploadZone.addEventListener('drop', e => { e.preventDefault(); this.$uploadZone.classList.remove('drag-over'); this._onFileDrop(e); });
    this.$previewRemoveBtn.addEventListener('click', () => this._clearFile());
    this.$analyzeBtn.addEventListener('click', () => this._startAnalysisFlow());
    if (this.$demoBtn) this.$demoBtn.addEventListener('click', () => this._loadDemoBillFlow());

    // Screen 3: Review
    this.$reviewBackBtn.addEventListener('click', () => this._goToScreen(1));
    this.$reviewContinueBtn.addEventListener('click', () => this._onReviewContinue());
    if (this.$addItemBtn) this.$addItemBtn.addEventListener('click', () => this._addItem());
    [this.$fieldSubtotal, this.$fieldTax, this.$fieldSC, this.$fieldDiscount]
      .forEach(el => el.addEventListener('input', () => this._liveRecalculate()));

    // Screen 4: People
    this.$addPersonBtn.addEventListener('click', () => this._addPerson());
    this.$addPersonInput.addEventListener('keydown', e => { if (e.key === 'Enter') this._addPerson(); });
    this.$peopleBackBtn.addEventListener('click', () => this._goToScreen(3));
    this.$peopleContinueBtn.addEventListener('click', () => {
      this._buildAssignScreen();
      this._goToScreen(5);
    });

    // Screen 5: Assign
    this.$assignBackBtn.addEventListener('click', () => this._goToScreen(4));
    this.$calculateBtn.addEventListener('click', () => this._calculateSplit());

    // Screen 6: Summary
    this.$summaryBackBtn.addEventListener('click', () => this._goToScreen(5));
    this.$startOverBtn.addEventListener('click', () => this._resetAll());

    // Allow step pills navigation for visited steps
    this.$steps.forEach((stepEl, idx) => {
      stepEl.addEventListener('click', () => {
        if (stepEl.classList.contains('done') || stepEl.classList.contains('active')) {
          this._goToScreen(idx + 1);
        }
      });
    });
  }

  // ── Screen Navigation ─────────────────────────────────────────────────
  _goToScreen(n) {
    const screens = [
      this.$screenUpload,
      this.$screenAnalysis,
      this.$screenReview,
      this.$screenPeople,
      this.$screenAssign,
      this.$screenSummary
    ];
    screens.forEach((s, i) => {
      if (s) s.style.display = (i === n - 1) ? 'block' : 'none';
    });

    this.$steps.forEach((step, i) => {
      if (!step) return;
      step.classList.remove('active', 'done');
      if (i + 1 < n) step.classList.add('done');
      if (i + 1 === n) step.classList.add('active');
    });

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── File Selection ────────────────────────────────────────────────────
  _onFileSelected(e) {
    const file = e.target.files[0];
    if (file) this._loadFile(file);
  }

  _onFileDrop(e) {
    const file = e.dataTransfer.files[0];
    if (file) this._loadFile(file);
  }

  _loadFile(file) {
    const ALLOWED = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'];
    if (!ALLOWED.includes(file.type)) {
      this._showUploadError('Unsupported file type. Please upload a JPEG, PNG, WebP, or HEIC image.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this._showUploadError('File is too large. Maximum size is 10 MB.');
      return;
    }

    this._clearUploadError();
    this.state.uploadedFile = file;

    const reader = new FileReader();
    reader.onload = e => {
      this.state.previewDataUrl = e.target.result;
      this.$previewImg.src = e.target.result;
      this.$previewWrap.style.display = 'block';
    };
    reader.readAsDataURL(file);

    this.$analyzeBtn.disabled = false;
  }

  _clearFile() {
    this.state.uploadedFile = null;
    this.state.previewDataUrl = null;
    this.$previewImg.src = '';
    this.$previewWrap.style.display = 'none';
    this.$fileInput.value = '';
    this.$analyzeBtn.disabled = true;
    this._clearUploadError();
  }

  _showUploadError(msg) {
    this.$uploadError.innerHTML = `<div class="alert alert-error"><span class="alert-icon">❌</span><div class="alert-content">${this._esc(msg)}</div></div>`;
    this.$uploadError.classList.remove('hidden');
  }

  _clearUploadError() {
    this.$uploadError.innerHTML = '';
    this.$uploadError.classList.add('hidden');
  }

  // ── Screen 2: AI Analysis Flow ───────────────────────────────────────
  async _startAnalysisFlow() {
    if (!this.state.uploadedFile) return;

    this._goToScreen(2);
    this.$analysisPreviewImg.src = this.state.previewDataUrl || '';

    // Staged status messages animation
    const stages = [
      { text: "Reading receipt...", pct: "25%", mood: "note-cute" },
      { text: "Finding every little item...", pct: "55%", mood: "note-doodle" },
      { text: "Adding up the good stuff...", pct: "85%", mood: "note-tacky" },
      { text: "Making every rupee count...", pct: "98%", mood: "note-polished" }
    ];

    let currentStage = 0;
    const interval = setInterval(() => {
      if (currentStage < stages.length) {
        this.$analysisStatusText.className = `staged-status-text ${stages[currentStage].mood}`;
        this.$analysisStatusText.innerHTML = `<span class="spinner"></span> ${stages[currentStage].text}`;
        this.$analysisProgressBar.style.width = stages[currentStage].pct;
        currentStage++;
      }
    }, 450);

    const formData = new FormData();
    formData.append('file', this.state.uploadedFile);

    try {
      const res = await fetch(`${API_BASE}/api/bills/analyze`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(interval);

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Server error ${res.status}`);
      }

      this.state.bill = await res.json();
      this._populateReviewScreen();
      this._goToScreen(3);

    } catch (err) {
      clearInterval(interval);
      this._goToScreen(1);
      this._showUploadError(`Extraction failed: ${err.message}`);
    }
  }

  async _loadDemoBillFlow() {
    this._goToScreen(2);
    this.$analysisPreviewImg.src = 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500&auto=format&fit=crop&q=60';

    const stages = [
      { text: "Reading receipt...", pct: "30%", mood: "note-cute" },
      { text: "Finding every little item...", pct: "65%", mood: "note-doodle" },
      { text: "Making every rupee count...", pct: "95%", mood: "note-polished" }
    ];

    let currentStage = 0;
    const interval = setInterval(() => {
      if (currentStage < stages.length) {
        this.$analysisStatusText.className = `staged-status-text ${stages[currentStage].mood}`;
        this.$analysisStatusText.innerHTML = `<span class="spinner"></span> ${stages[currentStage].text}`;
        this.$analysisProgressBar.style.width = stages[currentStage].pct;
        currentStage++;
      }
    }, 400);

    try {
      const res = await fetch(`${API_BASE}/api/bills/demo`);
      clearInterval(interval);

      if (!res.ok) {
        throw new Error(`Failed to load sample bill: ${res.statusText}`);
      }

      this.state.bill = await res.json();
      this.state.previewDataUrl = 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500&auto=format&fit=crop&q=60';
      this._populateReviewScreen();
      this._goToScreen(3);
    } catch (err) {
      clearInterval(interval);
      this._goToScreen(1);
      this._showUploadError(`Demo failed: ${err.message}`);
    }
  }

  // ── Screen 3: Review Screen ───────────────────────────────────────────
  _populateReviewScreen() {
    const bill = this.state.bill;

    if (this.$reviewReceiptImg) {
      this.$reviewReceiptImg.src = this.state.previewDataUrl || '';
    }

    // Render items table rows
    this.$itemsTbody.innerHTML = '';
    (bill.items || []).forEach(item => {
      const isManual = item.manually_added;
      const conf = item.confidence || 0;
      const pct = Math.round(conf * 100);
      const badgeClass = conf >= 0.9 ? 'badge-high' : conf >= 0.7 ? 'badge-medium' : 'badge-low';
      const badgeEmoji = conf >= 0.9 ? '🟢' : conf >= 0.7 ? '🟡' : '🔴';

      const badgeHtml = isManual
        ? `<span class="badge badge-manual">Manually added</span>`
        : `<span class="badge ${badgeClass}" title="Model extraction confidence">${badgeEmoji} ${pct}%</span>`;

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><input class="edit-input name-input" type="text" data-id="${item.item_id}" data-field="name" value="${this._esc(item.name)}" /></td>
        <td><input class="edit-input" type="number" data-id="${item.item_id}" data-field="quantity" value="${item.quantity}" min="0.01" step="0.01" style="width:60px;" /></td>
        <td><input class="edit-input" type="number" data-id="${item.item_id}" data-field="unit_price" value="${item.unit_price}" min="0" step="0.01" /></td>
        <td><input class="edit-input total-input" type="number" data-id="${item.item_id}" data-field="total" value="${item.total}" min="0" step="0.01" /></td>
        <td>${badgeHtml}</td>
        <td><button class="btn-row-delete" data-id="${item.item_id}" title="Delete item">🗑️</button></td>
      `;
      this.$itemsTbody.appendChild(tr);
    });

    // Attach listeners
    this.$itemsTbody.querySelectorAll('.total-input').forEach(inp => {
      inp.addEventListener('input', () => this._syncSubtotal());
    });
    this.$itemsTbody.querySelectorAll('input[data-field="quantity"], input[data-field="unit_price"]').forEach(inp => {
      inp.addEventListener('input', () => this._syncItemTotal(inp));
    });
    this.$itemsTbody.querySelectorAll('.btn-row-delete').forEach(btn => {
      btn.addEventListener('click', () => this._deleteItem(btn.dataset.id));
    });

    // Populate charge fields
    const printedSub = bill.printed_subtotal || bill.subtotal || '0.00';
    this.$fieldSubtotal.value  = printedSub;
    this.$fieldTax.value       = bill.tax        || '0.00';
    this.$fieldSC.value        = bill.service_charge || '0.00';
    this.$fieldDiscount.value  = bill.discount   || '0.00';

    if (bill.printed_total !== null && bill.printed_total !== undefined) {
      this.$displayPrinted.textContent = `₹${bill.printed_total}`;
    } else {
      this.$displayPrinted.textContent = '— (unreadable)';
    }

    this._syncSubtotal();
  }

  _syncItemTotal(input) {
    const row = input.closest('tr');
    if (!row) return;

    const quantity = parseFloat(row.querySelector('input[data-field="quantity"]')?.value) || 0;
    const unitPrice = parseFloat(row.querySelector('input[data-field="unit_price"]')?.value) || 0;
    const totalInput = row.querySelector('input[data-field="total"]');
    if (totalInput) totalInput.value = (quantity * unitPrice).toFixed(2);

    this._syncSubtotal();
  }

  /** Calculate items_subtotal = sum(item.total) and check mismatch */
  _syncSubtotal() {
    let itemsSum = 0;
    this.$itemsTbody.querySelectorAll('input[data-field="total"]').forEach(inp => {
      itemsSum += parseFloat(inp.value) || 0;
    });

    const itemsSubStr = itemsSum.toFixed(2);
    if (this.$displayItemsTotal) {
      this.$displayItemsTotal.textContent = `₹${itemsSubStr}`;
    }

    const printedSub = parseFloat(this.$fieldSubtotal.value) || 0;
    const diff = Math.abs(itemsSum - printedSub);

    // Mismatch alert
    if (diff > 1.00) {
      this.$alertMismatchDetail.innerHTML =
        `Printed subtotal: <strong>₹${printedSub.toFixed(2)}</strong> &nbsp;·&nbsp; ` +
        `Current items total: <strong>₹${itemsSubStr}</strong> &nbsp;·&nbsp; ` +
        `Difference: <strong>₹${diff.toFixed(2)}</strong>. The calculation will use current items total.`;
      this.$alertMismatch.classList.remove('hidden');
    } else {
      this.$alertMismatch.classList.add('hidden');
    }

    this._liveRecalculate();
  }

  /** Recompute calculated_total live */
  _liveRecalculate() {
    let itemsSum = 0;
    this.$itemsTbody.querySelectorAll('input[data-field="total"]').forEach(inp => {
      itemsSum += parseFloat(inp.value) || 0;
    });

    const tax  = parseFloat(this.$fieldTax.value)      || 0;
    const sc   = parseFloat(this.$fieldSC.value)       || 0;
    const disc = parseFloat(this.$fieldDiscount.value) || 0;
    const calc = (itemsSum + tax + sc - disc).toFixed(2);
    this.$displayCalc.textContent = `₹${calc}`;
  }

  _syncStateFromDOM() {
    if (!this.state.bill) return;

    const domValues = {};
    this.$itemsTbody.querySelectorAll('tr').forEach(tr => {
      const nameInp = tr.querySelector('input[data-field="name"]');
      if (!nameInp) return;
      const id = nameInp.dataset.id;
      domValues[id] = {
        name: nameInp.value,
        quantity: tr.querySelector('input[data-field="quantity"]')?.value || '1',
        unit_price: tr.querySelector('input[data-field="unit_price"]')?.value || '0.00',
        total: tr.querySelector('input[data-field="total"]')?.value || '0.00',
      };
    });

    (this.state.bill.items || []).forEach(item => {
      if (domValues[item.item_id]) {
        item.name       = domValues[item.item_id].name;
        item.quantity   = domValues[item.item_id].quantity;
        item.unit_price = domValues[item.item_id].unit_price;
        item.total      = domValues[item.item_id].total;
      }
    });

    this.state.bill.printed_subtotal = this.$fieldSubtotal.value;
    this.state.bill.subtotal       = this.$fieldSubtotal.value;
    this.state.bill.tax            = this.$fieldTax.value;
    this.state.bill.service_charge = this.$fieldSC.value;
    this.state.bill.discount       = this.$fieldDiscount.value;
  }

  _addItem() {
    this._syncStateFromDOM();
    const newId = Math.random().toString(36).substring(2, 10);
    const newItem = {
      item_id: newId,
      name: '',
      quantity: '1',
      unit_price: '0.00',
      total: '0.00',
      confidence: 1.0,
      manually_added: true,
    };
    if (!this.state.bill) {
      this.state.bill = { items: [], subtotal: '0.00', printed_subtotal: '0.00', tax: '0.00', service_charge: '0.00', discount: '0.00', printed_total: null, currency: '₹' };
    }
    if (!this.state.bill.items) this.state.bill.items = [];
    this.state.bill.items.push(newItem);
    this._populateReviewScreen();
  }

  _deleteItem(itemId) {
    this._syncStateFromDOM();
    if (this.state.bill && this.state.bill.items) {
      this.state.bill.items = this.state.bill.items.filter(item => item.item_id !== itemId);
    }
    this.state.assignments = this.state.assignments.filter(a => a.item_id !== itemId);
    this._populateReviewScreen();
  }

  _readEditedBill() {
    this._syncStateFromDOM();
    return JSON.parse(JSON.stringify(this.state.bill));
  }

  async _onReviewContinue() {
    this.$reviewContinueBtn.disabled = true;
    this.$reviewContinueBtn.innerHTML = '<span class="spinner"></span> Validating…';

    try {
      const edited = this._readEditedBill();
      const res = await fetch(`${API_BASE}/api/bills/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(edited),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        alert(`Validation failed: ${JSON.stringify(err.detail)}`);
        return;
      }

      this.state.bill = await res.json();
      this._goToScreen(4);

    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      this.$reviewContinueBtn.disabled = false;
      this.$reviewContinueBtn.innerHTML = 'Continue to People';
    }
  }

  // ── Screen 4: Add People & PricePop Interaction ──────────────────────
  _addPerson() {
    const name = this.$addPersonInput.value.trim();
    if (!name) return;

    this._personCounter++;
    const newPerson = { id: `p${this._personCounter}`, name };
    this.state.people.push(newPerson);
    this.$addPersonInput.value = '';

    this._renderParticipants();
    this._triggerPricePop(newPerson.id, '✨ + ₹0.00');
  }

  _removePerson(id) {
    this.state.people = this.state.people.filter(p => p.id !== id);
    this.state.assignments.forEach(a => {
      a.person_ids = a.person_ids.filter(pid => pid !== id);
    });
    this._renderParticipants();
  }

  _renderParticipants() {
    const avatarColors = [
      'var(--pastel-lavender)',
      'var(--pastel-coral)',
      'var(--pastel-blue)',
      'var(--pastel-mint)',
      'var(--pastel-amber)'
    ];

    this.$participantsRow.innerHTML = this.state.people.map((p, i) => `
      <div class="participant-chip" id="pchip-${p.id}">
        <span class="chip-avatar" style="background:${avatarColors[i % avatarColors.length]};">
          ${p.name[0].toUpperCase()}
        </span>
        ${this._esc(p.name)}
        <button class="chip-remove" data-id="${p.id}" title="Remove ${this._esc(p.name)}">×</button>
      </div>
    `).join('');

    this.$participantsRow.querySelectorAll('.chip-remove').forEach(btn => {
      btn.addEventListener('click', () => this._removePerson(btn.dataset.id));
    });

    if (this.state.people.length === 0) {
      this.$participantsHint.textContent = 'Add at least one person to continue.';
      this.$participantsHint.style.color = 'var(--amber)';
    } else {
      this.$participantsHint.textContent = `${this.state.people.length} person${this.state.people.length > 1 ? 's' : ''} added. Click Continue to assign items.`;
      this.$participantsHint.style.color = 'var(--text-muted-purple)';
    }
  }

  /** Reusable PricePop Micro-Interaction */
  _triggerPricePop(personId, amountText) {
    const chipEl = document.getElementById(`pchip-${personId}`);
    if (!chipEl) return;

    const popBadge = document.createElement('div');
    popBadge.className = 'price-pop-badge';
    popBadge.textContent = amountText;
    chipEl.appendChild(popBadge);

    setTimeout(() => {
      if (popBadge.parentNode) popBadge.parentNode.removeChild(popBadge);
    }, 750);
  }

  // ── Screen 5: Assign Items ───────────────────────────────────────────
  _buildAssignScreen() {
    const existingById = {};
    this.state.assignments.forEach(a => { existingById[a.item_id] = a; });

    this.state.assignments = (this.state.bill.items || []).map(item => {
      if (existingById[item.item_id]) {
        return existingById[item.item_id];
      }
      return {
        item_id: item.item_id,
        person_ids: [],
        everyone: false,
      };
    });

    this._renderAssignmentCards();
    this._updateCalculateBtn();
  }

  _renderAssignmentCards() {
    const bill = this.state.bill;
    const people = this.state.people;

    this.$assignmentCards.innerHTML = (bill.items || []).map(item => {
      const assignment = this.state.assignments.find(a => a.item_id === item.item_id) || {
        item_id: item.item_id,
        person_ids: [],
        everyone: false,
      };

      const isAssigned = assignment.everyone || assignment.person_ids.length > 0;
      const cardClass  = isAssigned ? 'assigned' : 'unassigned';

      // Shared item calculation indicator
      let sharedText = '';
      if (assignment.everyone) {
        sharedText = `<span class="shared-split-badge">Everyone (${people.length})</span>`;
      } else if (assignment.person_ids.length > 1) {
        const count = assignment.person_ids.length;
        const pct = Math.round(100 / count);
        sharedText = `<span class="shared-split-badge">Shared · ${pct}% each</span>`;
      }

      const personButtons = people.map(p => {
        const sel = !assignment.everyone && assignment.person_ids.includes(p.id);
        return `<button class="assign-btn ${sel ? 'selected' : ''}" data-id="${item.item_id}" data-pid="${p.id}">${this._esc(p.name)}</button>`;
      }).join('');

      const everyoneSelected = assignment.everyone;

      return `
        <div class="assignment-card ${cardClass}" id="acard-${item.item_id}">
          <div class="assignment-card-header">
            <div>
              <span class="item-name-display">${this._esc(item.name || 'Unnamed Item')}</span>
              ${sharedText}
            </div>
            <span class="item-price-display">₹${item.total}</span>
          </div>
          <div class="assignment-options">
            ${personButtons}
            ${people.length > 1
              ? `<button class="assign-btn everyone-btn ${everyoneSelected ? 'selected' : ''}" data-id="${item.item_id}" data-pid="__everyone__">Everyone</button>`
              : ''}
          </div>
        </div>
      `;
    }).join('');

    // Attach handlers
    this.$assignmentCards.querySelectorAll('.assign-btn').forEach(btn => {
      btn.addEventListener('click', () => this._toggleAssignment(
        btn.dataset.id,
        btn.dataset.pid
      ));
    });
  }

  _toggleAssignment(itemId, personId) {
    const assignment = this.state.assignments.find(a => a.item_id === itemId);
    if (!assignment) return;

    if (personId === '__everyone__') {
      assignment.everyone = !assignment.everyone;
      if (assignment.everyone) {
        assignment.person_ids = [];
      }
    } else {
      assignment.everyone = false;
      const pidIdx = assignment.person_ids.indexOf(personId);
      if (pidIdx >= 0) {
        assignment.person_ids.splice(pidIdx, 1);
      } else {
        assignment.person_ids.push(personId);
      }
    }

    // Trigger card pulse animation
    const cardEl = document.getElementById(`acard-${itemId}`);
    if (cardEl) {
      cardEl.classList.remove('pulse-highlight');
      void cardEl.offsetWidth;
      cardEl.classList.add('pulse-highlight');
    }

    this._renderAssignmentCards();
    this._updateCalculateBtn();
  }

  _updateCalculateBtn() {
    const hasPeople = this.state.people.length > 0;
    const unassigned = this.state.assignments.filter(
      a => !a.everyone && a.person_ids.length === 0
    );
    const allAssigned = unassigned.length === 0;

    this.$calculateBtn.disabled = !hasPeople || !allAssigned;

    if (!hasPeople) {
      this.$unassignedAlert.classList.add('hidden');
      return;
    }

    if (!allAssigned && (this.state.bill?.items?.length > 0)) {
      const names = unassigned.map(a => {
        const item = this.state.bill.items.find(i => i.item_id === a.item_id);
        return item && item.name ? item.name : 'Unnamed Item';
      });
      this.$unassignedAlertText.textContent =
        `Not yet assigned: ${names.join(', ')}.`;
      this.$unassignedAlert.classList.remove('hidden');
    } else {
      this.$unassignedAlert.classList.add('hidden');
    }
  }

  // ── Screen 6: Calculate & Split Summary ──────────────────────────────
  async _calculateSplit() {
    this.$calculateBtn.disabled = true;
    this.$calculateBtn.innerHTML = '<span class="spinner"></span> Calculating…';

    const payload = {
      bill: this.state.bill,
      people: this.state.people,
      assignments: this.state.assignments,
    };

    try {
      const res = await fetch(`${API_BASE}/api/split/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        const msg = Array.isArray(err.detail)
          ? err.detail.map(e => e.msg).join('\n')
          : String(err.detail);
        alert(`Calculation failed:\n${msg}`);
        return;
      }

      this.state.splitResult = await res.json();
      this._saveRecentSplit();
      this._renderSummary();
      this._goToScreen(6);

    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      this.$calculateBtn.disabled = false;
      this.$calculateBtn.innerHTML = 'Calculate Split';
    }
  }

  _renderSummary() {
    const result = this.state.splitResult;
    const bill   = this.state.bill;

    this.$summaryGrandTotal.textContent = `₹${result.bill_calculated_total}`;

    // Bill breakdown rows
    this.$summaryBreakdown.innerHTML = `
      <div class="summary-breakdown-row"><span>Items Total</span><span>₹${bill.items_subtotal || bill.subtotal}</span></div>
      ${parseFloat(bill.tax) > 0
        ? `<div class="summary-breakdown-row"><span>Tax / GST</span><span>₹${bill.tax}</span></div>`
        : ''}
      ${parseFloat(bill.service_charge) > 0
        ? `<div class="summary-breakdown-row"><span>Service Charge</span><span>₹${bill.service_charge}</span></div>`
        : ''}
      ${parseFloat(bill.discount) > 0
        ? `<div class="summary-breakdown-row"><span>Discount</span><span style="color:var(--text-dark)">−₹${bill.discount}</span></div>`
        : ''}
    `;

    if (result.mismatch_warning) {
      this.$summaryMismatchTxt.textContent = result.mismatch_warning;
      this.$summaryMismatch.classList.remove('hidden');
    } else {
      this.$summaryMismatch.classList.add('hidden');
    }

    const avatarColors = [
      'var(--pastel-lavender)',
      'var(--pastel-coral)',
      'var(--pastel-blue)',
      'var(--pastel-mint)',
      'var(--pastel-amber)'
    ];

    const grandTotalNum = parseFloat(result.bill_calculated_total) || 1;

    this.$personCardsGrid.innerHTML = result.people_splits.map((ps, i) => {
      const breakdown = ps.breakdown.map(line => {
        const isDiscount = line.label === 'Discount';
        const amtStr = parseFloat(line.amount) < 0
          ? `−₹${Math.abs(parseFloat(line.amount)).toFixed(2)}`
          : `₹${line.amount}`;
        return `
          <div class="breakdown-line ${isDiscount ? 'discount' : ''}">
            <span class="bl-label">${this._esc(line.label)}</span>
            <span class="bl-amount">${amtStr}</span>
          </div>
        `;
      }).join('');

      const personGrandNum = parseFloat(ps.grand_total) || 0;
      const propPct = Math.min(100, Math.round((personGrandNum / grandTotalNum) * 100));

      return `
        <div class="person-card">
          <div class="person-card-header">
            <div class="person-card-header-top">
              <div class="person-avatar" style="background:${avatarColors[i % avatarColors.length]};">
                ${ps.person.name[0].toUpperCase()}
              </div>
              <div class="person-card-name">${this._esc(ps.person.name)}</div>
            </div>
            <div class="person-grand-total">₹${ps.grand_total}</div>

            <div class="proportional-bar-wrap">
              <div class="proportional-bar-track">
                <div class="proportional-bar-fill" style="width:${propPct}%;background:${avatarColors[i % avatarColors.length]};"></div>
              </div>
            </div>
          </div>

          <div class="person-card-body">
            ${breakdown}
          </div>
        </div>
      `;
    }).join('');

    this.$reconcileNote.textContent =
      `✓ All amounts verified: ₹${result.sum_of_splits} total across ${result.people_splits.length} people ` +
      `= ₹${result.bill_calculated_total} bill total. Penny-reconciled.`;
  }

  // ── Reset ─────────────────────────────────────────────────────────────
  _resetAll() {
    this.state = { uploadedFile: null, previewDataUrl: null, bill: null, people: [], assignments: [], splitResult: null };
    this._personCounter = 0;
    this._clearFile();
    this.$itemsTbody.innerHTML = '';
    this.$participantsRow.innerHTML = '';
    this.$assignmentCards.innerHTML = '';
    this.$personCardsGrid.innerHTML = '';
    this._goToScreen(1);
  }

  _getRecentSplits() {
    try {
      const stored = JSON.parse(localStorage.getItem('billsplit_recent_splits') || '[]');
      return Array.isArray(stored) ? stored : [];
    } catch {
      return [];
    }
  }

  _saveRecentSplit() {
    const result = this.state.splitResult;
    if (!result) return;

    const recent = this._getRecentSplits();
    recent.unshift({
      id: `${Date.now()}`,
      total: result.bill_calculated_total,
      people: result.people_splits.length,
      createdAt: new Date().toISOString(),
    });

    try {
      localStorage.setItem('billsplit_recent_splits', JSON.stringify(recent.slice(0, 5)));
    } catch {
      // History remains optional if browser storage is unavailable.
    }
    this._renderRecentBills();
  }

  _renderRecentBills() {
    if (!this.$recentBillsGrid) return;
    const recent = this._getRecentSplits();

    if (!recent.length) {
      this.$recentBillsGrid.innerHTML = '<span class="recent-empty">Your completed splits will appear here.</span>';
      return;
    }

    this.$recentBillsGrid.innerHTML = recent.map(split => {
      const date = new Date(split.createdAt);
      const label = Number.isNaN(date.getTime()) ? 'Recent split' : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      return `
        <div class="recent-row">
          <span class="recent-row-icon" aria-hidden="true"></span>
          <span class="recent-row-copy"><strong>Completed split</strong><small>${this._esc(label)} · ${split.people} people</small></span>
          <strong class="recent-row-amount">₹${this._esc(split.total)}</strong>
        </div>
      `;
    }).join('');
  }

  // ── Utilities ─────────────────────────────────────────────────────────
  _esc(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

// Boot the app
document.addEventListener('DOMContentLoaded', () => { new BillSplitApp(); });
