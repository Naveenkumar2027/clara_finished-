import { chromium, expect, test } from '@playwright/test';

const audioPath = process.env.REAL_REGIONAL_STT_AUDIO;
const language = process.env.REAL_REGIONAL_STT_LANGUAGE;
const physicalMicrophone = process.env.REAL_REGIONAL_STT_PHYSICAL === '1';
const browserChannel = process.env.REAL_REGIONAL_STT_CHANNEL === 'msedge' ? 'msedge' : 'chrome';

test('installed browser returns a real Web Speech transcript', async () => {
  test.skip(
    !language || (!audioPath && !physicalMicrophone),
    'Set REAL_REGIONAL_STT_LANGUAGE and either REAL_REGIONAL_STT_AUDIO or REAL_REGIONAL_STT_PHYSICAL=1',
  );
  test.setTimeout(90_000);

  const browser = await chromium.launch({
    channel: browserChannel,
    headless: false,
    args: [
      '--autoplay-policy=no-user-gesture-required',
      '--use-fake-ui-for-media-stream',
      ...(audioPath ? [`--use-file-for-fake-audio-capture=${audioPath}`] : []),
    ],
  });
  try {
    const context = await browser.newContext({ permissions: ['microphone'] });
    const page = await context.newPage();
    await page.goto('http://localhost:5176', { waitUntil: 'domcontentloaded' });

    const result = await page.evaluate(async (lang) => {
      const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognitionCtor) throw new Error('SpeechRecognition is unavailable in installed Chrome');
      return await new Promise<{ transcript: string; confidence: number | null }>((resolve, reject) => {
        const recognition = new SpeechRecognitionCtor();
        recognition.lang = lang;
        recognition.continuous = false;
        recognition.interimResults = false;
        const timeout = window.setTimeout(() => {
          recognition.abort();
          reject(new Error('Web Speech recognition timed out'));
        }, 60_000);
        recognition.onerror = (event) => {
          window.clearTimeout(timeout);
          reject(new Error(`Web Speech error: ${event.error}`));
        };
        recognition.onresult = (event) => {
          window.clearTimeout(timeout);
          const alternative = event.results[event.resultIndex]?.[0];
          resolve({
            transcript: alternative?.transcript?.trim() || '',
            confidence: Number.isFinite(alternative?.confidence) ? alternative.confidence : null,
          });
        };
        recognition.start();
      });
    }, language!);

    console.log(`REAL_REGIONAL_STT ${JSON.stringify({
      language,
      browserChannel,
      inputMode: physicalMicrophone ? 'physical_microphone' : 'provider_audio_capture',
      ...result,
    })}`);
    expect(result.transcript).not.toBe('');
  } finally {
    await browser.close();
  }
});
