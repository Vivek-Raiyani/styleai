/* ============================================================
   STYLEAI STUDIO — app.js
   1. Canvas-based image resize (client-side, before upload)
   2. Drag-and-drop upload zones
   3. CameraKit bridge (YMK SDK → hidden base64 field)
   4. Flash message auto-dismiss
   ============================================================ */

'use strict';

// ── Per-module max dimensions for canvas resize ─────────────
const MODULE_CONSTRAINTS = {
  skin:     { maxW: 2560, maxH: 2560 },
  palette:  { maxW: 4096, maxH: 4096 },
  hair:     { maxW: 1920, maxH: 1920 },
  eyes:     { maxW: 1920, maxH: 1920 },
  style:    { maxW: 4096, maxH: 4096 },
  complete: { maxW: 2560, maxH: 2560 },
  default:  { maxW: 2048, maxH: 2048 },
};

// ── Canvas resize & auto-scaling ────────────────────────────
function resizeImage(file, maxW, maxH, minShortSide = 480) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      let { width, height } = img;
      
      // Auto-upscale low-res thumbnails to meet API requirements
      const shortSide = Math.min(width, height);
      let scale = 1;
      if (shortSide < minShortSide) {
        scale = minShortSide / shortSide;
      }

      let targetW = Math.round(width * scale);
      let targetH = Math.round(height * scale);

      // Downscale if exceeds max dimensions
      const maxRatio = Math.min(1, maxW / targetW, maxH / targetH);
      const finalW = Math.round(targetW * maxRatio);
      const finalH = Math.round(targetH * maxRatio);

      if (scale === 1 && maxRatio === 1 && file.type === 'image/jpeg') {
        resolve(file);
        return;
      }

      const canvas = document.createElement('canvas');
      canvas.width  = finalW;
      canvas.height = finalH;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, finalW, finalH);
      canvas.toBlob(
        (blob) => resolve(new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), { type: 'image/jpeg' })),
        'image/jpeg', 0.92
      );
    };
    img.src = url;
  });
}

// ── Upload zone setup ───────────────────────────────────────
function setupUploadZone(zoneEl) {
  const input   = zoneEl.querySelector('input[type="file"]');
  const preview = zoneEl.querySelector('.upload-preview');
  const previewImg = preview ? preview.querySelector('img') : null;
  const module  = document.body.dataset.module || 'default';
  const { maxW, maxH } = MODULE_CONSTRAINTS[module] || MODULE_CONSTRAINTS.default;

  if (!input) return;

  // Click zone → trigger file input
  zoneEl.addEventListener('click', (e) => {
    if (e.target.tagName !== 'BUTTON') input.click();
  });

  // Drag-and-drop
  zoneEl.addEventListener('dragover', (e) => {
    e.preventDefault();
    zoneEl.classList.add('dragover');
  });
  zoneEl.addEventListener('dragleave', () => zoneEl.classList.remove('dragover'));
  zoneEl.addEventListener('drop', (e) => {
    e.preventDefault();
    zoneEl.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) handleFile(file);
  });

  // File input change
  input.addEventListener('change', () => {
    if (input.files[0]) handleFile(input.files[0]);
  });

  async function handleFile(file) {
    const resized = await resizeImage(file, maxW, maxH);
    // Replace file in the input (create new FileList)
    const dt = new DataTransfer();
    dt.items.add(resized);
    input.files = dt.files;

    // Show preview
    if (preview && previewImg) {
      previewImg.src = URL.createObjectURL(resized);
      preview.classList.add('show');
      zoneEl.querySelector('.upload-content').classList.add('hidden');
    }

    // Store dimensions as data attributes
    const tmpImg = new Image();
    tmpImg.onload = () => {
      zoneEl.dataset.imgW = tmpImg.naturalWidth;
      zoneEl.dataset.imgH = tmpImg.naturalHeight;
    };
    tmpImg.src = URL.createObjectURL(resized);
  }
}

// ── Camera: YouCam CameraKit with WebRTC Fallback ───────────
let cameraStream = null;

function openCamera() {
  if (window.YMK_READY && typeof YMK !== 'undefined' && YMK.openCameraKit) {
    try {
      console.log('[StyleAI] Opening YouCam CameraKit SDK');
      YMK.init({
        faceDetectionMode: 'makeup',
        imageFormat: 'base64',
        language: 'enu'
      });
      YMK.openCameraKit();
      return;
    } catch (e) {
      console.warn('[StyleAI] YouCam CameraKit error, falling back to WebRTC camera modal:', e);
    }
  }
  openWebRTCCamera();
}

async function openWebRTCCamera() {
  const modal = document.getElementById('camera-modal');
  const video = document.getElementById('camera-video');
  if (!modal || !video) return;

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('Camera is not supported on this browser or connection. Please use file upload instead.');
    return;
  }

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: 'user',
        width: { ideal: 1280, min: 640 },
        height: { ideal: 960, min: 480 },
      },
      audio: false
    });
    video.srcObject = cameraStream;
    await video.play();
    modal.style.display = 'flex';
  } catch (err) {
    console.error('[StyleAI Camera] Access failed:', err);
    alert('Could not access camera. Please allow camera permissions in your browser or select a photo.');
  }
}

function closeCamera() {
  const modal = document.getElementById('camera-modal');
  const video = document.getElementById('camera-video');
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
  if (video) video.srcObject = null;
  if (modal) modal.style.display = 'none';
}

function captureCameraPhoto() {
  const video = document.getElementById('camera-video');
  const canvas = document.getElementById('camera-canvas');
  if (!video || !canvas) return;

  const w = video.videoWidth || 640;
  const h = video.videoHeight || 480;
  canvas.width = w;
  canvas.height = h;

  const ctx = canvas.getContext('2d');
  // Mirror frame to match mirror preview
  ctx.translate(w, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(video, 0, 0, w, h);

  const dataUrl = canvas.toDataURL('image/jpeg', 0.95);

  canvas.toBlob((blob) => {
    if (!blob) return;
    const file = new File([blob], 'selfie_capture.jpg', { type: 'image/jpeg' });
    
    // 1. Inject into file input and previews in upload zone
    document.querySelectorAll('.upload-zone').forEach(zone => {
      const input = zone.querySelector('input[type="file"]');
      const preview = zone.querySelector('.upload-preview');
      const previewImg = preview ? preview.querySelector('img') : null;
      const placeholder = zone.querySelector('.upload-placeholder') || zone.querySelector('.upload-content');

      if (input) {
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
      }
      if (preview && previewImg) {
        previewImg.src = dataUrl;
        preview.classList.add('show');
        if (placeholder) placeholder.classList.add('hidden');
      }
    });

    // 2. Set all base64 hidden fields
    document.querySelectorAll('input[name="base64_image"], #base64-image-input, #base64_image').forEach(field => {
      field.value = dataUrl;
    });

    closeCamera();
  }, 'image/jpeg', 0.95);
}

// Global handler for YouCam CameraKit faceDetectionCaptured event
window.handleYouCamCapture = function(capturedResult) {
  if (!capturedResult || !capturedResult.images || capturedResult.images.length === 0) return;
  const item = capturedResult.images[0];
  if (typeof item.image === 'string') {
    setCapturedImage(item.image);
  } else {
    const reader = new FileReader();
    reader.onload = (e) => setCapturedImage(e.target.result);
    reader.readAsDataURL(item.image);
  }
};

function setCapturedImage(base64DataUrl) {
  // Store into base64 fields
  document.querySelectorAll('input[type="hidden"][name="base64_image"]').forEach(el => {
    el.value = base64DataUrl;
  });

  const uploadZone = document.querySelector('.upload-zone');
  if (uploadZone) {
    const preview = uploadZone.querySelector('.upload-preview');
    const previewImg = preview ? preview.querySelector('img') : null;
    const content = uploadZone.querySelector('.upload-content');
    if (preview && previewImg) {
      previewImg.src = base64DataUrl;
      preview.classList.add('show');
      if (content) content.classList.add('hidden');
    }
  }
}

// ── Flash auto-dismiss ───────────────────────────────────────
function setupFlash() {
  document.querySelectorAll('.flash').forEach(el => {
    el.addEventListener('click', () => el.remove());
    setTimeout(() => el.remove(), 5000);
  });
}

// ── HTMX indicator & error helpers ───────────────────────────
document.addEventListener('htmx:beforeRequest', (e) => {
  console.log('[StyleAI HTMX] Sending request to:', e.detail.pathInfo.requestPath);
  const btn = e.detail.elt.querySelector('[type="submit"]') || e.detail.elt;
  if (btn && btn.tagName === 'BUTTON') {
    btn.dataset.origText = btn.textContent;
    btn.textContent = 'Processing…';
    btn.disabled = true;
  }
});

document.addEventListener('htmx:afterRequest', (e) => {
  console.log('[StyleAI HTMX] Request completed:', e.detail.pathInfo.requestPath, 'Status:', e.detail.xhr.status);
  const btn = e.detail.elt.querySelector('[type="submit"]') || e.detail.elt;
  if (btn && btn.dataset && btn.dataset.origText) {
    btn.textContent = btn.dataset.origText;
    btn.disabled = false;
  }
});

document.addEventListener('htmx:responseError', (e) => {
  console.error('[StyleAI HTMX] Response error:', e.detail.xhr.status, e.detail.xhr.responseText);
  const target = e.detail.target;
  if (target) {
    target.innerHTML = `<div class="card" style="border-color:var(--c-error-fg); padding:var(--sp-4);">
      <p class="text-error" style="font-weight:600;">Request Error (${e.detail.xhr.status})</p>
      <p class="text-sm muted">${e.detail.xhr.responseText || 'Could not process request. Please try again.'}</p>
    </div>`;
  }
});

document.addEventListener('htmx:sendError', (e) => {
  console.error('[StyleAI HTMX] Network / Send error:', e.detail);
});

// ── Init ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Upload zones
  document.querySelectorAll('.upload-zone').forEach(setupUploadZone);

  // Flash messages
  setupFlash();

  // Camera buttons & modal listeners
  document.querySelectorAll('.camera-btn').forEach(btn => {
    btn.disabled = false;
    btn.textContent = '📷 Take Selfie';
    btn.addEventListener('click', openCamera);
  });

  const closeBtn = document.getElementById('camera-modal-close');
  if (closeBtn) closeBtn.addEventListener('click', closeCamera);

  const captureBtn = document.getElementById('camera-capture-btn');
  if (captureBtn) captureBtn.addEventListener('click', captureCameraPhoto);

  const modal = document.getElementById('camera-modal');
  // ── Global Modal Helpers ─────────────────────────────────
  window.openModal = function(id) {
    const m = document.getElementById(id);
    if (m) {
      m.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }
  };

  window.closeModal = function(id) {
    const m = document.getElementById(id);
    if (m) {
      m.style.display = 'none';
      document.body.style.overflow = '';
    }
  };

  // Close modals when clicking backdrop
  document.querySelectorAll('.brand-compare-modal, .modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
      }
    });
  });

  // ── Mobile Sidebar Drawer ──────────────────────────────────
  const toggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  const closeBtnNav = document.getElementById('sidebar-close-btn');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('open');
    if (backdrop) backdrop.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    if (backdrop) backdrop.classList.remove('show');
    document.body.style.overflow = '';
  }

  if (toggle) toggle.addEventListener('click', openSidebar);
  if (closeBtnNav) closeBtnNav.addEventListener('click', closeSidebar);
  if (backdrop) backdrop.addEventListener('click', closeSidebar);

  // Close drawer when clicking any link inside sidebar (for mobile)
  if (sidebar) {
    sidebar.querySelectorAll('.nav-item').forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 860) {
          closeSidebar();
        }
      });
    });
  }

  // Close with Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeSidebar();
      closeCamera();
      document.querySelectorAll('.brand-compare-modal, .camera-modal-backdrop').forEach(m => {
        m.style.display = 'none';
      });
      document.body.style.overflow = '';
    }
  });
});
