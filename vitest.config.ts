import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Default to node, tsx files override with jsdom below
    environment: 'node',
    environmentMatchGlobs: [
      // React components need jsdom (browser environment)
      ['src/__tests__/**/*.tsx', 'jsdom'],
      ['src/app/**/__tests__/**/*.tsx', 'jsdom'],
    ],
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    watch: false,
    reporters: ['default'],
    include: ['src/__tests__/**/*.{ts,tsx}', 'src/app/**/__tests__/**/*.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});
