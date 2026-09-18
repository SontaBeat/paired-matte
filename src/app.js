    const els = {
      preset: document.getElementById('preset'),
      backgroundMode: document.getElementById('backgroundMode'),
      backgroundColor: document.getElementById('backgroundColor'),
      previewMode: document.getElementById('previewMode'),
      actualSize: document.getElementById('actualSize'),
      colorInput: document.getElementById('colorInput'),
      maskInput: document.getElementById('maskInput'),
      processBtn: document.getElementById('processBtn'),
      downloadBtn: document.getElementById('downloadBtn'),
      canvas: document.getElementById('canvas'),
      empty: document.getElementById('empty'),
      status: document.getElementById('status'),
      stage: document.getElementById('stage'),
      trim: document.getElementById('trim'),
      trimValue: document.getElementById('trimValue'),
      opaque: document.getElementById('opaque'),
      opaqueValue: document.getElementById('opaqueValue'),
      resizeMask: document.getElementById('resizeMask'),
      unmix: document.getElementById('unmix'),
      unmixValue: document.getElementById('unmixValue'),
      edgeClean: document.getElementById('edgeClean'),
      edgeCleanValue: document.getElementById('edgeCleanValue'),
      cloth: document.getElementById('cloth'),
      clothValue: document.getElementById('clothValue'),
      blackTransparent: document.getElementById('blackTransparent'),
    };

    const state = {
      colorBitmap: null,
      maskBitmap: null,
      outputReady: false,
      timer: null,
      output: null,
      color: null,
      mask: null,
      loadVersion: { color: 0, mask: 0 },
    };

    function setStatus(text, isError = false) {
      els.status.textContent = text;
      els.status.classList.toggle('error', isError);
    }

    function updateLabels() {
      els.trimValue.textContent = (Number(els.trim.value) / 1000).toFixed(3);
      els.opaqueValue.textContent = (Number(els.opaque.value) / 1000).toFixed(3);
      els.unmixValue.textContent = (Number(els.unmix.value) / 100).toFixed(2);
      els.edgeCleanValue.textContent = (Number(els.edgeClean.value) / 100).toFixed(2);
      els.clothValue.textContent = (Number(els.cloth.value) / 100).toFixed(2);
    }

    async function loadBitmap(file) {
      if (!file) return null;
      return await createImageBitmap(file);
    }

    function drawBitmapToData(bitmap, width = bitmap.width, height = bitmap.height) {
      const c = document.createElement('canvas');
      c.width = width;
      c.height = height;
      const ctx = c.getContext('2d', { willReadFrequently: true });
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(bitmap, 0, 0, width, height);
      return ctx.getImageData(0, 0, width, height);
    }

    function estimateBorderRgb(imageData, borderSize = 24) {
      const { data, width, height } = imageData;
      const samples = [];
      const push = (x, y) => {
        const i = (y * width + x) * 4;
        samples.push([data[i], data[i + 1], data[i + 2]]);
      };

      const b = Math.min(borderSize, Math.floor(width / 2), Math.floor(height / 2));
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          if (x < b || x >= width - b || y < b || y >= height - b) push(x, y);
        }
      }

      const med = [0, 1, 2].map((ch) => {
        const values = samples.map((s) => s[ch]).sort((a, b) => a - b);
        return values[Math.floor(values.length / 2)] || 0;
      });
      return med;
    }

    const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
    const normDist = (r, g, b, bg) => {
      const dr = r - bg[0], dg = g - bg[1], db = b - bg[2];
      return Math.sqrt(dr * dr + dg * dg + db * db);
    };

    function processImages() {
      state.outputReady = false;
      els.downloadBtn.disabled = true;
      if (!state.colorBitmap || !state.maskBitmap) {
        setStatus('等待图片');
        return;
      }

      const width = state.colorBitmap.width;
      const height = state.colorBitmap.height;
      const colorData = drawBitmapToData(state.colorBitmap);
      const maskWidth = els.resizeMask.checked ? width : state.maskBitmap.width;
      const maskHeight = els.resizeMask.checked ? height : state.maskBitmap.height;
      const maskData = drawBitmapToData(state.maskBitmap, maskWidth, maskHeight);

      if (maskData.width !== width || maskData.height !== height) {
        els.canvas.hidden = true;
        setStatus('尺寸不同：检查是否为正确配对；仅画布大小差异才允许缩放。', true);
        return;
      }

      const trim = Number(els.trim.value) / 1000;
      const opaque = Number(els.opaque.value) / 1000;
      const unmixAmount = Number(els.unmix.value) / 100;
      const edgeCleanAmount = Number(els.edgeClean.value) / 100;
      const clothAmount = Number(els.cloth.value) / 100;
      const bg = els.backgroundMode.value === 'border' ? estimateBorderRgb(colorData) :
        [1, 3, 5].map(i => parseInt(els.backgroundColor.value.slice(i, i + 2), 16));

      const out = new ImageData(width, height);
      const cd = colorData.data;
      const md = maskData.data;
      const od = out.data;

      for (let i = 0; i < cd.length; i += 4) {
        const r0 = cd[i], g0 = cd[i + 1], b0 = cd[i + 2];
        const mr = md[i], mg = md[i + 1], mb = md[i + 2];
        const maxMask = Math.max(mr, mg, mb);
        const lumaMask = 0.2126 * mr + 0.7152 * mg + 0.0722 * mb;
        let a = Math.max(lumaMask, maxMask * 0.96) / 255;
        a = clamp((a - trim) / Math.max(0.0001, 1 - trim), 0, 1);
        if (trim > 0 && a < 0.006) a = 0;
        if (a > opaque) a = 1;

        const safe = Math.max(a, 1 / 255);
        let ur = clamp((r0 - (1 - a) * bg[0]) / safe, 0, 255);
        let ug = clamp((g0 - (1 - a) * bg[1]) / safe, 0, 255);
        let ub = clamp((b0 - (1 - a) * bg[2]) / safe, 0, 255);

        const brightness = Math.max(r0, g0, b0);
        const lightness = clamp((brightness - 95) / 120, 0, 1);
        const semi = a > 0.02 && a < 0.985 ? 1 : 0;
        let strength = clamp((0.94 - a) / 0.74, 0, 1) * semi;
        strength = clamp(strength * (0.28 + 0.72 * lightness) * unmixAmount, 0, 0.9);

        let r = r0 * (1 - strength) + ur * strength;
        let g = g0 * (1 - strength) + ug * strength;
        let b = b0 * (1 - strength) + ub * strength;

        const cloth = clamp(maxMask * 1.06 + 14, 0, 255);
        const cr = cloth * 0.985, cg = cloth, cb = cloth * 1.025;
        const low = clamp((0.38 - a) / 0.32, 0, 1) * semi * lightness * clothAmount;
        r = r * (1 - low * 0.72) + cr * (low * 0.72);
        g = g * (1 - low * 0.72) + cg * (low * 0.72);
        b = b * (1 - low * 0.72) + cb * (low * 0.72);

        const dist = normDist(r0, g0, b0, bg);
        const darkKeep = clamp((105 - brightness) / 55, 0, 1);
        const brightKeep = clamp((brightness - 150) / 75, 0, 1);
        const distKeep = clamp((dist - 10) / 42, 0, 1);
        const keep = Math.max(darkKeep, brightKeep, distKeep);
        const edgeZone = a > 0 && a < 0.82 ? 1 : 0;
        a = a * (1 - edgeZone * (1 - keep) * 0.95 * edgeCleanAmount);
        if ((trim > 0 || edgeCleanAmount > 0) && a < 0.008) a = 0;

        const mx = Math.max(r, g, b);
        const mn = Math.min(r, g, b);
        const sat = (mx - mn) / Math.max(mx, 1);
        const edge = clamp((1.02 - a) / 0.82, 0, 1) * semi * lightness;
        const whiteLift = clamp((0.20 - sat) / 0.20, 0, 1) * edge * 0.22 * clothAmount;
        const whiteish = clamp(0.88 * mx + 0.12 * ((r + g + b) / 3), 0, 255);
        r = r * (1 - whiteLift) + whiteish * 0.99 * whiteLift;
        g = g * (1 - whiteLift) + whiteish * whiteLift;
        b = b * (1 - whiteLift) + whiteish * 1.02 * whiteLift;

        if (a <= 0 && els.blackTransparent.checked) {
          r = 0; g = 0; b = 0;
        }

        od[i] = clamp(Math.round(r), 0, 255);
        od[i + 1] = clamp(Math.round(g), 0, 255);
        od[i + 2] = clamp(Math.round(b), 0, 255);
        od[i + 3] = clamp(Math.round(a * 255), 0, 255);
      }

      state.output = out;
      state.color = colorData;
      state.mask = maskData;
      renderPreview();
      els.canvas.hidden = false;
      els.empty.hidden = true;
      state.outputReady = true;
      els.downloadBtn.disabled = false;
      setStatus(`已生成 ${width}×${height}，背景 #${bg.map(v => v.toString(16).padStart(2, '0')).join('')}`);
    }

    function renderPreview() {
      if (!state.output) return;
      const { width, height } = state.output;
      let data = state.output;
      if (els.previewMode.value === 'color') data = state.color;
      if (els.previewMode.value === 'mask') data = state.mask;
      if (els.previewMode.value === 'overlay') {
        // Inspect against the input color image; do not inspect a mask-clipped result.
        data = new ImageData(new Uint8ClampedArray(state.color.data), width, height);
        const m = state.mask.data;
        const inside = (x, y) => m[(y * width + x) * 4] > 8;
        for (let y = 1; y < height - 1; y++) for (let x = 1; x < width - 1; x++) {
          const v = inside(x, y);
          if (v !== inside(x-1, y) || v !== inside(x+1, y) || v !== inside(x, y-1) || v !== inside(x, y+1)) {
            data.data.set([255, 40, 40, 255], (y * width + x) * 4);
          }
        }
      }
      els.canvas.width = width;
      els.canvas.height = height;
      els.canvas.getContext('2d').putImageData(data, 0, 0);
    }

    function applyPreset() {
      const p = els.preset.value === 'cloth' ? [4, 992, 90, 95, 72] : [0, 1000, 90, 0, 0];
      ['trim', 'opaque', 'unmix', 'edgeClean', 'cloth'].forEach((key, i) => els[key].value = p[i]);
      scheduleProcess();
    }

    function scheduleProcess() {
      updateLabels();
      clearTimeout(state.timer);
      if (!state.colorBitmap || !state.maskBitmap) return;
      state.timer = setTimeout(processImages, 80);
    }

    async function onFileChange(kind) {
      const version = ++state.loadVersion[kind];
      state.outputReady = false;
      state.output = null;
      els.downloadBtn.disabled = true;
      els.processBtn.disabled = true;
      els.canvas.hidden = true;
      const slot = kind === 'color' ? 'colorBitmap' : 'maskBitmap';
      state[slot]?.close();
      state[slot] = null;
      try {
        setStatus('读取图片中');
        const file = kind === 'color' ? els.colorInput.files[0] : els.maskInput.files[0];
        const bitmap = await loadBitmap(file);
        if (version !== state.loadVersion[kind]) { bitmap?.close(); return; }
        if (kind === 'color') state.colorBitmap = bitmap;
        if (kind === 'mask') state.maskBitmap = bitmap;
        els.processBtn.disabled = !(state.colorBitmap && state.maskBitmap);
        if (state.colorBitmap && state.maskBitmap) processImages();
        else setStatus('等待另一张图片');
      } catch (err) {
        setStatus(err.message || '图片读取失败', true);
      }
    }

    function downloadPng() {
      if (!state.outputReady) return;
      // Export always uses the result, never the mask/outline preview.
      const exportCanvas = document.createElement('canvas');
      exportCanvas.width = state.output.width;
      exportCanvas.height = state.output.height;
      exportCanvas.getContext('2d').putImageData(state.output, 0, 0);
      exportCanvas.toBlob((blob) => {
        if (!blob) {
          setStatus('导出失败', true);
          return;
        }
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `cutout-${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.png`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 500);
      }, 'image/png');
    }

    document.querySelectorAll('.view-toggle button').forEach((button) => {
      button.addEventListener('click', () => {
        document.querySelectorAll('.view-toggle button').forEach((b) => b.classList.remove('active'));
        button.classList.add('active');
        els.stage.classList.remove('dark', 'light');
        const view = button.dataset.view;
        if (view === 'dark') els.stage.classList.add('dark');
        if (view === 'light') els.stage.classList.add('light');
      });
    });

    els.colorInput.addEventListener('change', () => onFileChange('color'));
    els.maskInput.addEventListener('change', () => onFileChange('mask'));
    els.processBtn.addEventListener('click', processImages);
    els.downloadBtn.addEventListener('click', downloadPng);
    [els.trim, els.opaque, els.resizeMask, els.unmix, els.edgeClean, els.cloth, els.blackTransparent]
      .forEach((el) => el.addEventListener('input', scheduleProcess));

    els.preset.addEventListener('change', applyPreset);
    els.backgroundMode.addEventListener('change', scheduleProcess);
    els.backgroundColor.addEventListener('input', scheduleProcess);
    els.previewMode.addEventListener('change', renderPreview);
    els.actualSize.addEventListener('change', () => els.stage.classList.toggle('actual', els.actualSize.checked));
    applyPreset();
