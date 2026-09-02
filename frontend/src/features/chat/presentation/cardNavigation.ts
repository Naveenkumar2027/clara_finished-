export type CardNavigationDirection = 'next' | 'previous';

const NEXT_COMMANDS = new Set([
  'next',
  'next card',
  'ಮುಂದೆ',
  'ಮುಂದಿನ',
  'अगला',
  'अगली',
  'आगे',
  'नेक्स्ट',
  'తదుపరి',
  'తర్వాత',
  'ముందుకు',
  'அடுத்து',
  'அடுத்த',
  'അടുത്ത',
  'അടുത്തത്',
  'മുന്നോട്ട്',
  'पुढे',
  'पुढील',
]);

const PREVIOUS_COMMANDS = new Set([
  'previous',
  'previous card',
  'back',
  'ಹಿಂದೆ',
  'ಹಿಂದಿನ',
  'पिछला',
  'पिछली',
  'पीछे',
  'वापस',
  'మునుపటి',
  'వెనుకకు',
  'వెనక్కి',
  'முந்தைய',
  'பின்னால்',
  'മുമ്പത്തെ',
  'പിന്നോട്ട്',
  'मागे',
  'मागील',
]);

function normalizeCommand(text: string): string {
  return text
    .normalize('NFKC')
    .toLocaleLowerCase('und')
    .replace(/[\p{P}\p{S}]+/gu, ' ')
    .replace(/\s+/gu, ' ')
    .trim();
}

/**
 * Recognize only a complete navigation command. Once a canonical card queue
 * exists, language changes how the command is recognized, never how the queue
 * is resolved or ordered.
 */
export function parseCardNavigationCommand(text: string): CardNavigationDirection | null {
  const command = normalizeCommand(text);
  if (NEXT_COMMANDS.has(command)) return 'next';
  if (PREVIOUS_COMMANDS.has(command)) return 'previous';
  return null;
}
