import { expect, test, type Page } from '@playwright/test';

type RegionalCase = {
  language: 'telugu' | 'malayalam';
  sttCode: 'te-IN' | 'ml-IN';
  single: string;
  mixedSingle: string;
  multiHod: string;
  mixed: string;
  next: string;
  previous: string;
  reset: string;
  overview: string;
  followHod: string;
  followFaculty: string;
  replacement: string;
  principal: string;
  admissions: string;
  location: string;
  missingHod: string;
  missingDepartmentReply: string;
  offTopicReply: string;
  script: RegExp;
};

const CASES: RegionalCase[] = [
  {
    language: 'telugu',
    sttCode: 'te-IN',
    single: 'డేటా సైన్స్ HOD ఎవరు?',
    mixedSingle: 'data science HOD ఎవరు?',
    multiHod: 'CSE HOD మరియు Data Science HOD ఎవరు?',
    mixed: 'CSE HOD మరియు Data Science fees చూపించు',
    next: 'తర్వాత',
    previous: 'వెనక్కి',
    reset: 'ECE fees చూపించు',
    overview: 'డేటా సైన్స్ డిపార్ట్మెంట్ చూపించు',
    followHod: 'HOD కూడా',
    followFaculty: 'faculty కూడా',
    replacement: 'ECE HOD చూపించు',
    principal: 'ప్రిన్సిపాల్ ఎవరు?',
    admissions: 'ప్రవేశాల వివరాలు చూపించు',
    location: 'కాలేజీ ఎక్కడ ఉంది?',
    missingHod: 'HOD ఎవరు?',
    missingDepartmentReply: 'మీరు ఏ విభాగం గురించి తెలుసుకోవాలనుకుంటున్నారు?',
    offTopicReply: 'అది నేను సహాయం చేయగల పరిధికి వెలుపల ఉంది.',
    script: /[\u0C00-\u0C7F]/,
  },
  {
    language: 'malayalam',
    sttCode: 'ml-IN',
    single: 'ഡാറ്റ സയൻസ് HOD ആരാണ്?',
    mixedSingle: 'data science HOD ആരാണ്?',
    multiHod: 'CSE HOD ഉം Data Science HOD ഉം ആരാണ്?',
    mixed: 'CSE HOD ഉം Data Science fees ഉം കാണിക്കൂ',
    next: 'മുന്നോട്ട്',
    previous: 'പിന്നോട്ട്',
    reset: 'ECE fees കാണിക്കൂ',
    overview: 'ഡാറ്റ സയൻസ് ഡിപ്പാർട്ട്മെന്റ് കാണിക്കൂ',
    followHod: 'HOD കൂടി',
    followFaculty: 'faculty കൂടി',
    replacement: 'ECE HOD കാണിക്കൂ',
    principal: 'പ്രിൻസിപ്പൽ ആരാണ്?',
    admissions: 'പ്രവേശന വിവരങ്ങൾ കാണിക്കൂ',
    location: 'കോളേജ് എവിടെയാണ്?',
    missingHod: 'HOD ആരാണ്?',
    missingDepartmentReply: 'നിങ്ങൾക്ക് ഏത് ഡിപ്പാർട്ട്മെന്റിനെക്കുറിച്ചാണ് അറിയേണ്ടത്?',
    offTopicReply: 'അത് എനിക്ക് സഹായിക്കാൻ കഴിയുന്ന പരിധിക്ക് പുറത്താണ്.',
    script: /[\u0D00-\u0D7F]/,
  },
];

async function installSpeechRecognition(page: Page, transcript: string) {
  await page.addInitScript(({ spoken }) => {
    HTMLMediaElement.prototype.play = () => Promise.resolve();
    class MockSpeechRecognition {
      continuous = false;
      interimResults = false;
      lang = '';
      onresult: ((event: unknown) => void) | null = null;
      onerror: ((event: unknown) => void) | null = null;
      onend: (() => void) | null = null;
      start() {
        (window as unknown as { __REGIONAL_STT_LANG?: string }).__REGIONAL_STT_LANG = this.lang;
        (window as unknown as { __REGIONAL_STT_RAW?: string }).__REGIONAL_STT_RAW = spoken;
        setTimeout(() => {
          this.onresult?.({ resultIndex: 0, results: [[{ transcript: spoken }]] });
          this.onend?.();
        }, 25);
      }
      stop() { this.onend?.(); }
      abort() { this.onend?.(); }
    }
    Object.defineProperty(window, 'SpeechRecognition', { configurable: true, value: MockSpeechRecognition });
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: async () => ({ getTracks: () => [{ stop: () => undefined }] }) },
    });
  }, { spoken: transcript });
}

async function ready(page: Page, language: RegionalCase['language']) {
  await page.goto('http://localhost:5176/?e2e=1', { waitUntil: 'domcontentloaded' });
  const sleep = page.getByTestId('sleep-screen');
  await expect(sleep).toBeVisible({ timeout: 30_000 });
  await sleep.click({ force: true });
  await expect(page.getByTestId('chat-screen')).toBeVisible({ timeout: 30_000 });
  const button = page.getByTestId(`inline-language-${language}`);
  await expect(button).toBeVisible({ timeout: 60_000 });
  await button.click({ force: true });
  await page.waitForFunction(() => typeof window.__CLARA_TEST_SEND_MESSAGE === 'function');
  await page.waitForTimeout(1_000);
  await page.evaluate(() => window.__CLARA_TEST_SEND_MESSAGE?.('Alex'));
  await page.waitForTimeout(1_500);
}

async function ask(page: Page, text: string) {
  await page.evaluate((query) => window.__CLARA_TEST_SEND_MESSAGE?.(query), text);
}

async function waitUnits(page: Page, unitIds: string[]) {
  await expect.poll(
    async () => page.evaluate(() => {
      const debug = window.__CLARA_M52_DEBUG?.();
      const direct = debug?.unitIds;
      if (Array.isArray(direct) && direct.length) return direct;
      const queued = debug?.queueUnitIds;
      if (Array.isArray(queued) && queued.length) return queued;
      return (debug?.unitCardContents || []).map((card) => card.unitId).filter(Boolean);
    }),
    { timeout: 90_000 },
  ).toEqual(unitIds);
}

for (const regional of CASES) {
  test(`${regional.language} canonical typed, queue, localization, reset, and STT`, async ({ page }) => {
    test.setTimeout(240_000);
    await installSpeechRecognition(page, regional.single);
    await ready(page, regional.language);

    await ask(page, regional.single);
    await waitUnits(page, ['cse_ds.hod']);
    await expect(page.getByTestId('hod-card')).toBeVisible();
    const localizedCardText = await page.getByTestId('hod-card').innerText();
    expect(localizedCardText).toMatch(regional.script);
    expect(localizedCardText).not.toContain('With 20 years of experience');

    await ask(page, regional.mixedSingle);
    await waitUnits(page, ['cse_ds.hod']);
    await expect(page.getByTestId('hod-card')).toBeVisible();
    expect(await page.getByTestId('hod-card').innerText()).toMatch(regional.script);

    await ask(page, regional.multiHod);
    await waitUnits(page, ['cse.hod', 'cse_ds.hod']);
    await ask(page, regional.next);
    await expect.poll(
      async () => page.evaluate(() => window.__CLARA_M52_DEBUG?.().cardIndex),
      { timeout: 30_000 },
    ).toBe(1);
    await ask(page, regional.previous);
    await expect.poll(
      async () => page.evaluate(() => window.__CLARA_M52_DEBUG?.().cardIndex),
      { timeout: 30_000 },
    ).toBe(0);

    await ask(page, regional.mixed);
    await waitUnits(page, ['cse.hod', 'cse_ds.fees']);
    await ask(page, regional.reset);
    await waitUnits(page, ['ece.fees']);
    await expect.poll(
      async () => page.evaluate(() => window.__CLARA_M52_DEBUG?.().cardIndex),
      { timeout: 30_000 },
    ).toBe(0);

    await page.getByTestId('chat-orb').last().click({ force: true });
    await waitUnits(page, ['cse_ds.hod']);
    expect(await page.evaluate(() => (window as unknown as { __REGIONAL_STT_LANG?: string }).__REGIONAL_STT_LANG))
      .toBe(regional.sttCode);
    expect(await page.evaluate(() => (window as unknown as { __REGIONAL_STT_RAW?: string }).__REGIONAL_STT_RAW))
      .toBe(regional.single);
  });

  test(`${regional.language} follow-up, replacement, and global cards`, async ({ page }) => {
    test.setTimeout(240_000);
    await ready(page, regional.language);

    await ask(page, regional.overview);
    await waitUnits(page, ['cse_ds.overview']);
    for (const [question, unitId] of [
      [regional.followHod, 'cse_ds.hod'],
      [regional.followFaculty, 'cse_ds.faculty'],
      [regional.replacement, 'ece.hod'],
    ] as const) {
      await ask(page, question);
      await waitUnits(page, [unitId]);
    }

    await ask(page, regional.principal);
    await waitUnits(page, ['leadership.principal']);
    await expect(page.getByTestId('principal-card')).toBeVisible();
    expect(await page.getByTestId('principal-card').innerText()).toMatch(regional.script);

    await ask(page, regional.admissions);
    await waitUnits(page, ['college.admissions']);
    await expect(page.getByTestId('campus-unit-card')).toContainText(regional.script);

    await ask(page, regional.location);
    await waitUnits(page, ['college.location']);
    await expect(page.getByTestId('campus-unit-card')).toContainText(regional.script);
  });

  test(`${regional.language} localized clarification and off-topic fallback`, async ({ page }) => {
    test.setTimeout(180_000);
    await ready(page, regional.language);

    await ask(page, regional.missingHod);
    await expect(page.locator('body')).toContainText(regional.missingDepartmentReply, { timeout: 90_000 });
    await expect.poll(
      async () => page.evaluate(() => window.__CLARA_M52_DEBUG?.().unitIds ?? null),
      { timeout: 30_000 },
    ).toBeNull();

    await ask(page, 'What is the weather on the moon?');
    await expect(page.locator('body')).toContainText(regional.offTopicReply, { timeout: 90_000 });
    await expect.poll(
      async () => page.evaluate(() => window.__CLARA_M52_DEBUG?.().unitIds ?? null),
      { timeout: 30_000 },
    ).toBeNull();
  });
}
