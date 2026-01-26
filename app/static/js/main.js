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

  // Files sidebar elements
  const filesList = document.getElementById('filesList');
  const filesEmptyState = document.getElementById('filesEmptyState');
  const uploadBtn = document.getElementById('uploadBtn');
  const fileInput = document.getElementById('fileInput');

  // Theme toggle element
  const themeToggle = document.getElementById('themeToggle');

  // State
  let uploadedFiles = []; // { id, name, dataUrl, analyzed }
  let activeFileId = null;
  let currentFilename = null;
  let detectionResult = null;
  let selectedRowId = null;
  let analysisResult = null;
  let isImageLoaded = false;

  // Adjusted band box positions: { [rowId]: [centerX1, centerX2, ...] }
  let adjustedBoxCenters = {};

  // Strip drag state
  let stripDragState = {
    isDragging: false,
    bandIdx: null,
    startX: 0,
    startCenterX: 0
  };

  // Cached strip drawing coordinates (set in drawRowStrip, used in drag handlers)
  let stripDrawCoords = { drawX: 0, drawW: 0, srcW: 0, bbox: null };

  // Profile drawing margins (shared with strip for alignment)
  const PROFILE_MARGIN_LEFT = 50;

  // --- Theme Management ---

  function initTheme() {
    const savedTheme = localStorage.getItem('vitreous-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    setTheme(theme);
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('vitreous-theme', theme);
  }

  function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    // Redraw profile and strip if they're visible
    if (selectedRowId !== null && analysisResult) {
      drawProfile();
      drawRowStrip();
    }
  }

  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }

  // Initialize theme on load
  initTheme();

  // Helper to get CSS variable value
  function getCSSVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  const PROFILE_MARGIN_RIGHT = 20;

  // --- Uniform Box Helpers ---

  function getUniformBoxSize(rowId) {
    if (!detectionResult || !detectionResult.rows[rowId]) return { width: 0, height: 0 };

    const row = detectionResult.rows[rowId];
    let maxWidth = 0;

    row.bands.forEach(band => {
      const width = band.bbox.x2 - band.bbox.x1;
      if (width > maxWidth) maxWidth = width;
    });

    const height = row.bbox.y2 - row.bbox.y1;
    return { width: maxWidth, height };
  }

  function getEffectiveBoxCenters(rowId) {
    if (adjustedBoxCenters[rowId]) {
      return adjustedBoxCenters[rowId];
    }
    // Use original band centers
    if (!detectionResult || !detectionResult.rows[rowId]) return [];
    const row = detectionResult.rows[rowId];
    return row.bands.map(b => b.center.x);
  }

  function getEffectiveBboxes(rowId) {
    const centers = getEffectiveBoxCenters(rowId);
    const { width, height } = getUniformBoxSize(rowId);
    if (!detectionResult || !detectionResult.rows[rowId]) return [];
    const row = detectionResult.rows[rowId];

    return centers.map(centerX => ({
      x1: Math.round(centerX - width / 2),
      y1: row.bbox.y1,
      x2: Math.round(centerX + width / 2),
      y2: row.bbox.y2
    }));
  }

  // --- Initialize ---

  checkModelStatus();
  loadInitialImage();

  confidenceSlider.addEventListener('input', () => {
    confidenceValue.textContent = (confidenceSlider.value / 100).toFixed(2);
  });

  // File upload handlers
  if (uploadBtn) {
    uploadBtn.addEventListener('click', () => fileInput.click());
  }
  if (fileInput) {
    fileInput.addEventListener('change', handleFileUpload);
  }

  // --- Files Library ---

  async function handleFileUpload(e) {
    const files = Array.from(e.target.files);
    for (const file of files) {
      if (!file.type.startsWith('image/')) continue;
      
      // Upload to server
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        setLoading(true, 'Uploading...');
        const res = await fetch('/upload', {
          method: 'POST',
          body: formData
        });
        
        if (!res.ok) {
          console.error('Upload failed');
          continue;
        }
        
        const result = await res.json();
        
        const newFile = {
          id: Date.now() + Math.random(),
          name: result.filename,
          dataUrl: result.path,
          analyzed: false
        };
        uploadedFiles.push(newFile);
        renderFilesList();
        selectFile(newFile.id);
      } catch (err) {
        console.error('Upload error:', err);
      } finally {
        setLoading(false);
      }
    }
    fileInput.value = '';
  }

  function renderFilesList() {
    if (!filesList) return;
    const fileItems = uploadedFiles.map(f => `
      <div class="file-item group cursor-pointer rounded-lg border-2 transition-all overflow-hidden theme-transition ${f.id === activeFileId ? 'shadow-md' : 'border-transparent hover:shadow-sm'}"
           style="background: var(--bg-card); ${f.id === activeFileId ? 'border-color: var(--accent);' : 'border-color: transparent;'}"
           data-file-id="${f.id}">
        <div class="aspect-[4/3] overflow-hidden" style="background: var(--bg-primary);">
          <img src="${f.dataUrl}" alt="${f.name}" class="w-full h-full object-cover" />
        </div>
        <div class="px-2.5 py-2">
          <p class="text-xs truncate font-medium" style="color: var(--text-primary);">${f.name}</p>
          <div class="flex items-center gap-1.5 mt-1">
            ${f.analyzed
              ? '<span class="w-2 h-2 rounded-full" style="background: var(--accent);"></span><span class="text-[10px] font-medium" style="color: var(--accent-dark);">Analyzed</span>'
              : '<span class="w-2 h-2 rounded-full" style="background: var(--border-primary);"></span><span class="text-[10px]" style="color: var(--text-muted);">Pending</span>'
            }
          </div>
        </div>
      </div>
    `).join('');
    
    filesEmptyState.classList.toggle('hidden', uploadedFiles.length > 0);
    filesList.innerHTML = (uploadedFiles.length > 0 ? fileItems : '') + filesEmptyState.outerHTML;
    
    // Re-attach click handlers
    filesList.querySelectorAll('.file-item').forEach(item => {
      item.addEventListener('click', () => selectFile(Number(item.dataset.fileId)));
    });
  }

  function selectFile(fileId) {
    const file = uploadedFiles.find(f => f.id === fileId);
    if (!file) return;
    
    activeFileId = fileId;
    currentFilename = file.name;
    
    // Load the image
    emptyState.classList.add('hidden');
    canvasContainer.classList.remove('hidden');
    originalImage.src = file.dataUrl;
    
    originalImage.onload = () => {
      imgResLabel.textContent = `${originalImage.naturalWidth} × ${originalImage.naturalHeight}`;
      isImageLoaded = true;
      detectBtn.disabled = false;
      statusHint.textContent = 'Click "Analyze" to detect bands';
      resizeOverlay();
      // Reset detection state
      detectionResult = null;
      selectedRowId = null;
      analysisResult = null;
      adjustedBoxCenters = {}; // Clear any user adjustments
      bandCount.textContent = '--';
      rowCount.textContent = '--';
    };
    
    renderFilesList();
  }

  function markFileAnalyzed(fileId) {
    const file = uploadedFiles.find(f => f.id === fileId);
    if (file) {
      file.analyzed = true;
      renderFilesList();
    }
  }

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
    // Add initial demo image to files list
    const initialFile = {
      id: Date.now(),
      name: 'initial.png',
      dataUrl: '/static/demo_images/initial.png',
      analyzed: false
    };
    uploadedFiles.push(initialFile);
    activeFileId = initialFile.id;
    renderFilesList();
    
    emptyState.classList.add('hidden');
    canvasContainer.classList.remove('hidden');
    originalImage.src = '/static/demo_images/initial.png';
    currentFilename = 'initial.png';
    originalImage.onload = () => {
      imgResLabel.textContent = `${originalImage.naturalWidth} × ${originalImage.naturalHeight}`;
      isImageLoaded = true;
      detectBtn.disabled = false;
      statusHint.textContent = 'Click "Analyze" to detect bands';
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

  // Calculate displayed image bounds accounting for object-contain
  function getImageDisplayBounds() {
    const containerRect = originalImage.getBoundingClientRect();
    const containerW = containerRect.width;
    const containerH = containerRect.height;
    const imgW = originalImage.naturalWidth;
    const imgH = originalImage.naturalHeight;
    
    if (!imgW || !imgH) return { offsetX: 0, offsetY: 0, scale: 1 };
    
    const containerRatio = containerW / containerH;
    const imageRatio = imgW / imgH;
    
    let displayW, displayH, offsetX, offsetY;
    
    if (imageRatio > containerRatio) {
      // Image is wider - letterbox top/bottom
      displayW = containerW;
      displayH = containerW / imageRatio;
      offsetX = 0;
      offsetY = (containerH - displayH) / 2;
    } else {
      // Image is taller - letterbox left/right
      displayH = containerH;
      displayW = containerH * imageRatio;
      offsetX = (containerW - displayW) / 2;
      offsetY = 0;
    }
    
    const scale = displayW / imgW;
    return { offsetX, offsetY, scale, displayW, displayH };
  }

  function drawDetections() {
    if (!detectionResult || !detectionResult.rows) return;

    resizeOverlay();
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    const { offsetX, offsetY, scale } = getImageDisplayBounds();

    detectionResult.rows.forEach((row, rowIdx) => {
      const isSelected = rowIdx === selectedRowId;

      // Draw row bounding box
      const rowBbox = row.bbox;
      ctx.strokeStyle = isSelected ? '#22c55e' : '#6366f1';
      ctx.lineWidth = isSelected ? 3 : 1;
      ctx.setLineDash(isSelected ? [] : [4, 4]);
      ctx.strokeRect(
        offsetX + rowBbox.x1 * scale,
        offsetY + rowBbox.y1 * scale,
        (rowBbox.x2 - rowBbox.x1) * scale,
        (rowBbox.y2 - rowBbox.y1) * scale
      );

      // Draw individual bands
      row.bands.forEach((band, bandIdx) => {
        const bbox = band.bbox;
        const x = offsetX + bbox.x1 * scale;
        const y = offsetY + bbox.y1 * scale;
        const w = (bbox.x2 - bbox.x1) * scale;
        const h = (bbox.y2 - bbox.y1) * scale;

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
      ctx.fillText(`Row ${rowIdx + 1}`, offsetX + rowBbox.x1 * scale, offsetY + rowBbox.y1 * scale - 8);
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

    const canvasRect = overlayCanvas.getBoundingClientRect();
    const { offsetX, offsetY, scale } = getImageDisplayBounds();

    // Get click position in canvas coordinates
    const canvasX = e.clientX - canvasRect.left;
    const canvasY = e.clientY - canvasRect.top;
    
    // Convert to image coordinates (accounting for letterboxing)
    const clickX = (canvasX - offsetX) / scale;
    const clickY = (canvasY - offsetY) / scale;

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
    adjustedBoxCenters = {}; // Clear any user adjustments
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
        // Mark file as analyzed
        if (activeFileId) markFileAnalyzed(activeFileId);
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

    // Analysis panel - show label, hide skeleton, enable export
    selectedRowLabel.textContent = `Row ${rowId + 1}`;
    selectedRowLabel.classList.remove('hidden');
    const bandTableSkeleton = document.getElementById('bandTableSkeleton');
    if (bandTableSkeleton) bandTableSkeleton.classList.add('hidden');
    if (exportBtn) {
      exportBtn.disabled = false;
      exportBtn.classList.remove('opacity-50');
    }

    // Add slide-up animation to profile area
    profileCanvas.classList.add('slide-up');
    stripCanvas.classList.add('slide-up');

    // Remove animation classes after they complete (for re-triggering)
    setTimeout(() => {
      profileCanvas.classList.remove('slide-up');
      stripCanvas.classList.remove('slide-up');
    }, 300);
  }

  function hideAnalysisUI() {
    profileSubtitle.textContent = 'Click a detected row to view profile';
    selectedRowBadge.classList.add('hidden');
    profileEmptyState.classList.remove('hidden');
    profileCanvas.classList.add('hidden');
    stripEmptyState.classList.remove('hidden');
    stripCanvas.classList.add('hidden');
    
    // Show skeleton, hide label, disable export
    selectedRowLabel.classList.add('hidden');
    const bandTableSkeleton = document.getElementById('bandTableSkeleton');
    if (bandTableSkeleton) bandTableSkeleton.classList.remove('hidden');
    if (bandTableBody) bandTableBody.innerHTML = '';
    if (exportBtn) {
      exportBtn.disabled = true;
      exportBtn.classList.add('opacity-50');
    }
  }

  function populateBandTable() {
    if (!analysisResult || !analysisResult.bands) return;

    bandTableBody.innerHTML = '';

    analysisResult.bands.forEach((band, idx) => {
      const intensity = band.intensity;
      const relPercent = (intensity.relative * 100).toFixed(1);

      const tr = document.createElement('tr');
      tr.className = 'theme-transition';
      tr.style.cssText = 'background: var(--bg-card);';
      tr.innerHTML = `
        <td class="px-5 py-2.5 font-medium" style="color: var(--text-primary);">Band ${idx + 1}</td>
        <td class="px-5 py-2.5 text-right font-mono" style="color: var(--text-secondary);">${intensity.mean.toFixed(1)}</td>
        <td class="px-5 py-2.5 text-right font-mono" style="color: var(--text-secondary);">${intensity.integrated_density.toFixed(0)}</td>
        <td class="px-5 py-2.5 text-right font-mono" style="color: var(--text-secondary);">${intensity.background_corrected.toFixed(0)}</td>
        <td class="px-5 py-2.5 text-right">
          <div class="flex items-center justify-end gap-3">
            <div class="w-20 rounded-full h-2" style="background: var(--border-primary);">
              <div class="h-2 rounded-full" style="width: ${relPercent}%; background: var(--accent);"></div>
            </div>
            <span class="font-medium font-mono w-14 text-right" style="color: var(--text-primary);">${relPercent}%</span>
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

    // Get theme-aware colors
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const bgColor = getCSSVar('--bg-card');
    const gridColor = isDark ? 'rgba(243, 235, 224, 0.1)' : 'rgba(42, 38, 34, 0.1)';
    const lineColor = getCSSVar('--text-primary');
    const axisColor = getCSSVar('--text-muted');
    const labelColor = getCSSVar('--text-secondary');
    const fillColorStart = isDark ? 'rgba(243, 235, 224, 0.2)' : 'rgba(42, 38, 34, 0.25)';
    const fillColorEnd = isDark ? 'rgba(243, 235, 224, 0.02)' : 'rgba(42, 38, 34, 0.03)';

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
    profileCtx.fillStyle = bgColor;
    profileCtx.fillRect(0, 0, displayW, displayH);

    // Grid
    profileCtx.strokeStyle = gridColor;
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
    profileCtx.strokeStyle = lineColor;
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
    gradient.addColorStop(0, fillColorStart);
    gradient.addColorStop(1, fillColorEnd);
    profileCtx.fillStyle = gradient;
    profileCtx.fill();

    // Axes
    profileCtx.strokeStyle = axisColor;
    profileCtx.lineWidth = 1;
    profileCtx.beginPath();
    profileCtx.moveTo(PROFILE_MARGIN_LEFT, marginTop);
    profileCtx.lineTo(PROFILE_MARGIN_LEFT, marginTop + graphH);
    profileCtx.lineTo(PROFILE_MARGIN_LEFT + graphW, marginTop + graphH);
    profileCtx.stroke();

    // Labels
    profileCtx.fillStyle = labelColor;
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

    // --- Background Threshold Line ---
    // Draw average background level as horizontal dashed line
    if (analysisResult && analysisResult.bands && analysisResult.bands.length > 0) {
      const avgBackground = analysisResult.bands.reduce((sum, b) => sum + (b.intensity.background || 0), 0)
                          / analysisResult.bands.length;

      // Only draw if background is within visible range
      if (avgBackground >= minVal && avgBackground <= maxVal) {
        const bgNormalized = (avgBackground - minVal) / range;
        const bgY = marginTop + graphH * (1 - bgNormalized);

        // Get accent color for background line
        const accentColor = getCSSVar('--accent');

        // Draw dashed background line
        profileCtx.strokeStyle = accentColor + '80'; // 50% opacity
        profileCtx.lineWidth = 1;
        profileCtx.setLineDash([4, 4]);
        profileCtx.beginPath();
        profileCtx.moveTo(PROFILE_MARGIN_LEFT, bgY);
        profileCtx.lineTo(PROFILE_MARGIN_LEFT + graphW, bgY);
        profileCtx.stroke();
        profileCtx.setLineDash([]);

        // BG label on left
        profileCtx.fillStyle = accentColor;
        profileCtx.font = '10px system-ui';
        profileCtx.textAlign = 'right';
        profileCtx.fillText('BG', PROFILE_MARGIN_LEFT - 5, bgY + 3);
      }
    }

    // --- Band Boundary Lines ---
    // Draw vertical lines at band edges showing where pixel counting happens
    // Uses effective bboxes (respecting user adjustments)
    if (detectionResult && selectedRowId !== null) {
      const row = detectionResult.rows[selectedRowId];
      if (row && row.bands && row.bands.length > 0) {
        const rowBbox = row.bbox;
        const rowWidth = rowBbox.x2 - rowBbox.x1;

        // Get accent color for band boundaries
        const accentColor = getCSSVar('--accent');

        // Use effective bboxes (includes user adjustments)
        const effectiveBboxes = getEffectiveBboxes(selectedRowId);

        effectiveBboxes.forEach((bbox, idx) => {
          // Calculate edge positions relative to graph
          const leftRelX = (bbox.x1 - rowBbox.x1) / rowWidth;
          const rightRelX = (bbox.x2 - rowBbox.x1) / rowWidth;
          const leftX = PROFILE_MARGIN_LEFT + leftRelX * graphW;
          const rightX = PROFILE_MARGIN_LEFT + rightRelX * graphW;

          // Draw band boundary lines (burnt sienna, semi-transparent)
          profileCtx.strokeStyle = accentColor + '66'; // 40% opacity
          profileCtx.lineWidth = 1;
          profileCtx.setLineDash([]);

          // Left boundary
          profileCtx.beginPath();
          profileCtx.moveTo(leftX, marginTop);
          profileCtx.lineTo(leftX, marginTop + graphH);
          profileCtx.stroke();

          // Right boundary
          profileCtx.beginPath();
          profileCtx.moveTo(rightX, marginTop);
          profileCtx.lineTo(rightX, marginTop + graphH);
          profileCtx.stroke();

          // Band number label (centered between boundaries)
          const centerX = (leftX + rightX) / 2;
          profileCtx.fillStyle = accentColor;
          profileCtx.font = 'bold 10px system-ui';
          profileCtx.textAlign = 'center';
          profileCtx.fillText(`${idx + 1}`, centerX, marginTop - 5);
        });
      }
    }
  }

  // --- Row Strip Image ---

  function drawRowStrip() {
    if (!stripCanvas || !stripCtx || selectedRowId === null || !detectionResult) return;

    const row = detectionResult.rows[selectedRowId];
    if (!row) return;

    // Get theme-aware strip background (always dark for contrast)
    const stripBg = document.documentElement.getAttribute('data-theme') === 'dark' ? '#0a0908' : '#1c1815';

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
    stripCtx.fillStyle = stripBg;
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

    // Cache coordinates for drag handlers
    stripDrawCoords = { drawX, drawW, srcW, bbox };

    // Draw the cropped row
    stripCtx.drawImage(
      originalImage,
      srcX, srcY, srcW, srcH,
      drawX, drawY, drawW, drawH
    );

    // Draw uniform band boxes
    const { width: boxWidth } = getUniformBoxSize(selectedRowId);
    const centers = getEffectiveBoxCenters(selectedRowId);
    const accentColor = getCSSVar('--accent');

    centers.forEach((centerX, idx) => {
      // Convert image coords to canvas coords
      const relCenterX = (centerX - bbox.x1) / srcW;
      const canvasCenterX = drawX + relCenterX * drawW;
      const canvasBoxWidth = (boxWidth / srcW) * drawW;

      const boxLeft = canvasCenterX - canvasBoxWidth / 2;

      // Draw box outline
      stripCtx.strokeStyle = accentColor;
      stripCtx.lineWidth = 2;
      stripCtx.strokeRect(boxLeft, drawY, canvasBoxWidth, drawH);

      // Semi-transparent fill to show the box area
      stripCtx.fillStyle = accentColor + '1a'; // 10% opacity
      stripCtx.fillRect(boxLeft, drawY, canvasBoxWidth, drawH);

      // Band number label
      stripCtx.fillStyle = accentColor;
      stripCtx.font = 'bold 10px system-ui';
      stripCtx.textAlign = 'center';
      stripCtx.fillText(`${idx + 1}`, canvasCenterX, displayH - 2);
    });
  }

  // --- Strip Canvas Drag Handlers ---

  function findBoxAtPoint(canvasX) {
    if (selectedRowId === null || !detectionResult) return null;

    const { drawX, drawW, srcW, bbox } = stripDrawCoords;
    if (!bbox) return null;

    const { width: boxWidth } = getUniformBoxSize(selectedRowId);
    const centers = getEffectiveBoxCenters(selectedRowId);

    for (let i = 0; i < centers.length; i++) {
      const relCenterX = (centers[i] - bbox.x1) / srcW;
      const canvasCenterX = drawX + relCenterX * drawW;
      const canvasBoxWidth = (boxWidth / srcW) * drawW;

      const boxLeft = canvasCenterX - canvasBoxWidth / 2;
      const boxRight = canvasCenterX + canvasBoxWidth / 2;

      if (canvasX >= boxLeft && canvasX <= boxRight) {
        return i;
      }
    }
    return null;
  }

  function onStripMouseDown(e) {
    if (selectedRowId === null) return;

    const rect = stripCanvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const canvasX = (e.clientX - rect.left);

    const bandIdx = findBoxAtPoint(canvasX);
    if (bandIdx !== null) {
      stripDragState.isDragging = true;
      stripDragState.bandIdx = bandIdx;
      stripDragState.startX = canvasX;
      stripDragState.startCenterX = getEffectiveBoxCenters(selectedRowId)[bandIdx];
      stripCanvas.style.cursor = 'grabbing';
    }
  }

  function onStripMouseMove(e) {
    const rect = stripCanvas.getBoundingClientRect();
    const canvasX = (e.clientX - rect.left);

    if (stripDragState.isDragging && selectedRowId !== null) {
      const { drawW, srcW, bbox } = stripDrawCoords;
      if (!bbox) return;

      // Calculate new center position
      const deltaCanvas = canvasX - stripDragState.startX;
      const deltaImage = (deltaCanvas / drawW) * srcW;
      let newCenterX = stripDragState.startCenterX + deltaImage;

      // Clamp to row bounds
      const { width: boxWidth } = getUniformBoxSize(selectedRowId);
      newCenterX = Math.max(bbox.x1 + boxWidth / 2, Math.min(bbox.x2 - boxWidth / 2, newCenterX));

      // Update adjusted centers
      if (!adjustedBoxCenters[selectedRowId]) {
        adjustedBoxCenters[selectedRowId] = [...getEffectiveBoxCenters(selectedRowId)];
      }
      adjustedBoxCenters[selectedRowId][stripDragState.bandIdx] = newCenterX;

      // Redraw
      drawRowStrip();
      drawProfile();
    } else {
      // Update cursor based on hover
      const bandIdx = findBoxAtPoint(canvasX);
      stripCanvas.style.cursor = bandIdx !== null ? 'grab' : 'default';
    }
  }

  async function onStripMouseUp() {
    if (stripDragState.isDragging) {
      stripDragState.isDragging = false;
      stripCanvas.style.cursor = 'default';

      // Recalculate with new positions
      await reanalyzeWithCustomBboxes();
    }
  }

  async function reanalyzeWithCustomBboxes() {
    if (selectedRowId === null) return;

    setLoading(true, 'Recalculating...');

    const bboxes = getEffectiveBboxes(selectedRowId);

    try {
      const res = await fetch('/analyze-row-custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: currentFilename,
          row_id: selectedRowId,
          bboxes: bboxes
        })
      });

      if (!res.ok) throw new Error('Analysis failed');

      analysisResult = await res.json();
      populateBandTable();
      drawProfile();
      drawRowStrip();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  // Attach strip canvas event listeners
  if (stripCanvas) {
    stripCanvas.addEventListener('mousedown', onStripMouseDown);
    stripCanvas.addEventListener('mousemove', onStripMouseMove);
    stripCanvas.addEventListener('mouseup', onStripMouseUp);
    stripCanvas.addEventListener('mouseleave', onStripMouseUp);
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
        demoGrid.innerHTML = '<p class="col-span-full text-center" style="color: var(--text-muted);">No demo images found.</p>';
        return;
      }

      images.forEach(filename => {
        const div = document.createElement('div');
        div.className = 'group relative aspect-square rounded-lg overflow-hidden cursor-pointer border-2 border-transparent transition-all shadow-warm hover:shadow-warm-lg theme-transition';
        div.style.cssText = 'background: var(--bg-tertiary);';
        div.onmouseenter = () => div.style.borderColor = 'var(--accent)';
        div.onmouseleave = () => div.style.borderColor = 'transparent';

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
      demoGrid.innerHTML = '<p class="col-span-full text-center" style="color: var(--accent);">Error loading images.</p>';
    }
  }

  function selectDemoImage(filename) {
    toggleDemoModal(false);
    setLoading(true, 'Loading image...');

    // Reset state
    detectionResult = null;
    selectedRowId = null;
    analysisResult = null;
    adjustedBoxCenters = {}; // Clear any user adjustments
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
