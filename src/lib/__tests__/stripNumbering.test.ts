import { describe, it, expect } from 'vitest';
import { stripNumbering } from '@/lib/text';

describe('stripNumbering', () => {
  it('removes simple numbering like 1. ', () => {
    expect(stripNumbering('1. Hello world')).toBe('Hello world');
  });
  it('removes fraction numbering like 2/6 ', () => {
    expect(stripNumbering('2/6 This is fine')).toBe('This is fine');
  });
  it('removes bracketed numbering like [3] ', () => {
    expect(stripNumbering('[3] Test case')).toBe('Test case');
  });
  it('removes parenthetical numbering like (4) ', () => {
    expect(stripNumbering('(4) Keep going')).toBe('Keep going');
  });
  it('removes bullets', () => {
    expect(stripNumbering('• Bullet point')).toBe('Bullet point');
    expect(stripNumbering('- Bullet point')).toBe('Bullet point');
    expect(stripNumbering('* Bullet point')).toBe('Bullet point');
  });
  it('keeps clean text unchanged', () => {
    expect(stripNumbering('Clean text')).toBe('Clean text');
  });
});
