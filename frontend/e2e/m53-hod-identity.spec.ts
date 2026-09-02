import { test, expect, type Page } from '@playwright/test';

async function stubMediaOnly(page: Page) {
  await page.addInitScript(() => {
    HTMLMediaElement.prototype.play = function () {
      return Promise.resolve();
    };
  });
}

async function wakeFromSleep(page: Page) {
  const sleepScreen = page.getByTestId('sleep-screen');
  await expect(sleepScreen).toBeVisible({ timeout: 30000 });
  await sleepScreen.click({ force: true });
  try {
    await expect(sleepScreen).toBeHidden({ timeout: 8000 });
  } catch {
    await sleepScreen.focus();
    await page.keyboard.press('Enter');
    await expect(sleepScreen).toBeHidden({ timeout: 8000 });
  }
}

type InlineLang = 'english' | 'kannada' | 'hindi' | 'tamil' | 'telugu' | 'malayalam';

const NAME_PROMPT =
  /May I know your preferred name|ಆತ್ಮೀಯ|ದಯವಿಟ್ಟು ನಿಮ್ಮನ್ನು|आपका नाम|உங்கள் பெயரை|మీ పేరు|നിങ്ങളുടെ/;

const READY_PROMPT =
  /Wonderful to meet you|What would you like|ಸಂತೋಷ|ಸ್ವಾಗತ|मिलकर अच्छा|மகிழ்ச்சி|కలవడం ఆనందం|കാണാൻ സന്തോഷം/;

async function reachReadyChat(page: Page, language: InlineLang) {
  await page.goto('http://localhost:5176/?e2e=1', { waitUntil: 'domcontentloaded' });
  await wakeFromSleep(page);
  await expect(page.getByTestId('chat-screen')).toBeVisible({ timeout: 30000 });
  const button = page.getByTestId(`inline-language-${language}`);
  await expect(button).toBeVisible({ timeout: 60000 });
  await button.click({ force: true });
  await expect(page.locator('body')).toContainText(NAME_PROMPT, { timeout: 60000 });
  await page.waitForFunction(() => typeof window.__CLARA_TEST_SEND_MESSAGE === 'function');
  await page.evaluate(() => window.__CLARA_TEST_SEND_MESSAGE?.('Alex'));
  await expect(page.locator('body')).toContainText(READY_PROMPT, { timeout: 60000 });
}

async function ask(page: Page, text: string) {
  await page.evaluate((q) => window.__CLARA_TEST_SEND_MESSAGE?.(q), text);
}

async function m52(page: Page) {
  await page.waitForFunction(() => typeof window.__CLARA_M52_DEBUG === 'function');
  return page.evaluate(() => window.__CLARA_M52_DEBUG!());
}

async function waitForHod(page: Page, unitIds: string[]) {
  await expect(page.getByTestId('hod-card')).toBeVisible({ timeout: 90000 });
  await expect(page.getByTestId('hod-card')).toHaveAttribute(
    'data-hod-count',
    String(unitIds.length),
    { timeout: 90000 },
  );
  await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual(unitIds);
}

async function waitForClipSlots(page: Page, n: number) {
  await expect
    .poll(async () => {
      const d = await m52(page);
      const ids = d.queueUnitIds ?? [];
      return d.queueLength === n || ids.length === n;
    }, { timeout: 90000 })
    .toBe(true);
}

async function assertClip(page: Page, unitId: string) {
  await expect(page.getByTestId('hod-card')).toHaveAttribute('data-unit-id', unitId, {
    timeout: 30000,
  });
  await expect.poll(async () => (await m52(page)).playbackUnitId, { timeout: 30000 }).toBe(unitId);
}

async function endClipWhenQueued(page: Page, nextUnitId: string, minQueue: number) {
  await expect
    .poll(async () => (await m52(page)).queueLength, { timeout: 90000 })
    .toBeGreaterThanOrEqual(minQueue);
  await expect.poll(async () => (await m52(page)).hasCurrentAudio, { timeout: 30000 }).toBe(true);
  await page.evaluate(() => window.__CLARA_M52_END_CLIP?.());
  await assertClip(page, nextUnitId);
}

test.describe('M5.3 HOD identity live browser', () => {
  test.setTimeout(180000);

  test.beforeEach(async ({ page }) => {
    await stubMediaOnly(page);
  });

  test('English single HOD is cse_ds.hod', async ({ page }) => {
    await reachReadyChat(page, 'english');
    await ask(page, 'Who is the HOD of CSE Data Science?');
    await waitForHod(page, ['cse_ds.hod']);
    await assertClip(page, 'cse_ds.hod');
    const dbg = await m52(page);
    expect(dbg.unitCardContents?.[0]?.content || '').toMatch(/Nagashree/i);
    expect(dbg.unitCardContents?.[0]?.content || '').not.toMatch(/Shashikumar/i);
  });

  test('English two HOD then sequential clips', async ({ page }) => {
    await reachReadyChat(page, 'english');
    await ask(page, 'Who is the HOD of AIML and Data Science?');
    await waitForHod(page, ['cse_aiml.hod', 'cse_ds.hod']);
    await waitForClipSlots(page, 2);
    await assertClip(page, 'cse_aiml.hod');
    await endClipWhenQueued(page, 'cse_ds.hod', 2);
    await expect
      .poll(async () => (await m52(page)).queueLength, { timeout: 90000 })
      .toBeGreaterThanOrEqual(2);
    await page.evaluate(() => window.__CLARA_M52_END_CLIP?.());
    await expect.poll(async () => (await m52(page)).engineState, { timeout: 30000 }).toBe(
      'PRESENTATION_COMPLETE',
    );
  });

  test('exact multi-entity HOD request keeps contextual card instances and navigation', async ({ page }) => {
    const duplicateKeyWarnings: string[] = [];
    page.on('console', (message) => {
      const text = message.text();
      if (/same key|unique "key" prop|duplicate key/i.test(text)) duplicateKeyWarnings.push(text);
    });

    await reachReadyChat(page, 'english');
    await ask(page, 'Who is the CSE HOD and Data Science HOD?');
    await waitForHod(page, ['cse.hod', 'cse_ds.hod']);
    await expect.poll(async () => (await m52(page)).cardIds, { timeout: 90000 }).toEqual([
      'hod_profile',
      'hod_profile',
    ]);
    await expect(page.getByTestId('hod-card')).toHaveAttribute('data-unit-id', 'cse.hod');

    await ask(page, 'next');
    await expect.poll(async () => (await m52(page)).cardIndex, { timeout: 30000 }).toBe(1);
    await expect(page.getByTestId('hod-card')).toHaveAttribute('data-unit-id', 'cse_ds.hod');

    await ask(page, 'previous');
    await expect.poll(async () => (await m52(page)).cardIndex, { timeout: 30000 }).toBe(0);
    await expect(page.getByTestId('hod-card')).toHaveAttribute('data-unit-id', 'cse.hod');
    expect(duplicateKeyWarnings).toEqual([]);
  });

  test('exact multi-entity Kannada request reuses the same canonical queue', async ({ page }) => {
    await reachReadyChat(page, 'kannada');
    await ask(page, 'CSE HOD ಮತ್ತು Data Science HOD ಯಾರು?');
    await waitForHod(page, ['cse.hod', 'cse_ds.hod']);
    const debug = await m52(page);
    expect(debug.cardIds).toEqual(['hod_profile', 'hod_profile']);
    expect(debug.unitCardContents?.[0]?.content || '').toMatch(/[\u0C80-\u0CFF]/);
    expect(debug.unitCardContents?.[1]?.content || '').toMatch(/[\u0C80-\u0CFF]/);
  });

  test('exact Hindi and code-switched HOD requests use Hindi cards', async ({ page }) => {
    await reachReadyChat(page, 'hindi');
    for (const question of ['डेटा साइंस के HOD कौन हैं?', 'data science HOD कौन है?']) {
      await ask(page, question);
      await waitForHod(page, ['cse_ds.hod']);
      const debug = await m52(page);
      expect(debug.cardIds).toEqual(['hod_profile']);
      expect(debug.unitCardContents?.[0]?.content || '').toMatch(/[\u0900-\u097F]/);
      await expect(page.getByTestId('hod-card')).toContainText(/[\u0900-\u097F]/);
    }
  });

  test('exact Hindi multi-entity queue preserves order and Hindi navigation', async ({ page }) => {
    const duplicateKeyWarnings: string[] = [];
    page.on('console', (message) => {
      if (/same key|unique "key" prop|duplicate key/i.test(message.text())) {
        duplicateKeyWarnings.push(message.text());
      }
    });
    await reachReadyChat(page, 'hindi');
    await ask(page, 'CSE HOD और Data Science HOD कौन हैं?');
    await waitForHod(page, ['cse.hod', 'cse_ds.hod']);
    expect((await m52(page)).cardIds).toEqual(['hod_profile', 'hod_profile']);
    await ask(page, 'अगला');
    await expect.poll(async () => (await m52(page)).visibleUnitId, { timeout: 30000 }).toBe('cse_ds.hod');
    await ask(page, 'पिछला');
    await expect.poll(async () => (await m52(page)).visibleUnitId, { timeout: 30000 }).toBe('cse.hod');
    await ask(page, 'आगे');
    await expect.poll(async () => (await m52(page)).visibleUnitId, { timeout: 30000 }).toBe('cse_ds.hod');
    await ask(page, 'वापस');
    await expect.poll(async () => (await m52(page)).visibleUnitId, { timeout: 30000 }).toBe('cse.hod');
    expect(duplicateKeyWarnings).toEqual([]);
  });

  test('exact Hindi mixed-card request preserves entity pairing', async ({ page }) => {
    await reachReadyChat(page, 'hindi');
    await ask(page, 'CSE HOD और Data Science fees दिखाओ');
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 30000 }).toEqual([
      'cse.hod',
      'cse_ds.fees',
    ]);
    const debug = await m52(page);
    expect(debug.cardIds).toEqual(['hod_profile', 'fees']);
    expect(debug.unitCardContents?.every((card) => /[\u0900-\u097F]/.test(card.content || ''))).toBe(true);
    await ask(page, 'आगे');
    await expect(page.getByTestId('department-fees-card')).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId('department-fees-card')).toContainText(/फीस|शुल्क/u);
  });

  test('Hindi faculty and global location use shared unit cards and reset queues', async ({ page }) => {
    await reachReadyChat(page, 'hindi');
    await ask(page, 'CSE HOD, Data Science faculty और ECE fees दिखाओ');
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual([
      'cse.hod',
      'cse_ds.faculty',
      'ece.fees',
    ]);
    expect((await m52(page)).cardIds).toEqual(['hod_profile', 'faculty_list', 'fees']);

    await ask(page, 'अगला');
    await expect.poll(async () => (await m52(page)).visibleUnitId, { timeout: 30000 }).toBe('cse_ds.faculty');
    await expect(page.getByTestId('campus-unit-card')).toHaveAttribute('data-unit-id', 'cse_ds.faculty');
    await expect(page.getByTestId('campus-unit-card')).toContainText(/[\u0900-\u097F]/);

    await ask(page, 'कॉलेज कहाँ है?');
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual(['college.location']);
    expect((await m52(page)).cardIds).toEqual(['location']);
    await expect(page.getByTestId('campus-unit-card')).toHaveAttribute('data-unit-id', 'college.location');
    await expect(page.getByTestId('campus-unit-card')).toContainText(/राजानुकुंटे/u);
  });

  test('Hindi follow-ups reuse context and an explicit department replaces it', async ({ page }) => {
    await reachReadyChat(page, 'hindi');
    await ask(page, 'डेटा साइंस विभाग दिखाओ');
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual([
      'cse_ds.overview',
    ]);

    for (const [question, unitId, cardId] of [
      ['HOD भी', 'cse_ds.hod', 'hod_profile'],
      ['faculty भी', 'cse_ds.faculty', 'faculty_list'],
      ['fees?', 'cse_ds.fees', 'fees'],
      ['ECE HOD दिखाओ', 'ece.hod', 'hod_profile'],
    ] as const) {
      await ask(page, question);
      await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual([unitId]);
      expect((await m52(page)).cardIds).toEqual([cardId]);
    }
  });

  test('Hindi missing-department clarification stays Hindi and creates no card queue', async ({ page }) => {
    await reachReadyChat(page, 'hindi');
    await ask(page, 'HOD कौन हैं?');
    await expect(page.locator('body')).toContainText('आप किस विभाग के बारे में जानना चाहेंगे?', {
      timeout: 90000,
    });
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 30000 }).toBeNull();
  });

  test('Hindi global and campus cards stay localized and hide sample metadata', async ({ page }) => {
    await reachReadyChat(page, 'hindi');
    await ask(page, 'प्रिंसिपल कौन हैं?');
    await expect(page.getByTestId('principal-card')).toBeVisible({ timeout: 90000 });
    await expect(page.getByTestId('principal-card')).toContainText(/[\u0900-\u097F]/);

    await ask(page, 'admission details बताओ');
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual([
      'college.admissions',
    ]);
    expect((await m52(page)).cardIds).toEqual(['admissions']);
    await expect(page.getByTestId('campus-unit-card')).toContainText(/[\u0900-\u097F]/);

    await ask(page, 'लड़कियों के हॉस्टल की फीस बताओ');
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual([
      'hostel.girls.fees',
    ]);
    expect((await m52(page)).cardIds).toEqual(['hostel']);
    const campusText = await page.getByTestId('campus-unit-card').innerText();
    expect(campusText).toContain('छात्रावास');
    expect(campusText).toContain('आधिकारिक पुष्टि');
    expect(campusText).not.toContain('SAMPLE_REPLACE_WITH_OFFICIAL');
  });

  test('Hindi direct course-menu selection sends a canonical department click', async ({ page }) => {
    await reachReadyChat(page, 'hindi');
    await ask(page, 'courses बताओ');
    await expect(page.getByTestId('course-menu')).toBeVisible({ timeout: 90000 });
    await page.getByTestId('course-menu-option-0').click();
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual([
      'cse.overview',
    ]);
    expect((await m52(page)).cardIds).toEqual(['department_overview']);
    await expect(page.locator('[data-card-language="Hindi"]')).toBeVisible();
  });

  test('Hindi session keeps deterministic off-topic fallback in Hindi', async ({ page }) => {
    await reachReadyChat(page, 'hindi');
    await ask(page, 'What is the weather on the moon?');
    await expect(page.locator('body')).toContainText(
      'यह मेरे सहायता क्षेत्र से बाहर है।',
      { timeout: 90000 },
    );
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 30000 }).toBeNull();
  });

  test('Hindi browser speech path requests hi-IN and routes a mixed transcript', async ({ page }) => {
    await page.addInitScript(() => {
      class MockSpeechRecognition {
        continuous = false;
        interimResults = false;
        lang = '';
        onresult: ((event: unknown) => void) | null = null;
        onerror: ((event: unknown) => void) | null = null;
        onend: (() => void) | null = null;
        start() {
          (window as unknown as { __HINDI_STT_LANG?: string }).__HINDI_STT_LANG = this.lang;
          setTimeout(() => {
            this.onresult?.({ resultIndex: 0, results: [[{ transcript: 'data science के एच ओ डी कौन है' }]] });
            this.onend?.();
          }, 25);
        }
        stop() { this.onend?.(); }
        abort() { this.onend?.(); }
      }
      Object.defineProperty(window, 'SpeechRecognition', {
        configurable: true,
        value: MockSpeechRecognition,
      });
      Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        value: {
          getUserMedia: async () => ({ getTracks: () => [{ stop: () => undefined }] }),
        },
      });
    });
    await reachReadyChat(page, 'hindi');
    await page.getByTestId('chat-orb').last().click({ force: true });
    await waitForHod(page, ['cse_ds.hod']);
    expect(await page.evaluate(() => (window as unknown as { __HINDI_STT_LANG?: string }).__HINDI_STT_LANG)).toBe('hi-IN');
    expect((await m52(page)).unitCardContents?.[0]?.content || '').toMatch(/[\u0900-\u097F]/);
  });

  test('English three HOD preserves order and completes after last', async ({ page }) => {
    await reachReadyChat(page, 'english');
    await ask(page, 'Who are the HODs of AIML, Data Science and CSE?');
    await waitForHod(page, ['cse_aiml.hod', 'cse_ds.hod', 'cse.hod']);
    await waitForClipSlots(page, 3);
    await assertClip(page, 'cse_aiml.hod');
    await endClipWhenQueued(page, 'cse_ds.hod', 2);
    await endClipWhenQueued(page, 'cse.hod', 3);
    await page.evaluate(() => window.__CLARA_M52_END_CLIP?.());
    await expect.poll(async () => (await m52(page)).engineState, { timeout: 30000 }).toBe(
      'PRESENTATION_COMPLETE',
    );
  });

  test('Kannada single HOD keeps localized card body', async ({ page }) => {
    await reachReadyChat(page, 'kannada');
    await ask(page, 'CSE Data Science HOD yaaru?');
    await waitForHod(page, ['cse_ds.hod']);
    await assertClip(page, 'cse_ds.hod');
    const body = (await m52(page)).unitCardContents?.[0]?.content || '';
    expect(body).toMatch(/[\u0C80-\u0CFF]/);
    expect(body).not.toMatch(/extensive teaching and research/i);
    const cardText = await page.getByTestId('hod-card').innerText();
    expect(cardText).toMatch(/[\u0C80-\u0CFF]/);
    expect(cardText).not.toMatch(/Shashikumar/i);
  });

  test('Kannada-English native-script HOD opens Data Science HOD directly', async ({ page }) => {
    await reachReadyChat(page, 'kannada');
    await ask(page, 'data science hod ಯಾರು?');
    await waitForHod(page, ['cse_ds.hod']);
    await assertClip(page, 'cse_ds.hod');
    const debug = await m52(page);
    expect(debug.unitIds).toEqual(['cse_ds.hod']);
    expect(debug.cardIds).toEqual(['hod_profile']);
    expect(debug.unitCardContents?.[0]?.content || '').toMatch(/[\u0C80-\u0CFF]/);
  });

  test('Kannada two HOD sequential clips', async ({ page }) => {
    await reachReadyChat(page, 'kannada');
    await ask(page, 'AIML mattu Data Science HOD yaaru?');
    await waitForHod(page, ['cse_aiml.hod', 'cse_ds.hod']);
    await waitForClipSlots(page, 2);
    await assertClip(page, 'cse_aiml.hod');
    await endClipWhenQueued(page, 'cse_ds.hod', 2);
  });

  test('Kannada three HOD sequential clips', async ({ page }) => {
    await reachReadyChat(page, 'kannada');
    await ask(page, 'AIML, Data Science mattu CSE HOD yaaru?');
    await waitForHod(page, ['cse_aiml.hod', 'cse_ds.hod', 'cse.hod']);
    await waitForClipSlots(page, 3);
    await assertClip(page, 'cse_aiml.hod');
    await endClipWhenQueued(page, 'cse_ds.hod', 2);
    await endClipWhenQueued(page, 'cse.hod', 3);
  });

  test('new turn resets from three HOD to single HOD', async ({ page }) => {
    await reachReadyChat(page, 'english');
    await ask(page, 'Who are the HODs of AIML, Data Science and CSE?');
    await waitForHod(page, ['cse_aiml.hod', 'cse_ds.hod', 'cse.hod']);
    await waitForClipSlots(page, 3);
    await ask(page, 'Who is the HOD of CSE Data Science?');
    await waitForHod(page, ['cse_ds.hod']);
    await waitForClipSlots(page, 1);
    await assertClip(page, 'cse_ds.hod');
  });

  test('new turn expands from single HOD to three HOD', async ({ page }) => {
    await reachReadyChat(page, 'english');
    await ask(page, 'Who is the HOD of CSE Data Science?');
    await waitForHod(page, ['cse_ds.hod']);
    await waitForClipSlots(page, 1);
    await ask(page, 'Who are the HODs of AIML, Data Science and CSE?');
    await waitForHod(page, ['cse_aiml.hod', 'cse_ds.hod', 'cse.hod']);
    await waitForClipSlots(page, 3);
    await assertClip(page, 'cse_aiml.hod');
  });

  test('multilingual navigation changes only active index in the resolved queue', async ({ page }) => {
    await reachReadyChat(page, 'kannada');
    await ask(page, 'Data Science overview, HOD and fees');
    await expect.poll(async () => (await m52(page)).unitIds, { timeout: 90000 }).toEqual([
      'cse_ds.overview',
      'cse_ds.hod',
      'cse_ds.fees',
    ]);
    await expect.poll(async () => (await m52(page)).cardIds, { timeout: 90000 }).toEqual([
      'department_overview',
      'hod_profile',
      'fees',
    ]);
    await ask(page, 'ಮುಂದೆ');
    await expect.poll(async () => (await m52(page)).cardIndex, { timeout: 30000 }).toBe(1);
    await expect.poll(async () => (await m52(page)).visibleUnitId, { timeout: 30000 }).toBe('cse_ds.hod');
    await ask(page, 'ಹಿಂದೆ');
    await expect.poll(async () => (await m52(page)).cardIndex, { timeout: 30000 }).toBe(0);
    expect((await m52(page)).unitIds).toEqual([
      'cse_ds.overview',
      'cse_ds.hod',
      'cse_ds.fees',
    ]);
  });

  const regional: Array<{
    lang: InlineLang;
    script: RegExp;
    q1: string;
    q2: string;
    q3: string;
  }> = [
    {
      lang: 'hindi',
      script: /[\u0900-\u097F]/,
      q1: 'CSE Data Science ka HOD kaun hai?',
      q2: 'AIML aur Data Science ke HOD kaun hain?',
      q3: 'AIML, Data Science aur CSE ke HOD kaun hain?',
    },
    {
      lang: 'tamil',
      script: /[\u0B80-\u0BFF]/,
      q1: 'CSE Data Science HOD yaar?',
      q2: 'AIML and Data Science HOD yaar?',
      q3: 'AIML, Data Science and CSE HOD yaar?',
    },
    {
      lang: 'telugu',
      script: /[\u0C00-\u0C7F]/,
      q1: 'CSE Data Science HOD evaru?',
      q2: 'AIML and Data Science HOD evaru?',
      q3: 'AIML, Data Science and CSE HOD evaru?',
    },
    {
      lang: 'malayalam',
      script: /[\u0D00-\u0D7F]/,
      q1: 'CSE Data Science HOD aaranu?',
      q2: 'AIML and Data Science HOD aaranu?',
      q3: 'AIML, Data Science and CSE HOD aaranu?',
    },
  ];

  for (const row of regional) {
    test(`${row.lang} single HOD keeps localized card body`, async ({ page }) => {
      await reachReadyChat(page, row.lang);
      await ask(page, row.q1);
      await waitForHod(page, ['cse_ds.hod']);
      await waitForClipSlots(page, 1);
      await assertClip(page, 'cse_ds.hod');
      const body = (await m52(page)).unitCardContents?.[0]?.content || '';
      expect(body).toMatch(row.script);
      const cardText = await page.getByTestId('hod-card').innerText();
      expect(cardText).toMatch(row.script);
    });

    test(`${row.lang} two HOD sequential clips`, async ({ page }) => {
      await reachReadyChat(page, row.lang);
      await ask(page, row.q2);
      await waitForHod(page, ['cse_aiml.hod', 'cse_ds.hod']);
      await waitForClipSlots(page, 2);
      await assertClip(page, 'cse_aiml.hod');
      await endClipWhenQueued(page, 'cse_ds.hod', 2);
    });

    test(`${row.lang} three HOD sequential clips`, async ({ page }) => {
      await reachReadyChat(page, row.lang);
      await ask(page, row.q3);
      await waitForHod(page, ['cse_aiml.hod', 'cse_ds.hod', 'cse.hod']);
      await waitForClipSlots(page, 3);
      await assertClip(page, 'cse_aiml.hod');
      await endClipWhenQueued(page, 'cse_ds.hod', 2);
      await endClipWhenQueued(page, 'cse.hod', 3);
    });
  }
});
