import { SubtitleChunk } from '../schema/types';

/**
 * Automatically splits narration text into timed subtitle chunks.
 * Splits by common punctuation or character count thresholds to prevent overflowing lines.
 */
export function generateSubtitles(
  narration: string,
  durationSeconds: number
): SubtitleChunk[] {
  if (!narration || narration.trim() === '') {
    return [];
  }

  // Define split characters (Chinese and English punctuation)
  const regex = /([，。！？；、,.?!;]+)/g;
  const parts = narration.split(regex);
  
  const sentences: string[] = [];
  let tempSentence = '';

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    if (!part) continue;
    
    if (part.match(regex)) {
      // It's a punctuation mark, append it to the current sentence
      tempSentence += part;
      if (tempSentence.trim()) {
        sentences.push(tempSentence.trim());
      }
      tempSentence = '';
    } else {
      // If we already have a pending sentence (e.g. consecutive texts without punctuation), push it first
      if (tempSentence.trim().length > 15) {
        sentences.push(tempSentence.trim());
        tempSentence = '';
      }
      tempSentence += part;
    }
  }
  
  if (tempSentence.trim()) {
    sentences.push(tempSentence.trim());
  }

  // If no sentences were generated (e.g., plain text without punctuation)
  if (sentences.length === 0) {
    sentences.push(narration.trim());
  }

  // Filter out empty entries
  const activeSentences = sentences.filter(s => s.length > 0);

  // If we have very long sentences, split them by character limits (e.g. max 18 characters for Chinese/English mixed)
  const finalSentences: string[] = [];
  const maxCharLimit = 20;

  for (const sentence of activeSentences) {
    if (sentence.length <= maxCharLimit) {
      finalSentences.push(sentence);
    } else {
      // Split into chunks of maxCharLimit
      let start = 0;
      while (start < sentence.length) {
        finalSentences.push(sentence.substring(start, start + maxCharLimit));
        start += maxCharLimit;
      }
    }
  }

  // Calculate total character count to allocate time proportionally
  const totalChars = finalSentences.reduce((sum, s) => sum + s.length, 0);
  if (totalChars === 0) return [];

  const chunks: SubtitleChunk[] = [];
  let accumulatedTime = 0;

  for (let i = 0; i < finalSentences.length; i++) {
    const sentence = finalSentences[i];
    const charRatio = sentence.length / totalChars;
    const chunkDuration = durationSeconds * charRatio;

    // Set start/end times
    const start = accumulatedTime;
    const end = Math.min(accumulatedTime + chunkDuration, durationSeconds);
    
    chunks.push({
      start,
      end,
      text: sentence,
    });

    accumulatedTime = end;
  }

  // Ensure the last chunk ends exactly at the total duration
  if (chunks.length > 0) {
    chunks[chunks.length - 1].end = durationSeconds;
  }

  return chunks;
}
