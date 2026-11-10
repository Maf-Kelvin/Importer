import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'src/api/generated', 'playwright-report', 'node_modules'] },
  // ---- Architecture boundaries (see README.md "Layers") -------------------------------------
  // Dependencies point one way: lib <- api <- auth <- components <- features <- app.
  {
    files: ['src/lib/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': ['error', { patterns: [{ group: ['@/api/*', '@/auth/*', '@/components/*', '@/features/*'], message: 'lib/ is the lowest layer: it must not import from api, auth, components or features.' }] }],
    },
  },
  {
    files: ['src/api/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': ['error', { patterns: [{ group: ['@/auth/*', '@/components/*', '@/features/*'], message: 'api/ must not import from auth, components or features.' }] }],
    },
  },
  {
    files: ['src/components/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': ['error', { patterns: [{ group: ['@/features/*'], message: 'Shared components must not depend on a feature.' }] }],
    },
  },
  {
    // Inside src/features/<x>/ use relative imports. To use ANOTHER feature, import its index only.
    files: ['src/features/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': ['error', { patterns: [{ group: ['@/features/*/*'], message: "Import a feature through its index (e.g. '@/features/items'), not its internal files." }] }],
    },
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: { ecmaVersion: 2022, globals: globals.browser },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': 'error',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
);
