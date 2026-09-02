import React, { useEffect, useRef } from 'react';

export interface HorizontalVoiceAnalyserProps {
  isListening: boolean;
  amplitude: number; // 0 to 1 normalized visual amplitude
  frequencyDataRef?: React.RefObject<Uint8Array | null>;
  compact?: boolean;
  width?: number;
  height?: number;
  className?: string;
  style?: React.CSSProperties;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * Smooth bell curve function for fluid lobe shaping.
 */
function gaussianBell(x: number, center: number, sigma: number): number {
  const d = (x - center) / sigma;
  return Math.exp(-0.5 * d * d);
}

/**
 * Hann window for clean tapering at the line ends.
 */
function windowEnvelope(xNormalized: number): number {
  const x = Math.max(0, Math.min(1, xNormalized));
  return Math.sin(Math.PI * x);
}

export default function HorizontalVoiceAnalyser({
  isListening,
  amplitude,
  frequencyDataRef,
  compact = false,
  width: propWidth,
  height: propHeight,
  className = '',
  style,
}: HorizontalVoiceAnalyserProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number>(0);

  // Morph transition state (0 = orb circle of radius 63px, 1 = full horizontal wave ribbon)
  const morphProgressRef = useRef<number>(isListening ? 1 : 0);
  const smoothedAmpRef = useRef<number>(0);
  const phaseRef = useRef<number>(0);
  const smoothedBinsRef = useRef<Float32Array>(new Float32Array(32));

  // Frequency bands (low, mid, high) smoothed values
  const lowEnergyRef = useRef<number>(0);
  const midEnergyRef = useRef<number>(0);
  const highEnergyRef = useRef<number>(0);

  const targetWidth = propWidth ?? (compact ? 290 : 420);
  const targetHeight = propHeight ?? (compact ? 120 : 160);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    let lastTime = performance.now();

    const render = (now: number) => {
      const dt = Math.min((now - lastTime) / 1000, 0.05);
      lastTime = now;

      // ─── 1. Ultra-Smooth Morph Transition (~520ms) ───
      const targetMorph = isListening ? 1.0 : 0.0;
      const morphSpeed = 2.4; // ~520ms organic uncurling transition
      if (morphProgressRef.current < targetMorph) {
        morphProgressRef.current = Math.min(targetMorph, morphProgressRef.current + dt * morphSpeed);
      } else if (morphProgressRef.current > targetMorph) {
        morphProgressRef.current = Math.max(targetMorph, morphProgressRef.current - dt * morphSpeed);
      }
      const morph = morphProgressRef.current;

      // ─── 2. High-DPI Canvas Sizing ───
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const displayWidth = targetWidth;
      const displayHeight = targetHeight;

      if (canvas.width !== displayWidth * dpr || canvas.height !== displayHeight * dpr) {
        canvas.width = displayWidth * dpr;
        canvas.height = displayHeight * dpr;
        canvas.style.width = `${displayWidth}px`;
        canvas.style.height = `${displayHeight}px`;
      }

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, displayWidth, displayHeight);

      if (morph < 0.002) {
        ctx.restore();
        animFrameRef.current = requestAnimationFrame(render);
        return;
      }

      // ─── 3. Real-Time Audio Processing ───
      const rawAmp = Math.max(0, Math.min(1, amplitude));
      smoothedAmpRef.current = lerp(smoothedAmpRef.current, rawAmp, 0.24);
      const amp = smoothedAmpRef.current;

      phaseRef.current += dt * (1.8 + amp * 4.2);
      const phase = phaseRef.current;

      const freqData = frequencyDataRef?.current;
      const bins = smoothedBinsRef.current;
      const numBins = bins.length;

      let rawLow = 0;
      let rawMid = 0;
      let rawHigh = 0;

      if (freqData && freqData.length > 0) {
        const step = Math.floor(freqData.length / numBins);
        for (let b = 0; b < numBins; b++) {
          const idx = Math.min(b * step, freqData.length - 1);
          const val = freqData[idx] / 255;
          bins[b] = lerp(bins[b], val, 0.28);
          if (b < 8) rawLow += val;
          else if (b < 20) rawMid += val;
          else rawHigh += val;
        }
        rawLow /= 8;
        rawMid /= 12;
        rawHigh /= (numBins - 20);
      } else {
        for (let b = 0; b < numBins; b++) {
          const s = Math.sin(phase * 1.6 + b * 0.25) * 0.5 + 0.5;
          bins[b] = lerp(bins[b], s * (0.12 + amp * 0.6), 0.12);
        }
        rawLow = 0.15 + amp * 0.6;
        rawMid = 0.12 + amp * 0.5;
        rawHigh = 0.08 + amp * 0.4;
      }

      lowEnergyRef.current = lerp(lowEnergyRef.current, rawLow, 0.22);
      midEnergyRef.current = lerp(midEnergyRef.current, rawMid, 0.22);
      highEnergyRef.current = lerp(highEnergyRef.current, rawHigh, 0.22);

      const lowEnergy = lowEnergyRef.current;
      const midEnergy = midEnergyRef.current;
      const highEnergy = highEnergyRef.current;

      // ─── 4. Uncurling Circular Thread / Arc Mathematics ───
      const cx = displayWidth / 2;
      const cy = displayHeight / 2;

      // Orb radius is exactly 63px (126px diameter)
      const orbRadius = 63;
      const fullHalfSpan = (displayWidth - 20) / 2; // e.g. ~200px
      const numPoints = 140;

      // Morph ease curve (smooth ease-in-out unrolling)
      const m = Math.sin(morph * Math.PI * 0.5);

      // Voice expansion heights
      const maxPeak = compact ? 36 : 48;
      const baseHeight = 1.8 + Math.sin(phase * 2.0) * 0.5;

      const centerLobeHeight = (baseHeight + (lowEnergy * 0.7 + amp * 0.7) * maxPeak) * m;
      const midLobeHeight = (baseHeight + (midEnergy * 0.65 + amp * 0.55) * (maxPeak * 0.78)) * m;
      const outerLobeHeight = (baseHeight + (highEnergy * 0.5 + amp * 0.45) * (maxPeak * 0.52)) * m;

      // Uncurling position function for normalized coordinate u in [0, 1]:
      // At m = 0: Forms a circle of radius orbRadius = 63px.
      // At m = 1: Uncurves straight to horizontal span [-fullHalfSpan, +fullHalfSpan].
      const computeUncurledPoint = (
        u: number,
        hTop: number,
        hBottom: number
      ): { top: [number, number]; bottom: [number, number] } => {
        const theta = (u - 0.5) * Math.PI; // -pi/2 to +pi/2
        const straightX = (u - 0.5) * (fullHalfSpan * 2);
        const circleX = orbRadius * Math.sin(theta);
        const px = cx + lerp(circleX, straightX, m);

        // Circular arc height: at center u=0.5, arcHeight = orbRadius (63px); at tips u=0 or 1, arcHeight = 0.
        const arcY = (1 - m) * orbRadius * Math.cos(theta);

        const pyTop = cy - arcY - hTop;
        const pyBottom = cy + arcY + hBottom;

        return { top: [px, pyTop], bottom: [px, pyBottom] };
      };

      // ─── 5. Lobe Displacement Functions ───
      const computeLobeDisplacement = (
        u: number,
        lobeCenter: number,
        lobeSigma: number,
        lobeHeight: number,
        phaseOffset: number
      ) => {
        const bell = gaussianBell(u, lobeCenter, lobeSigma);
        const ripple = 1.0 + 0.1 * Math.sin(phase * 2.4 + phaseOffset + u * Math.PI * 4);
        const env = windowEnvelope(u);
        return lobeHeight * bell * ripple * env;
      };

      // ─── 6. Helper to Draw a Solid Translucent Fluid Lobe Body ───
      const drawFluidLobe = (
        lobeCenter: number,
        lobeSigma: number,
        lobeHeight: number,
        fillColor: string,
        strokeColor: string,
        glowColor: string,
        glowBlur: number,
        phaseOffset = 0,
        topAsymmetry = 1.0,
        bottomAsymmetry = 1.0
      ) => {
        ctx.save();
        ctx.fillStyle = fillColor;
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 1.5;
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = glowBlur * m;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';

        // Top points (left to right)
        ctx.beginPath();
        for (let i = 0; i < numPoints; i++) {
          const u = i / (numPoints - 1);
          const hTop = computeLobeDisplacement(u, lobeCenter, lobeSigma, lobeHeight, phaseOffset) * topAsymmetry;
          const { top } = computeUncurledPoint(u, hTop, 0);

          if (i === 0) ctx.moveTo(top[0], top[1]);
          else ctx.lineTo(top[0], top[1]);
        }

        // Bottom points (right to left)
        for (let i = numPoints - 1; i >= 0; i--) {
          const u = i / (numPoints - 1);
          const hBottom = computeLobeDisplacement(u, lobeCenter, lobeSigma, lobeHeight, phaseOffset + Math.PI * 0.3) * bottomAsymmetry;
          const { bottom } = computeUncurledPoint(u, 0, hBottom);

          ctx.lineTo(bottom[0], bottom[1]);
        }

        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.restore();
      };

      // ─── 7. Render Layer 1: Outer Violet/Purple Wings (Tails) ───
      drawFluidLobe(
        0.18,
        0.12,
        outerLobeHeight * 0.9,
        'rgba(147, 51, 234, 0.65)',
        'rgba(168, 85, 247, 0.9)',
        'rgba(147, 51, 234, 0.5)',
        8,
        0.8,
        0.95,
        0.9
      );
      drawFluidLobe(
        0.82,
        0.12,
        outerLobeHeight * 0.9,
        'rgba(147, 51, 234, 0.65)',
        'rgba(168, 85, 247, 0.9)',
        'rgba(147, 51, 234, 0.5)',
        8,
        1.6,
        0.9,
        0.95
      );

      // ─── 8. Render Layer 2: Mid Royal Blue / Indigo Lobes ───
      drawFluidLobe(
        0.34,
        0.11,
        midLobeHeight,
        'rgba(67, 56, 202, 0.75)',
        'rgba(79, 70, 229, 0.95)',
        'rgba(59, 130, 246, 0.6)',
        12,
        0.4,
        1.05,
        0.95
      );
      drawFluidLobe(
        0.66,
        0.11,
        midLobeHeight,
        'rgba(67, 56, 202, 0.75)',
        'rgba(79, 70, 229, 0.95)',
        'rgba(59, 130, 246, 0.6)',
        12,
        1.2,
        0.95,
        1.05
      );

      // ─── 9. Render Layer 3: Central Cyan / Bright Turquoise Dominant Peak ───
      drawFluidLobe(
        0.50,
        0.10,
        centerLobeHeight,
        'rgba(6, 182, 212, 0.88)',
        'rgba(34, 211, 238, 1.0)',
        'rgba(6, 182, 212, 0.8)',
        16,
        0.0,
        1.0,
        1.0
      );

      // ─── 10. Render Layer 4: Inner Glowing Translucent Highlight (Core Light) ───
      drawFluidLobe(
        0.50,
        0.065,
        centerLobeHeight * 0.6,
        'rgba(165, 243, 252, 0.65)',
        'rgba(255, 255, 255, 0.95)',
        'rgba(255, 255, 255, 0.8)',
        10,
        0.2,
        0.95,
        0.95
      );

      // ─── 11. Render Layer 5: Uncurling Luminous Spine / Baseline Thread ───
      ctx.save();
      const startX = cx - (lerp(orbRadius, fullHalfSpan, m));
      const endX = cx + (lerp(orbRadius, fullHalfSpan, m));
      const lineGrad = ctx.createLinearGradient(startX, 0, endX, 0);
      lineGrad.addColorStop(0, 'rgba(147, 51, 234, 0)');
      lineGrad.addColorStop(0.12, 'rgba(147, 51, 234, 0.95)');
      lineGrad.addColorStop(0.32, 'rgba(79, 70, 229, 0.95)');
      lineGrad.addColorStop(0.50, 'rgba(255, 255, 255, 1.0)');
      lineGrad.addColorStop(0.68, 'rgba(79, 70, 229, 0.95)');
      lineGrad.addColorStop(0.88, 'rgba(147, 51, 234, 0.95)');
      lineGrad.addColorStop(1, 'rgba(147, 51, 234, 0)');

      ctx.strokeStyle = lineGrad;
      ctx.shadowColor = 'rgba(34, 211, 238, 0.9)';
      ctx.shadowBlur = 8 * m;
      ctx.lineWidth = lerp(1.5, 2.2, m);
      ctx.lineCap = 'round';

      ctx.beginPath();
      for (let i = 0; i < numPoints; i++) {
        const u = i / (numPoints - 1);
        const { top, bottom } = computeUncurledPoint(u, 0, 0);
        const midY = (top[1] + bottom[1]) / 2;

        if (i === 0) ctx.moveTo(top[0], midY);
        else ctx.lineTo(top[0], midY);
      }
      ctx.stroke();
      ctx.restore();

      ctx.restore();
      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [isListening, amplitude, frequencyDataRef, targetWidth, targetHeight, compact]);

  return (
    <div
      className={`relative flex items-center justify-center pointer-events-none ${className}`}
      style={{
        width: targetWidth,
        height: targetHeight,
        ...style,
      }}
      aria-hidden="true"
    >
      <canvas
        ref={canvasRef}
        className="block pointer-events-none"
        style={{
          width: targetWidth,
          height: targetHeight,
        }}
      />
    </div>
  );
}
