document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const selectDemoBtn = document.getElementById('selectDemoBtn');
  const demoBtn = document.getElementById('demoBtn');
  const demoModal = document.getElementById('demoModal');
  const demoModalContent = document.getElementById('demoModalContent');
  const closeDemoModalBtn = document.getElementById('closeDemoModalBtn');
  const demoGrid = document.getElementById('demoGrid');
  const emptyState = document.getElementById('emptyState');
  const loadingState = document.getElementById('loadingState');
  const loadingText = document.getElementById('loadingText');
  const canvasContainer = document.getElementById('canvasContainer');
  const originalImage = document.getElementById('originalImage');
  const overlayCanvas = document.getElementById('overlayCanvas');
  const ctx = overlayCanvas.getContext('2d');

  const imgResLabel = document.getElementById('imgRes');
  const modelStatus = document.getElementById('modelStatus');
  const statusHint = document.getElementById('statusHint');
  const confidenceSlider = document.getElementById('confidenceSlider');
  const confidenceValue = document.getElementById('confidenceValue');
  const detectBtn = document.getElementById('detectBtn');
  const bandCount = document.getElementById('bandCount');
  const rowCount = document.getElementById('rowCount');

  // Densitometry panel elements
  const profileSubtitle = document.getElementById('profileSubtitle');
  const selectedRowBadge = document.getElementById('selectedRowBadge');
  const profileContainer = document.getElementById('profileContainer');
  const profileEmptyState = document.getElementById('profileEmptyState');
  const profileCanvas = document.getElementById('profileCanvas');
  const profileCtx = profileCanvas ? profileCanvas.getContext('2d') : null;
  const stripContainer = document.getElementById('stripContainer');
  const stripEmptyState = document.getElementById('stripEmptyState');
  const stripCanvas = document.getElementById('stripCanvas');
  const stripCtx = stripCanvas ? stripCanvas.getContext('2d') : null;

  // Analysis panel elements
  const analysisPanel = document.getElementById('analysisPanel');
  const selectedRowLabel = document.getElementById('selectedRowLabel');
  const bandTableBody = document.getElementById('bandTableBody');
  const exportBtn = document.getElementById('exportBtn');

  // State
  let currentFilename = null;
  let detectionResult = null;
  let selectedRowId = null;
  let analysisResult = null;
  let isImageLoaded = false;

  // Profile drawing margins (shared with strip for alignment)
  const PROFILE_MARGIN_LEFT = 50;
  const PROFILE_MARGIN_RIGHT = 20;

  // --- Initialize ---

  checkModelStatus();
  loadInitialImage();

  confidenceSlider.addEventListener('input', () => {
    confidenceValue.textContent = (confidenceSlider.value / 100).toFixed(2);
  });

  // --- Model Status ---

  async function checkModelStatus() {
    try {
      const res = await fetch('/model-info');
      const info = await res.json();
      if (info.initialized) {
        modelStatus.textContent = `Model: ${info.model_type} (${info.device})`;
        modelStatus.classList.remove('text-ink-700/60');
        modelStatus.classList.add('text-green-600');
      } else {
        modelStatus.textContent = 'Model not loaded';
        modelStatus.classList.add('text-red-500');
      }
    } catch (e) {
      modelStatus.textContent = 'Model status unknown';
    }
  }

  // --- UI Helpers ---

  function setLoading(isLoading, text = 'Loading...') {
    if (isLoading) {
      loadingState.classList.remove('hidden');
      loadingText.textContent = text;
      emptyState.classList.add('hidden');
    } else {
      loadingState.classList.add('hidden');
    }
  }

  function showImage() {
    emptyState.classList.add('hidden');
    canvasContainer.classList.remove('hidden');
  }

  function loadInitialImage() {
    emptyState.classList.add('hidden');
    canvasContainer.classList.remove('hidden');
    originalImage.src = '/static/initial.png';
    currentFilename = 'initial.png';
    originalImage.onload = () => {
      imgResLabel.textContent = `${originalImage.naturalWidth} x ${originalImage.naturalHeight}`;
      isImageLoaded = true;
      detectBtn.disabled = false;
      statusHint.textContent = 'Click "Detect Bands" to analyze';
      resizeOverlay();
    };
  }

  // --- Overlay Drawing ---

  function resizeOverlay() {
    if (!originalImage.naturalWidth) return;
    const rect = originalImage.getBoundingClientRect();
    overlayCanvas.width = rect.width;
    overlayCanvas.height = rect.height;
  }

  function drawDetections() {
    if (!detectionResult || !detectionResult.rows) return;

    resizeOverlay();
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    const rect = originalImage.getBoundingClientRect();
    const scaleX = rect.width / originalImage.naturalWidth;
    const scaleY = rect.height / originalImage.naturalHeight;

    detectionResult.rows.forEach((row, rowIdx) => {
      const isSelected = rowIdx === selectedRowId;

      // Draw row bounding box
      const rowBbox = row.bbox;
      ctx.strokeStyle = isSelected ? '#22c55e' : '#6366f1';
      ctx.lineWidth = isSelected ? 3 : 1;
      ctx.setLineDash(isSelected ? [] : [4, 4]);
      ctx.strokeRect(
        rowBbox.x1 * scaleX,
        rowBbox.y1 * scaleY,
        (rowBbox.x2 - rowBbox.x1) * scaleX,
        (rowBbox.y2 - rowBbox.y1) * scaleY
      );

      // Draw individual bands
      row.bands.forEach((band, bandIdx) => {
        const bbox = band.bbox;
        const x = bbox.x1 * scaleX;
        const y = bbox.y1 * scaleY;
        const w = (bbox.x2 - bbox.x1) * scaleX;
        const h = (bbox.y2 - bbox.y1) * scaleY;

        ctx.strokeStyle = isSelected ? '#22c55e' : '#a5b4fc';
        ctx.lineWidth = isSelected ? 2 : 1;
        ctx.setLineDash([]);
        ctx.strokeRect(x, y, w, h);

        if (isSelected) {
          ctx.fillStyle = '#22c55e';
          ctx.font = 'bold 12px system-ui';
          ctx.fillText(`${bandIdx + 1}`, x + 3, y - 4);
        }

        ctx.fillStyle = isSelected ? '#22c55e' : '#6366f1';
        ctx.font = '10px system-ui';
        const confText = (band.confidence * 100).toFixed(0) + '%';
        ctx.fillText(confText, x + w - ctx.measureText(confText).width - 2, y + h - 3);
      });

      // Row label
      ctx.fillStyle = isSelected ? '#22c55e' : '#6366f1';
      ctx.font = 'bold 14px system-ui';
      ctx.fillText(`Row ${rowIdx + 1}`, rowBbox.x1 * scaleX, rowBbox.y1 * scaleY - 8);
    });
  }

  window.addEventListener('resize', () => {
    setTimeout(() => {
      resizeOverlay();
      drawDetections();
      if (selectedRowId !== null && analysisResult) {
        drawProfile();
        drawRowStrip();
      }
    }, 100);
  });

  // --- Click to Select Row ---

  overlayCanvas.addEventListener('click', (e) => {
    if (!detectionResult || !detectionResult.rows.length) return;

    const rect = originalImage.getBoundingClientRect();
    const canvasRect = overlayCanvas.getBoundingClientRect();

    // Get click position relative to image
    const clickX = (e.clientX - canvasRect.left) / rect.width * originalImage.naturalWidth;
    const clickY = (e.clientY - canvasRect.top) / rect.height * originalImage.naturalHeight;

    // Find which row was clicked
    const clickedRowIdx = getClickedRow(clickX, clickY);
    if (clickedRowIdx !== null) {
      selectRow(clickedRowIdx);
    }
  });

  function getClickedRow(x, y) {
    if (!detectionResult || !detectionResult.rows) return null;

    for (let i = 0; i < detectionResult.rows.length; i++) {
      const row = detectionResult.rows[i];
      const bbox = row.bbox;
      if (x >= bbox.x1 && x <= bbox.x2 && y >= bbox.y1 && y <= bbox.y2) {
        return i;
      }
    }
    return null;
  }

  // --- Detection ---

  async function detectBands() {
    if (!currentFilename) return;

    setLoading(true, 'Detecting bands...');
    detectBtn.disabled = true;

    // Reset state
    selectedRowId = null;
    analysisResult = null;
    hideAnalysisUI();

    try {
      const confidence = confidenceSlider.value / 100;
      const res = await fetch('/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: currentFilename, confidence })
      });

      if (!res.ok) throw new Error('Detection failed');

      detectionResult = await res.json();

      bandCount.textContent = detectionResult.total_bands;
      rowCount.textContent = detectionResult.total_rows;

      if (detectionResult.total_rows > 0) {
        statusHint.textContent = `Detected ${detectionResult.total_bands} bands in ${detectionResult.total_rows} rows. Click a row to analyze.`;
        drawDetections();
        // Auto-select first row
        setLoading(false);
        selectRow(0);
      } else {
        statusHint.textContent = 'No bands detected. Try lowering confidence threshold.';
        drawDetections();
        setLoading(false);
      }

      detectBtn.disabled = false;

    } catch (e) {
      console.error(e);
      alert('Detection failed: ' + e.message);
      setLoading(false);
      detectBtn.disabled = false;
    }
  }

  detectBtn.addEventListener('click', detectBands);

  // --- Row Selection ---

  async function selectRow(rowId) {
    selectedRowId = rowId;
    drawDetections();
    await analyzeRow(rowId);
  }

  async function analyzeRow(rowId) {
    if (!currentFilename) return;

    setLoading(true, 'Analyzing row...');

    try {
      const res = await fetch('/analyze-row', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: currentFilename, row_id: rowId })
      });

      if (!res.ok) throw new Error('Analysis failed');

      analysisResult = await res.json();

      // Update UI
      showAnalysisUI(rowId);
      populateBandTable();
      drawProfile();
      drawRowStrip();

      setLoading(false);
      statusHint.textContent = `Analyzing Row ${rowId + 1}. Click another row to switch.`;

    } catch (e) {
      console.error(e);
      alert('Analysis failed: ' + e.message);
      setLoading(false);
    }
  }

  function showAnalysisUI(rowId) {
    // Densitometry panel
    profileSubtitle.textContent = `Showing Row ${rowId + 1} profile`;
    selectedRowBadge.textContent = `Row ${rowId + 1}`;
    selectedRowBadge.classList.remove('hidden');
    profileEmptyState.classList.add('hidden');
    profileCanvas.classList.remove('hidden');
    stripEmptyState.classList.add('hidden');
    stripCanvas.classList.remove('hidden');

    // Analysis panel with fade-in animation
    analysisPanel.classList.remove('hidden');
    analysisPanel.classList.add('fade-in');
    selectedRowLabel.textContent = `Row ${rowId + 1}`;

    // Add slide-up animation to profile area
    profileCanvas.classList.add('slide-up');
    stripCanvas.classList.add('slide-up');

    // Remove animation classes after they complete (for re-triggering)
    setTimeout(() => {
      analysisPanel.classList.remove('fade-in');
      profileCanvas.classList.remove('slide-up');
      stripCanvas.classList.remove('slide-up');
    }, 300);
  }

  function hideAnalysisUI() {
    profileSubtitle.textContent = 'Click a row on the image to analyze';
    selectedRowBadge.classList.add('hidden');
    profileEmptyState.classList.remove('hidden');
    profileCanvas.classList.add('hidden');
    stripEmptyState.classList.remove('hidden');
    stripCanvas.classList.add('hidden');
    analysisPanel.classList.add('hidden');
  }

  function populateBandTable() {
    if (!analysisResult || !analysisResult.bands) return;

    bandTableBody.innerHTML = '';

    analysisResult.bands.forEach((band, idx) => {
      const intensity = band.intensity;
      const relPercent = (intensity.relative * 100).toFixed(1);

      const tr = document.createElement('tr');
      tr.className = 'bg-white hover:bg-slate-50';
      tr.innerHTML = `
        <td class="px-4 py-2.5 font-medium text-slate-800">Band ${idx + 1}</td>
        <td class="px-4 py-2.5 text-right text-slate-600 font-mono">${intensity.mean.toFixed(1)}</td>
        <td class="px-4 py-2.5 text-right text-slate-600 font-mono">${intensity.integrated_density.toFixed(0)}</td>
        <td class="px-4 py-2.5 text-right text-slate-600 font-mono">${intensity.background_corrected.toFixed(0)}</td>
        <td class="px-4 py-2.5 text-right">
          <div class="flex items-center justify-end gap-2">
            <div class="w-20 bg-slate-200 rounded-full h-2">
              <div class="bg-green-500 h-2 rounded-full" style="width: ${relPercent}%"></div>
            </div>
            <span class="text-slate-800 font-medium font-mono w-14 text-right">${relPercent}%</span>
          </div>
        </td>
      `;
      bandTableBody.appendChild(tr);
    });
  }

  // --- Profile Graph ---

  function drawProfile() {
    if (!profileCanvas || !profileCtx || !analysisResult || !analysisResult.profile) return;

    const profile = analysisResult.profile;
    const values = profile.values;
    const stats = profile.stats;

    if (!values || values.length === 0) return;

    const parent = profileContainer;
    const dpr = window.devicePixelRatio || 1;
    const displayW = parent.clientWidth - 24; // padding
    const displayH = parent.clientHeight - 24;

    profileCanvas.width = displayW * dpr;
    profileCanvas.height = displayH * dpr;
    profileCanvas.style.width = displayW + 'px';
    profileCanvas.style.height = displayH + 'px';

    profileCtx.setTransform(1, 0, 0, 1, 0, 0);
    profileCtx.scale(dpr, dpr);

    const marginTop = 20;
    const marginBottom = 30;
    const graphW = displayW - PROFILE_MARGIN_LEFT - PROFILE_MARGIN_RIGHT;
    const graphH = displayH - marginTop - marginBottom;

    // Background
    profileCtx.fillStyle = '#ffffff';
    profileCtx.fillRect(0, 0, displayW, displayH);

    // Grid
    profileCtx.strokeStyle = '#e2e8f0';
    profileCtx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = marginTop + (i / 4) * graphH;
      profileCtx.beginPath();
      profileCtx.moveTo(PROFILE_MARGIN_LEFT, y);
      profileCtx.lineTo(PROFILE_MARGIN_LEFT + graphW, y);
      profileCtx.stroke();
    }

    // Profile line
    const minVal = stats.min;
    const maxVal = stats.max;
    const range = maxVal - minVal || 1;

    profileCtx.beginPath();
    profileCtx.strokeStyle = '#2a2622'; // ink-800
    profileCtx.lineWidth = 2;

    for (let i = 0; i < values.length; i++) {
      const x = PROFILE_MARGIN_LEFT + (i / Math.max(values.length - 1, 1)) * graphW;
      const normalizedVal = (values[i] - minVal) / range;
      const y = marginTop + graphH * (1 - normalizedVal);

      if (i === 0) profileCtx.moveTo(x, y);
      else profileCtx.lineTo(x, y);
    }
    profileCtx.stroke();

    // Fill under curve
    profileCtx.lineTo(PROFILE_MARGIN_LEFT + graphW, marginTop + graphH);
    profileCtx.lineTo(PROFILE_MARGIN_LEFT, marginTop + graphH);
    profileCtx.closePath();
    const gradient = profileCtx.createLinearGradient(0, marginTop, 0, marginTop + graphH);
    gradient.addColorStop(0, 'rgba(42, 38, 34, 0.25)'); // ink with opacity
    gradient.addColorStop(1, 'rgba(42, 38, 34, 0.03)');
    profileCtx.fillStyle = gradient;
    profileCtx.fill();

    // Axes
    profileCtx.strokeStyle = '#94a3b8';
    profileCtx.lineWidth = 1;
    profileCtx.beginPath();
    profileCtx.moveTo(PROFILE_MARGIN_LEFT, marginTop);
    profileCtx.lineTo(PROFILE_MARGIN_LEFT, marginTop + graphH);
    profileCtx.lineTo(PROFILE_MARGIN_LEFT + graphW, marginTop + graphH);
    profileCtx.stroke();

    // Labels
    profileCtx.fillStyle = '#3d3833'; // ink-700
    profileCtx.font = '11px system-ui';
    profileCtx.textAlign = 'right';
    profileCtx.fillText(maxVal.toFixed(0), PROFILE_MARGIN_LEFT - 5, marginTop + 10);
    profileCtx.fillText(minVal.toFixed(0), PROFILE_MARGIN_LEFT - 5, marginTop + graphH);

    profileCtx.textAlign = 'center';
    profileCtx.fillText('Position (px)', PROFILE_MARGIN_LEFT + graphW / 2, marginTop + graphH + 25);

    profileCtx.save();
    profileCtx.translate(12, marginTop + graphH / 2);
    profileCtx.rotate(-Math.PI / 2);
    profileCtx.textAlign = 'center';
    profileCtx.fillText('Intensity', 0, 0);
    profileCtx.restore();

    // --- Peak Annotations ---
    // Draw band markers on profile aligned with detected bands
    if (detectionResult && selectedRowId !== null) {
      const row = detectionResult.rows[selectedRowId];
      if (row && row.bands && row.bands.length > 0) {
        const rowBbox = row.bbox;
        const rowWidth = rowBbox.x2 - rowBbox.x1;

        row.bands.forEach((band, idx) => {
          // Calculate band X position relative to profile graph
          const bandRelX = (band.center.x - rowBbox.x1) / rowWidth;
          const markerX = PROFILE_MARGIN_LEFT + bandRelX * graphW;

          // Dashed vertical line
          profileCtx.strokeStyle = '#22c55e';
          profileCtx.lineWidth = 1;
          profileCtx.setLineDash([3, 3]);
          profileCtx.beginPath();
          profileCtx.moveTo(markerX, marginTop);
          profileCtx.lineTo(markerX, marginTop + graphH);
          profileCtx.stroke();
          profileCtx.setLineDash([]);

          // Band number label at top
          profileCtx.fillStyle = '#22c55e';
          profileCtx.font = 'bold 10px system-ui';
          profileCtx.textAlign = 'center';
          profileCtx.fillText(`${idx + 1}`, markerX, marginTop - 5);
        });
      }
    }
  }

  // --- Row Strip Image ---

  function drawRowStrip() {
    if (!stripCanvas || !stripCtx || selectedRowId === null || !detectionResult) return;

    const row = detectionResult.rows[selectedRowId];
    if (!row) return;

    const bbox = row.bbox;
    const parent = stripContainer;
    const dpr = window.devicePixelRatio || 1;
    const displayW = parent.clientWidth;
    const displayH = parent.clientHeight;

    stripCanvas.width = displayW * dpr;
    stripCanvas.height = displayH * dpr;
    stripCanvas.style.width = displayW + 'px';
    stripCanvas.style.height = displayH + 'px';

    stripCtx.setTransform(1, 0, 0, 1, 0, 0);
    stripCtx.scale(dpr, dpr);

    // Background
    stripCtx.fillStyle = '#1a1714';
    stripCtx.fillRect(0, 0, displayW, displayH);

    // Calculate drawing area aligned with profile graph
    const drawX = PROFILE_MARGIN_LEFT;
    const drawW = displayW - PROFILE_MARGIN_LEFT - PROFILE_MARGIN_RIGHT;
    const drawH = displayH - 8; // small padding
    const drawY = 4;

    // Source region from original image
    const srcX = bbox.x1;
    const srcY = bbox.y1;
    const srcW = bbox.x2 - bbox.x1;
    const srcH = bbox.y2 - bbox.y1;

    // Draw the cropped row
    stripCtx.drawImage(
      originalImage,
      srcX, srcY, srcW, srcH,
      drawX, drawY, drawW, drawH
    );

    // Draw band markers
    if (row.bands && row.bands.length > 0) {
      stripCtx.strokeStyle = '#22c55e';
      stripCtx.lineWidth = 1;
      stripCtx.setLineDash([2, 2]);

      row.bands.forEach((band, idx) => {
        // Calculate band position relative to row
        const bandRelX = (band.center.x - bbox.x1) / srcW;
        const markerX = drawX + bandRelX * drawW;

        stripCtx.beginPath();
        stripCtx.moveTo(markerX, 0);
        stripCtx.lineTo(markerX, displayH);
        stripCtx.stroke();

        // Band number
        stripCtx.fillStyle = '#22c55e';
        stripCtx.font = 'bold 10px system-ui';
        stripCtx.textAlign = 'center';
        stripCtx.fillText(`${idx + 1}`, markerX, displayH - 2);
      });
    }
  }

  // --- Export ---

  exportBtn.addEventListener('click', () => {
    if (!analysisResult || !analysisResult.bands) {
      alert('No analysis data to export');
      return;
    }

    let csv = 'Band,Mean,Integrated Density,Background Corrected,Relative\n';
    analysisResult.bands.forEach((band, idx) => {
      const i = band.intensity;
      csv += `${idx + 1},${i.mean},${i.integrated_density},${i.background_corrected},${i.relative}\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `band-analysis-row${selectedRowId + 1}-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // --- Demo Modal ---

  function toggleDemoModal(show) {
    if (show) {
      demoModal.classList.remove('hidden');
      void demoModal.offsetWidth;
      demoModal.classList.remove('opacity-0');
      demoModalContent.classList.remove('scale-95');
      loadDemoImages();
    } else {
      demoModal.classList.add('opacity-0');
      demoModalContent.classList.add('scale-95');
      setTimeout(() => {
        demoModal.classList.add('hidden');
      }, 300);
    }
  }

  async function loadDemoImages() {
    try {
      const res = await fetch('/demo-images');
      const images = await res.json();

      demoGrid.innerHTML = '';
      if (images.length === 0) {
        demoGrid.innerHTML = '<p class="col-span-full text-center text-slate-500">No demo images found.</p>';
        return;
      }

      images.forEach(filename => {
        const div = document.createElement('div');
        div.className = 'group relative aspect-square bg-slate-100 rounded-xl overflow-hidden cursor-pointer border-2 border-transparent hover:border-indigo-500 transition-all shadow-sm hover:shadow-md';

        const img = document.createElement('img');
        img.src = `/static/demo_images/${filename}`;
        img.className = 'w-full h-full object-cover transition-transform duration-500 group-hover:scale-110';

        const overlay = document.createElement('div');
        overlay.className = 'absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-end p-3';

        const label = document.createElement('span');
        label.className = 'text-xs font-medium text-white bg-black/60 backdrop-blur-md px-2 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity';
        label.textContent = filename;

        overlay.appendChild(label);
        div.appendChild(img);
        div.appendChild(overlay);

        div.onclick = () => selectDemoImage(filename);
        demoGrid.appendChild(div);
      });
    } catch (e) {
      console.error(e);
      demoGrid.innerHTML = '<p class="col-span-full text-center text-red-500">Error loading images.</p>';
    }
  }

  function selectDemoImage(filename) {
    toggleDemoModal(false);
    setLoading(true, 'Loading image...');

    // Reset state
    detectionResult = null;
    selectedRowId = null;
    analysisResult = null;
    hideAnalysisUI();
    bandCount.textContent = '--';
    rowCount.textContent = '--';

    currentFilename = filename;
    originalImage.src = `/static/demo_images/${filename}?t=${Date.now()}`;
    originalImage.onload = () => {
      imgResLabel.textContent = `${originalImage.naturalWidth} x ${originalImage.naturalHeight}`;
      isImageLoaded = true;
      detectBtn.disabled = false;
      statusHint.textContent = 'Click "Detect Bands" to analyze';
      showImage();
      setLoading(false);
      resizeOverlay();
      ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    };
  }

  // --- Event Listeners ---

  if (selectDemoBtn) selectDemoBtn.addEventListener('click', () => toggleDemoModal(true));
  if (demoBtn) demoBtn.addEventListener('click', () => toggleDemoModal(true));
  if (closeDemoModalBtn) closeDemoModalBtn.addEventListener('click', () => toggleDemoModal(false));

  demoModal.addEventListener('click', (e) => {
    if (e.target === demoModal) toggleDemoModal(false);
  });

});
