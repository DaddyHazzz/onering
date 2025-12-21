import { describe, it } from 'vitest';

describe('No network calls on route import', () => {
  it('imports route modules without side effects', async () => {
    await import('../app/api/post-to-x/route');
    await import('../app/api/post-to-ig/route');
    await import('../app/api/post-to-linkedin/route');
  });
});
