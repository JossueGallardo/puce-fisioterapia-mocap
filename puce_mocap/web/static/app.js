const $ = (id) => document.getElementById(id);

const POSE_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 7], [0, 4], [4, 5], [5, 6], [6, 8],
  [9, 10], [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21],
  [17, 19], [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
  [11, 23], [12, 24], [23, 24], [23, 25], [24, 26], [25, 27], [26, 28],
  [27, 29], [28, 30], [29, 31], [30, 32], [27, 31], [28, 32],
];

let appInfo = null;
let currentState = null;
let selectedModule = "weights";
let hydratedModule = null;
let mediaStream = null;
let cameraLoopRunning = false;
let frameInFlight = false;
let lastFrameSentAt = 0;
let sourcePanel = "camera";

async function jsonRequest(path, payload = undefined) {
  const options = payload === undefined
    ? { method: "POST" }
    : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      };
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "No se pudo completar la acción.");
  }
  return data.state || data;
}

async function fetchState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("No se pudo obtener el estado del servidor.");
  }
  return response.json();
}

function setStatus(message, type = "normal") {
  $("status-text").textContent = message;
  $("status-dot").classList.toggle("live", type === "live");
  $("status-dot").classList.toggle("error", type === "error");
}

function updateMetrics(state) {
  const container = $("metrics");
  container.replaceChildren();
  state.metrics.forEach((metric) => {
    const item = document.createElement("div");
    item.className = "metric";
    const label = document.createElement("span");
    const value = document.createElement("strong");
    label.textContent = metric.label;
    value.textContent = metric.value;
    item.append(label, value);
    container.appendChild(item);
  });
}

function fillSelect(select, values, selected) {
  select.replaceChildren();
  values.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.key || item;
    option.textContent = item.label || item;
    option.selected = option.value === selected;
    select.appendChild(option);
  });
}

function hydrateWeights(state) {
  const weights = state.weights;
  fillSelect($("weights-exercise"), appInfo.weight_exercises, weights.exercise);
  $("weights-name").value = weights.patient.nombre_paciente;
  $("weights-code").value = weights.patient.codigo_paciente;
  $("weights-condition").value = weights.patient.lesion;
  $("weights-notes").value = weights.patient.observaciones_paciente;
  const ranges = weights.definitions[weights.exercise];
  $("weights-start-min").value = ranges.start_min;
  $("weights-start-max").value = ranges.start_max;
  $("weights-target-min").value = ranges.target_min;
  $("weights-target-max").value = ranges.target_max;
}

function hydrateRehab(state) {
  const rehab = state.rehab;
  fillSelect($("rehab-exercise"), appInfo.rehab_exercises, rehab.exercise);
  const profile = rehab.profile;
  $("rehab-name").value = profile.nombre;
  $("rehab-code").value = profile.codigo_paciente;
  $("rehab-injury").value = profile.lesion;
  $("rehab-notes").value = profile.observaciones;
  const config = profile.ejercicios[rehab.exercise];
  $("rehab-start-min").value = config.rango_inicio.minimo;
  $("rehab-start-max").value = config.rango_inicio.maximo;
  $("rehab-target-min").value = config.rango_objetivo.minimo;
  $("rehab-target-max").value = config.rango_objetivo.maximo;
  $("rehab-repetitions").value = config.repeticiones_objetivo;
  $("rehab-side").value = config.lado;
}

function hydrateGait(state) {
  $("gait-view").value = state.gait.view;
}

function hydrateForms(state, force = false) {
  if (!force && hydratedModule === state.module) {
    return;
  }
  hydrateWeights(state);
  hydrateRehab(state);
  hydrateGait(state);
  hydratedModule = state.module;
}

function moduleRecording(state) {
  if (state.module === "weights") return state.weights.recording;
  if (state.module === "rehab") return state.rehab.recording;
  return state.gait.recording;
}

function updateModuleVisibility(state) {
  selectedModule = state.module;
  $("weights-controls").hidden = state.module !== "weights";
  $("rehab-controls").hidden = state.module !== "rehab";
  $("gait-controls").hidden = state.module !== "gait";
  document.querySelectorAll(".module-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.module === state.module);
  });

  const titles = {
    weights: "Ejercicios con pesas",
    rehab: "Rehabilitación",
    gait: "Análisis de marcha",
  };
  $("module-title").textContent = titles[state.module];

  const recording = moduleRecording(state);
  $("recording-state").textContent = recording ? "Registrando" : "En espera";
  $("recording-state").classList.toggle("live", recording);
}

function updateAnalysisContext(state) {
  const stage = $("motion-stage");
  const guide = $("view-guide");
  let badge = "";
  let guideMode = "none";
  let guideLabel = "";

  if (state.module === "weights") {
    badge = `Pesas · ${state.weights.exercise}`;
    if (state.weights.exercise === "Peso muerto") {
      guideMode = "lateral";
      guideLabel = "Perfil lateral recomendado";
    }
  } else if (state.module === "rehab") {
    const exercise = appInfo.rehab_exercises.find((item) => item.key === state.rehab.exercise);
    const configuredSide = state.rehab.profile.ejercicios[state.rehab.exercise].lado;
    const evaluatedSide = state.rehab.evaluated_side;
    const side = evaluatedSide === "left"
      ? "izquierda"
      : evaluatedSide === "right"
        ? "derecha"
        : configuredSide === "left"
          ? "izquierda"
          : configuredSide === "right"
            ? "derecha"
            : "automática";
    badge = `Rehabilitación · ${exercise ? exercise.label : state.rehab.exercise} · extremidad ${side}`;
    const frontal = exercise?.orientation !== "lateral";
    guideMode = frontal ? "frontal" : "lateral";
    guideLabel = frontal
      ? "Mire de frente y mantenga visible la extremidad evaluada"
      : "Use una vista lateral u oblicua sin ocultar la extremidad evaluada";
    $("rehab-guidance").textContent = frontal
      ? "Colóquese de frente a la cámara. El selector indica la extremidad analizada, no la orientación corporal."
      : "Coloque la cámara de lado u oblicua para medir mejor la articulación. Puede elegir cualquiera de las dos extremidades.";
    $("rehab-calibrate").hidden = state.rehab.exercise !== "rotacion_muneca";
  } else {
    const frontal = state.gait.view === "Frontal";
    badge = `Caminadora · vista ${frontal ? "frontal" : "lateral"}`;
    guideMode = frontal ? "frontal" : "lateral";
    guideLabel = frontal ? "Alinee el cuerpo con el centro" : "Mantenga pies y cabeza en el encuadre";
    $("gait-guidance").textContent = frontal
      ? "Coloque la cámara frente a la caminadora y mantenga ambos lados del cuerpo visibles."
      : "Coloque la cámara a un costado y mantenga el cuerpo completo dentro del encuadre.";
  }

  $("analysis-badge").textContent = badge;
  stage.dataset.guide = guideMode;
  guide.hidden = guideMode === "none";
  $("view-guide-label").textContent = guideLabel;
}

function clearOverlay() {
  const canvas = $("pose-overlay");
  canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
}

function drawPose(visualization) {
  if (!visualization || !visualization.detected || !visualization.landmarks?.length) {
    clearOverlay();
    return;
  }

  const canvas = $("pose-overlay");
  const video = $("camera-video");
  const cameraMode = currentState?.source.mode === "browser_camera";
  canvas.width = cameraMode && video.videoWidth ? video.videoWidth : 960;
  canvas.height = cameraMode && video.videoHeight ? video.videoHeight : 540;
  canvas.classList.toggle("mirrored", cameraMode);
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.lineWidth = Math.max(2, canvas.width / 360);
  context.lineCap = "round";
  context.strokeStyle = "#68d5c2";

  POSE_CONNECTIONS.forEach(([from, to]) => {
    const a = visualization.landmarks[from];
    const b = visualization.landmarks[to];
    if (!a || !b || a.visibility < 0.5 || b.visibility < 0.5) return;
    context.beginPath();
    context.moveTo(a.x * canvas.width, a.y * canvas.height);
    context.lineTo(b.x * canvas.width, b.y * canvas.height);
    context.stroke();
  });

  const configuredSide = selectedModule === "rehab" ? $("rehab-side").value : null;
  const selectedSide = configuredSide === "auto"
    ? currentState?.rehab.evaluated_side || null
    : configuredSide;
  visualization.landmarks.forEach((landmark, index) => {
    if (landmark.visibility < 0.5) return;
    const isLeft = index >= 11 && index % 2 === 1;
    const isRight = index >= 12 && index % 2 === 0;
    const highlighted = !selectedSide
      || (selectedSide === "left" && isLeft)
      || (selectedSide === "right" && isRight)
      || index < 11;
    context.fillStyle = highlighted ? "#f1c95b" : "rgba(255, 255, 255, 0.45)";
    context.beginPath();
    context.arc(
      landmark.x * canvas.width,
      landmark.y * canvas.height,
      highlighted ? Math.max(3, canvas.width / 240) : Math.max(2, canvas.width / 320),
      0,
      Math.PI * 2,
    );
    context.fill();
  });
}

function updateSource(state) {
  const source = state.source;
  const video = $("camera-video");
  const placeholder = $("video-placeholder");
  const timeline = $("session-timeline");
  const cameraMode = source.mode === "browser_camera" && source.camera_active && mediaStream;
  const sessionMode = source.mode === "freemocap" && source.freemocap;

  video.hidden = !cameraMode;
  placeholder.hidden = cameraMode || sessionMode;
  timeline.hidden = !sessionMode;
  $("camera-stop").disabled = !cameraMode;

  if (cameraMode) {
    $("source-badge").textContent = source.camera.label || "Cámara del navegador";
    $("processing-indicator").hidden = false;
    return;
  }

  $("processing-indicator").hidden = true;
  if (sessionMode) {
    const info = source.freemocap;
    $("source-badge").textContent = "Sesión FreeMoCap";
    $("session-filename").textContent = info.filename;
    $("session-summary").textContent = `Fotograma ${info.frame_index + 1} de ${info.frame_count} · ${info.length_unit}`;
    $("frame-slider").max = Math.max(0, info.frame_count - 1);
    $("frame-slider").value = info.frame_index;
    drawPose(state.visualization);
    return;
  }

  $("source-badge").textContent = "Fuente inactiva";
  clearOverlay();
}

function renderState(state, forceHydrate = false) {
  currentState = state;
  updateModuleVisibility(state);
  updateMetrics(state);
  hydrateForms(state, forceHydrate);
  updateAnalysisContext(state);
  updateSource(state);
  setStatus(state.status, moduleRecording(state) ? "live" : "normal");
  const report = state.last_report;
  $("report-download").hidden = !report?.available;
  if (report?.available) {
    $("report-download").textContent = `Descargar ${report.filename}`;
  }
}

function weightsPayload() {
  return {
    exercise: $("weights-exercise").value,
    patient: {
      nombre_paciente: $("weights-name").value,
      codigo_paciente: $("weights-code").value,
      lesion: $("weights-condition").value,
      observaciones_paciente: $("weights-notes").value,
    },
    ranges: {
      start_min: Number($("weights-start-min").value),
      start_max: Number($("weights-start-max").value),
      target_min: Number($("weights-target-min").value),
      target_max: Number($("weights-target-max").value),
    },
  };
}

function rehabPayload() {
  return {
    exercise: $("rehab-exercise").value,
    patient: {
      nombre: $("rehab-name").value,
      codigo_paciente: $("rehab-code").value,
      lesion: $("rehab-injury").value,
      observaciones: $("rehab-notes").value,
    },
    config: {
      rango_inicio: {
        minimo: Number($("rehab-start-min").value),
        maximo: Number($("rehab-start-max").value),
      },
      rango_objetivo: {
        minimo: Number($("rehab-target-min").value),
        maximo: Number($("rehab-target-max").value),
      },
      lado: $("rehab-side").value,
      repeticiones_objetivo: Number($("rehab-repetitions").value),
    },
  };
}

async function run(path, payload = undefined, forceHydrate = false) {
  try {
    renderState(await jsonRequest(path, payload), forceHydrate);
  } catch (error) {
    try {
      renderState(await fetchState(), true);
    } catch (_stateError) {
      // Se conserva el error original de la acción.
    }
    setStatus(error.message, "error");
  }
}

function selectSourcePanel(panel) {
  sourcePanel = panel;
  const camera = panel === "camera";
  $("source-camera-tab").classList.toggle("active", camera);
  $("source-session-tab").classList.toggle("active", !camera);
  $("camera-source-controls").hidden = !camera;
  $("session-source-controls").hidden = camera;
}

async function populateCameraDevices(selectedId = "") {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const cameras = devices.filter((device) => device.kind === "videoinput");
  const select = $("camera-device");
  select.replaceChildren();
  cameras.forEach((camera, index) => {
    const option = document.createElement("option");
    option.value = camera.deviceId;
    option.textContent = camera.label || `Cámara ${index + 1}`;
    option.selected = camera.deviceId === selectedId;
    select.appendChild(option);
  });
  if (!cameras.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Cámara predeterminada";
    select.appendChild(option);
  }
}

function stopMediaTracks() {
  cameraLoopRunning = false;
  frameInFlight = false;
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
  $("camera-video").srcObject = null;
}

async function startBrowserCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Este navegador no permite acceder a la cámara. En un VPS debe usar HTTPS.");
  }
  stopMediaTracks();
  const [width, height] = $("camera-resolution").value.split("x").map(Number);
  const deviceId = $("camera-device").value;
  const constraints = {
    audio: false,
    video: {
      width: { ideal: width },
      height: { ideal: height },
      facingMode: "user",
      ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
    },
  };
  mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
  const video = $("camera-video");
  video.srcObject = mediaStream;
  await new Promise((resolve) => {
    if (video.readyState >= 1) resolve();
    else video.onloadedmetadata = resolve;
  });
  await video.play();
  const track = mediaStream.getVideoTracks()[0];
  const settings = track.getSettings();
  await populateCameraDevices(settings.deviceId || deviceId);
  const state = await jsonRequest("/api/source/camera/start", {
    device_label: track.label || "Cámara del navegador",
    width: settings.width || width,
    height: settings.height || height,
  });
  renderState(state);
  $("motion-stage").style.aspectRatio = `${settings.width || width} / ${settings.height || height}`;
  cameraLoopRunning = true;
  lastFrameSentAt = 0;
  window.requestAnimationFrame(cameraLoop);
}

async function stopBrowserCamera() {
  stopMediaTracks();
  renderState(await jsonRequest("/api/source/camera/stop"));
}

function cameraLoop(timestamp) {
  if (!cameraLoopRunning) return;
  if (!frameInFlight && timestamp - lastFrameSentAt >= 120) {
    lastFrameSentAt = timestamp;
    frameInFlight = true;
    sendCameraFrame()
      .catch((error) => setStatus(error.message, "error"))
      .finally(() => {
        frameInFlight = false;
      });
  }
  window.requestAnimationFrame(cameraLoop);
}

async function sendCameraFrame() {
  const video = $("camera-video");
  if (!video.videoWidth || !video.videoHeight) return;
  const canvas = $("capture-canvas");
  const targetWidth = Math.min(640, video.videoWidth);
  const targetHeight = Math.round(targetWidth * video.videoHeight / video.videoWidth);
  canvas.width = targetWidth;
  canvas.height = targetHeight;
  canvas.getContext("2d").drawImage(video, 0, 0, targetWidth, targetHeight);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.72));
  if (!blob) return;
  const response = await fetch("/api/source/camera/frame", {
    method: "POST",
    headers: { "Content-Type": "image/jpeg" },
    body: blob,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "No se pudo analizar el fotograma.");
  }
  renderState(data.state);
  drawPose(data.visualization);
  $("processing-indicator").textContent = data.visualization.detected
    ? `Análisis ${Math.round(data.visualization.processing_ms)} ms`
    : "Buscando postura";
}

async function uploadFreemocap() {
  const file = $("freemocap-file").files[0];
  if (!file) throw new Error("Seleccione un archivo *_body_3d_xyz.npy.");
  setStatus(`Cargando ${file.name}...`, "live");
  const params = new URLSearchParams({
    filename: file.name,
    unit: $("freemocap-unit").value,
  });
  const response = await fetch(`/api/source/freemocap/upload?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: file,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "No se pudo cargar la sesión.");
  stopMediaTracks();
  renderState(data.state, true);
}

async function uploadRehabProfile() {
  const file = $("rehab-profile-file").files[0];
  if (!file) return;
  const response = await fetch("/api/rehab/profile/upload", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: file,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "No se pudo importar el perfil.");
  renderState(data.state, true);
}

function bindEvents() {
  document.querySelectorAll(".module-tab").forEach((button) => {
    button.addEventListener("click", () => run("/api/module", { module: button.dataset.module }, true));
  });

  $("source-camera-tab").addEventListener("click", () => selectSourcePanel("camera"));
  $("source-session-tab").addEventListener("click", () => selectSourcePanel("session"));
  $("camera-start").addEventListener("click", () => {
    startBrowserCamera().catch((error) => setStatus(error.message, "error"));
  });
  $("camera-stop").addEventListener("click", () => {
    stopBrowserCamera().catch((error) => setStatus(error.message, "error"));
  });
  $("freemocap-file").addEventListener("change", () => {
    const file = $("freemocap-file").files[0];
    $("freemocap-load").disabled = !file;
    if (file) setStatus(`Archivo seleccionado: ${file.name}`);
  });
  $("freemocap-load").addEventListener("click", () => {
    uploadFreemocap().catch((error) => setStatus(error.message, "error"));
  });
  $("frame-slider").addEventListener("input", () => {
    run("/api/source/freemocap/frame", { index: Number($("frame-slider").value) });
  });

  $("weights-exercise").addEventListener("change", () => {
    run("/api/weights/configure", { exercise: $("weights-exercise").value }, true);
  });
  $("weights-configure").addEventListener("click", () => run("/api/weights/configure", weightsPayload(), true));
  $("weights-start").addEventListener("click", () => run("/api/weights/start", weightsPayload()));
  $("weights-pause").addEventListener("click", () => run("/api/weights/pause"));
  $("weights-reset").addEventListener("click", () => run("/api/weights/reset", undefined, true));
  $("weights-save").addEventListener("click", () => run("/api/weights/save", undefined, true));

  $("rehab-exercise").addEventListener("change", () => {
    run("/api/rehab/configure", { exercise: $("rehab-exercise").value }, true);
  });
  $("rehab-side").addEventListener("change", () => run("/api/rehab/configure", rehabPayload(), true));
  $("rehab-configure").addEventListener("click", () => run("/api/rehab/configure", rehabPayload(), true));
  $("rehab-calibrate").addEventListener("click", () => run("/api/rehab/calibrate-wrist"));
  $("rehab-start").addEventListener("click", () => run("/api/rehab/start", rehabPayload()));
  $("rehab-pause").addEventListener("click", () => run("/api/rehab/pause"));
  $("rehab-reset").addEventListener("click", () => run("/api/rehab/reset", undefined, true));
  $("rehab-save").addEventListener("click", () => run("/api/rehab/save", undefined, true));
  $("rehab-profile-file").addEventListener("change", () => {
    uploadRehabProfile().catch((error) => setStatus(error.message, "error"));
  });

  $("gait-view").addEventListener("change", () => {
    run("/api/gait/configure", { view: $("gait-view").value }, true);
  });
  $("gait-start").addEventListener("click", () => run("/api/gait/start"));
  $("gait-stop").addEventListener("click", () => run("/api/gait/stop"));
  $("gait-reset").addEventListener("click", () => run("/api/gait/reset", undefined, true));

  window.addEventListener("beforeunload", stopMediaTracks);
}

async function boot() {
  appInfo = await fetch("/api/app-info", { cache: "no-store" }).then((response) => response.json());
  bindEvents();
  selectSourcePanel(sourcePanel);
  if (navigator.mediaDevices?.enumerateDevices) {
    populateCameraDevices().catch(() => {});
  }
  renderState(await fetchState(), true);
  window.setInterval(async () => {
    if (frameInFlight) return;
    try {
      renderState(await fetchState());
    } catch (error) {
      setStatus(error.message, "error");
    }
  }, 1500);
}

boot().catch((error) => setStatus(error.message, "error"));
