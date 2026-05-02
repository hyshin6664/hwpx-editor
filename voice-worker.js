// Moonshine Tiny Korean ASR Worker — UI 스레드 안 막게 별도 worker 에서 추론
// 메인 스레드와는 postMessage 로 통신. 진행률/결과 모두 보고.

// transformers.js dynamic import (worker 내부)
let pipeline = null;
let env = null;
let transcriber = null;

const MODEL_ID = 'onnx-community/moonshine-tiny-ko-ONNX';

async function init(opts) {
  // opts: { device: 'webgpu'|'wasm', dtype: 'q4'|'q8'|'fp16' }
  if (transcriber) return { ok: true, cached: true };
  try {
    const mod = await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.5.0');
    pipeline = mod.pipeline;
    env = mod.env;
    // iOS WebGPU JSEP 메모리 폭증 회피 — 명시적으로 wasm 강제 옵션
    if (opts && opts.device === 'wasm') {
      env.backends.onnx.wasm.proxy = false;
      env.backends.onnx.wasm.numThreads = 1; // 메모리 절약
    }
    self.postMessage({ type: 'progress', stage: 'loading-model', pct: 0 });
    transcriber = await pipeline(
      'automatic-speech-recognition',
      MODEL_ID,
      {
        device: (opts && opts.device) || 'wasm',
        dtype: (opts && opts.dtype) || 'q8',
        progress_callback: (p) => {
          // p: { status, file, loaded, total, progress }
          if (p && p.status === 'progress' && p.progress != null) {
            self.postMessage({ type: 'progress', stage: 'downloading', file: p.file, pct: Math.round(p.progress) });
          } else if (p && p.status === 'ready') {
            self.postMessage({ type: 'progress', stage: 'ready', pct: 100 });
          }
        },
      }
    );
    self.postMessage({ type: 'init-done' });
    return { ok: true };
  } catch (e) {
    self.postMessage({ type: 'error', message: String(e && e.message || e) });
    return { ok: false, error: String(e) };
  }
}

async function transcribe(audioFloat32, opts) {
  // audioFloat32: Float32Array, 16kHz mono PCM
  // opts: { isFinal: bool, requestId: number }
  if (!transcriber) {
    self.postMessage({ type: 'error', message: 'transcriber not ready' });
    return;
  }
  try {
    const result = await transcriber(audioFloat32, {
      language: 'ko',
      task: 'transcribe',
      // chunked 처리 — 단일 청크
      return_timestamps: false,
    });
    self.postMessage({
      type: 'result',
      requestId: (opts && opts.requestId) || 0,
      isFinal: !!(opts && opts.isFinal),
      text: (result && result.text) || '',
    });
  } catch (e) {
    self.postMessage({ type: 'error', message: 'transcribe: ' + String(e && e.message || e), requestId: (opts && opts.requestId) || 0 });
  }
}

self.onmessage = async (e) => {
  const msg = e.data || {};
  if (msg.type === 'init') return init(msg.opts || {});
  if (msg.type === 'transcribe') return transcribe(msg.audio, { isFinal: msg.isFinal, requestId: msg.requestId });
  if (msg.type === 'reset') {
    transcriber = null;
    self.postMessage({ type: 'reset-done' });
  }
};
