/**
 * 把整个拉丁名切分成若干真实单词（name|you|like、what|to|call）。
 *
 * 多真词连写的短语（NameYouLike、WhatToCall）元音占比高、整体查词典查不到，
 * 以前落在「一个真词或两个词根」的缝隙里被判生造。判据应是「能不能完整读成
 * 几个真词」，所以这里做完整切分，而不是只看两段。
 */

/** 允许出现在短语里的两个字母常用词：to、of、in、my 这类，单列成表避免误切碎片。 */
const SHORT_FUNCTION_WORDS = new Set([
  "to", "of", "in", "on", "at", "by", "my", "me", "we", "it", "is", "be",
  "do", "go", "up", "an", "as", "so", "no", "or", "if", "us", "he", "ok",
]);

/** 最多切几段：超过五段的「名字」已经是句子，不该按名字放行。 */
const MAX_PARTS = 5;

/** 单个词元最长 12 个字母：更长的是拼写错误或外语句子，不在这套判据里。 */
const MAX_PART_LENGTH = 12;

export function splitRealWords(
  value: string,
  isReal: (word: string) => boolean,
): string[] | null {
  const word = value.toLowerCase().replace(/[^a-z]/g, "");
  if (word.length < 6) return null;

  const isWord = (piece: string): boolean =>
    piece.length >= 3 ? isReal(piece) : SHORT_FUNCTION_WORDS.has(piece);

  const best: Array<string[] | null> = Array.from({ length: word.length + 1 }, () => null);
  best[0] = [];
  for (let end = 1; end <= word.length; end += 1) {
    for (let start = Math.max(0, end - MAX_PART_LENGTH); start < end; start += 1) {
      const head = best[start];
      if (!head || head.length >= MAX_PARTS) continue;
      const piece = word.slice(start, end);
      if (!isWord(piece)) continue;
      best[end] = [...head, piece];
    }
  }

  const parts = best[word.length];
  return parts && parts.length >= 2 ? parts : null;
}
