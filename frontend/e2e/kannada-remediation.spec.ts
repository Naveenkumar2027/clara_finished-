import { expect, test } from '@playwright/test';

const NAME_PROMPT = 'ದಯವಿಟ್ಟು ನಿಮ್ಮನ್ನು ಯಾವ ಹೆಸರಿನಿಂದ ಕರೆಯಬೇಕೆಂದು ತಿಳಿಸಿ.';
const NAMED_WELCOME = 'ಆಶಾ ಅವರೇ, ಸ್ವಾಗತ. ಇಂದು ನಿಮಗೆ ಯಾವ ಮಾಹಿತಿ ಬೇಕು?';
const OFFICIAL_BLOCKED =
  'ಈ ಮಾಹಿತಿಯನ್ನು ಇನ್ನೂ ಅಧಿಕೃತವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ. ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ಸಂಬಂಧಿತ ವಿಭಾಗವನ್ನು ಸಂಪರ್ಕಿಸಿ.';
const MISSING_SOURCE_BLOCKED =
  'ಅನುಮೋದಿತ ಮೂಲದಲ್ಲಿ ಈ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. ಹೆಚ್ಚಿನ ಮಾಹಿತಿಗಾಗಿ ಸಂಬಂಧಿತ ವಿಭಾಗವನ್ನು ಸಂಪರ್ಕಿಸಿ.';

test.describe('real Kannada remediation flow', () => {
  test('real app selects Kannada, renders exact welcome, and blocks sample facts', async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto('http://127.0.0.1:5176/?e2e=1');
    const sleep = page.getByTestId('sleep-screen');
    await expect(sleep).toBeVisible({ timeout: 20_000 });
    await sleep.focus();
    await page.keyboard.press('Enter');
    const chat = page.getByTestId('chat-screen');
    await expect(chat).toBeVisible({ timeout: 20_000 });

    const kannada = page.getByTestId('inline-language-kannada');
    await expect(kannada).toBeVisible({ timeout: 20_000 });
    await kannada.click({ force: true });
    const namePrompt = page.getByText(NAME_PROMPT, { exact: true });
    await expect(namePrompt).toBeVisible({ timeout: 20_000 });
    await expect(namePrompt).toHaveClass(/indic-message-reveal/);
    await expect(namePrompt).toHaveAttribute('lang', 'kn');
    await expect(namePrompt.locator('.letter-reveal, .letter-reveal-sync, .token-reveal')).toHaveCount(0);
    await expect(namePrompt.locator('span')).toHaveCount(0);
    expect(await namePrompt.evaluate((element) => element.childNodes.length)).toBe(1);
    await expect(namePrompt).toHaveCSS('letter-spacing', 'normal');
    await expect(namePrompt).toHaveCSS('font-family', /Noto Sans Kannada/);

    await page.waitForFunction(() => typeof window.__CLARA_TEST_SEND_MESSAGE === 'function');
    await page.evaluate(() => window.__CLARA_TEST_SEND_MESSAGE?.('ಆಶಾ'));
    await expect(page.getByText(NAMED_WELCOME, { exact: true })).toBeVisible({ timeout: 20_000 });
    await expect(chat).toHaveClass(/script-typo-kn/);
    await expect(chat).toHaveAttribute('lang', 'kn');
    await expect(page.getByRole('button', { name: 'ಮುಖಪುಟಕ್ಕೆ ಹೋಗಿ' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'ಕಾಲೇಜಿನ ಮಾಹಿತಿ ಕೈಪಿಡಿ' })).toBeVisible();
    await page.screenshot({
      path: 'test-results/kannada-named-welcome.png',
      fullPage: true,
    });

    await page.evaluate(() => window.__CLARA_TEST_SEND_MESSAGE?.('girls hostel rooms'));
    await expect
      .poll(async () => {
        const visibleText = await page.locator('main').innerText();
        return visibleText.includes(OFFICIAL_BLOCKED) || visibleText.includes(MISSING_SOURCE_BLOCKED);
      }, { timeout: 60_000 })
      .toBe(true);
    await expect(page.getByText('SAMPLE_REPLACE_WITH_OFFICIAL')).toHaveCount(0);
    await page.screenshot({
      path: 'test-results/kannada-approved-blocker.png',
      fullPage: true,
    });
  });
});
