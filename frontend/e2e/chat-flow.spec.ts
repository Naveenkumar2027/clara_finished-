import { test, expect, type Page } from '@playwright/test';

async function installMockClaraSocket(page: Page) {
  await page.addInitScript(() => {
    const greetingPayload = {
      turn_id: 'greeting_opening',
      isProcessing: false,
      isSpeaking: false,
      messages: [
        {
          id: 'greeting',
          role: 'clara',
          text: 'Good evening. I am CLARA. How can I help you today?',
        },
      ],
    };
    const namePayload = {
      turn_id: 'name_after_language_pick',
      isProcessing: false,
      isSpeaking: false,
      messages: [
        {
          id: 'name_prompt',
          role: 'clara',
          text: 'May I know your preferred name?',
        },
      ],
    };
    const readyPayload = {
      turn_id: 'ready_after_language_pick',
      isProcessing: false,
      isSpeaking: false,
      messages: [
        {
          id: 'ready_prompt',
          role: 'clara',
          text: 'Wonderful. What would you like to know?',
        },
      ],
    };
    const documentsPayload = {
      turn_id: 'documents-answer',
      isProcessing: false,
      isSpeaking: true,
      audioPending: true,
      showCard: 'documents',
      messages: [
        { id: 'user-docs', role: 'user', text: 'admission documents' },
        {
          id: 'docs-answer',
          role: 'clara',
          text: 'These are the core admission documents.',
        },
      ],
    };
    const documentsAudioPayload = {
      ...documentsPayload,
      type: 'assistant_audio_update',
      isSpeaking: true,
      audioPending: false,
      audioUnavailable: false,
      audioBase64: 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=',
    };

    class MockClaraWebSocket extends EventTarget {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;
      /** First user_message after language_selected simulates guest-name reply → ready_prompt. */
      static postLangUserMsgCount = 0;

      CONNECTING = 0;
      OPEN = 1;
      CLOSING = 2;
      CLOSED = 3;
      readyState = MockClaraWebSocket.CONNECTING;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;

      constructor(_url: string) {
        super();
        window.setTimeout(() => {
          this.readyState = MockClaraWebSocket.OPEN;
          this.onopen?.(new Event('open'));
          if (new URLSearchParams(window.location.search).get('state') === '5') {
            this.emit(5, greetingPayload);
          }
        }, 0);
      }

      send(raw: string) {
        const msg = JSON.parse(raw);
        if (msg.action === 'wake') {
          MockClaraWebSocket.postLangUserMsgCount = 0;
          this.emit(5, greetingPayload);
        }
        if (msg.action === 'language_selected') {
          MockClaraWebSocket.postLangUserMsgCount = 0;
          this.emit(5, namePayload);
        }
        if (msg.action === 'user_message') {
          MockClaraWebSocket.postLangUserMsgCount += 1;
          const n = MockClaraWebSocket.postLangUserMsgCount;
          if (n === 1) {
            const ut = typeof msg.text === 'string' ? msg.text : '';
            this.emit(5, {
              turn_id: 'ready_after_language_pick',
              isProcessing: false,
              isSpeaking: false,
              messages: [
                { id: 'user-mock', role: 'user', text: ut },
                {
                  id: 'ready_prompt',
                  role: 'clara',
                  text: 'Wonderful. What would you like to know?',
                },
              ],
            });
            return;
          }
          this.emit(5, documentsPayload);
          window.setTimeout(() => this.emit(5, documentsAudioPayload), 120);
        }
        if (msg.action === 'reset_session' || msg.type === 'RESET_SESSION') {
          MockClaraWebSocket.postLangUserMsgCount = 0;
          this.emit(0, null);
        }
      }

      close() {
        this.readyState = MockClaraWebSocket.CLOSED;
        this.onclose?.(new CloseEvent('close'));
      }

      private emit(state: number, payload: unknown) {
        window.setTimeout(() => {
          if (payload && typeof payload === 'object' && (payload as { type?: string }).type === 'assistant_audio_update') {
            (window as unknown as { __CLARA_AUDIO_UPDATE_SEEN?: boolean }).__CLARA_AUDIO_UPDATE_SEEN = true;
          }
          this.onmessage?.(
            new MessageEvent('message', {
              data: JSON.stringify({ state, payload }),
            })
          );
        }, 0);
      }
    }

    window.WebSocket = MockClaraWebSocket as unknown as typeof WebSocket;
  });
}

async function wakeFromSleep(page: Page) {
  const sleepScreen = page.getByTestId('sleep-screen');
  await expect(sleepScreen).toBeVisible();
  await sleepScreen.focus();
  await page.keyboard.press('Enter');
}

async function selectInlineLanguage(page: Page, language: string) {
  const button = page.getByTestId(`inline-language-${language}`);
  await expect(button).toBeVisible({ timeout: 15000 });
  await button.scrollIntoViewIfNeeded();
  await button.click({ force: true });
}

async function completeInlineGuestNameGate(page: Page) {
  await expect(
    page.getByText(
      /May I know your preferred name\?|ನಿಮ್ಮ ಆತ್ಮೀಯ ಹೆಸರನ್ನು|आपका नाम|உங்கள் பெயரை|మీ పేరు|നിങ്ങളുടെ പേരറിയാമോ/i
    )
  ).toBeVisible({ timeout: 15000 });
  await page.waitForFunction(() => typeof window.__CLARA_TEST_SEND_MESSAGE === 'function');
  await page.evaluate(() => window.__CLARA_TEST_SEND_MESSAGE?.('Alex'));
  await expect(
    page.getByText(/Wonderful|ready to help|What would you like|सहायता|ಸಹಾಯ|உதவ|సహాయం|സഹായ/i)
  ).toBeVisible({ timeout: 15000 });
}

test.describe('CLARA chat flow', () => {
  test.beforeEach(async ({ page }) => {
    await installMockClaraSocket(page);
  });

  test('Sleep -> Language -> Chat (no menu) shows greeting and orb', async ({ page }) => {
    await page.goto('http://localhost:5176/?e2e=1');

    await wakeFromSleep(page);

    await expect(page.getByTestId('chat-screen')).toBeVisible({ timeout: 15000 });
    await selectInlineLanguage(page, 'english');
    await completeInlineGuestNameGate(page);

    await expect(page.getByRole('button', { name: /Voice input|Tap to speak/i })).toBeVisible();
  });

  test('URL ?state=5 shows chat screen with greeting and orb', async ({ page }) => {
    await page.goto('http://localhost:5176/?state=5&e2e=1', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    await expect(page.getByTestId('chat-screen')).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/Good (morning|afternoon|evening)|I am CLARA|selectLanguage|Select Language/i)
    ).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('button', { name: /Voice input|Tap to speak/i })).toBeVisible();
    await page.screenshot({ path: 'test-results/chat-screen-verified.png', fullPage: true });
  });

  test('Keyboard wake reaches language then chat', async ({ page }) => {
    await page.goto('http://localhost:5176/?e2e=1', { waitUntil: 'networkidle' });
    await wakeFromSleep(page);

    await expect(page.getByTestId('chat-screen')).toBeVisible({ timeout: 10000 });
    await selectInlineLanguage(page, 'english');
    await completeInlineGuestNameGate(page);

    await expect(page.getByRole('button', { name: /Voice input|Tap to speak/i })).toBeVisible();
  });

  test('English text query shows assistant result and reset returns to sleep', async ({ page }) => {
    await page.goto('http://localhost:5176/?e2e=1');
    await wakeFromSleep(page);

    await expect(page.getByTestId('chat-screen')).toBeVisible({ timeout: 15000 });
    await selectInlineLanguage(page, 'english');
    await completeInlineGuestNameGate(page);

    await expect(page.getByRole('button', { name: /Voice input|Tap to speak/i })).toBeVisible({ timeout: 15000 });
    await page.evaluate(() => window.__CLARA_TEST_SEND_MESSAGE?.('admission documents'));

    await expect(page.getByTestId('documents-block')).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/10th Marks Card/i)).toBeVisible();
    await page.waitForFunction(() => Boolean((window as unknown as { __CLARA_AUDIO_UPDATE_SEEN?: boolean }).__CLARA_AUDIO_UPDATE_SEEN));

    await page.getByTestId('home-button').click();
    await expect(page.getByTestId('sleep-screen')).toBeVisible({ timeout: 10000 });
  });

  for (const language of ['english', 'kannada', 'hindi', 'tamil', 'telugu', 'malayalam']) {
    test(`language selection reaches ready chat for ${language}`, async ({ page }) => {
      await page.goto('http://localhost:5176/?e2e=1');
      await wakeFromSleep(page);

      await expect(page.getByTestId('chat-screen')).toBeVisible({ timeout: 15000 });
      await selectInlineLanguage(page, language);
      await completeInlineGuestNameGate(page);

      await expect(page.getByTestId('chat-orb')).toBeVisible({ timeout: 15000 });
    });
  }
});
