import js from '@eslint/js';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import eslintConfigPrettier from 'eslint-config-prettier';
import importPlugin from 'eslint-plugin-import';
import vuePlugin from 'eslint-plugin-vue';
import vueParser from 'vue-eslint-parser';
import globals from 'globals';

const vueFiles = ['**/*.vue'];
const allSourceFiles = ['**/*.{js,jsx,cjs,mjs,ts,tsx,cts,mts,vue}'];
const moduleExtensions = ['.ts', '.tsx', '.cts', '.mts', '.js', '.jsx', '.mjs', '.cjs', '.vue'];

const typescriptConfigs = tseslint.configs['flat/recommended'].map((config) => ({
  ...config,
  languageOptions: {
    ...config.languageOptions,
    parserOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      ecmaFeatures: { jsx: true },
      ...(config.languageOptions?.parserOptions ?? {}),
    },
  },
}));

export default [
  {
    ignores: ['node_modules', 'dist', '*.min.js', 'vite.config.*.timestamp*', 'eslint.config.js'],
  },
  js.configs.recommended,
  ...vuePlugin.configs['flat/recommended'],
  ...typescriptConfigs,
  importPlugin.flatConfigs.recommended,
  importPlugin.flatConfigs.typescript,
  eslintConfigPrettier,
  {
    files: vueFiles,
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: {
          ts: tsParser,
          tsx: tsParser,
          cts: tsParser,
          mts: tsParser,
        },
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
        extraFileExtensions: ['.vue'],
      },
    },
  },
  {
    files: allSourceFiles,
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    settings: {
      'import/resolver': {
        typescript: {
          project: ['./tsconfig.json'],
          alwaysTryTypes: true,
        },
        node: {
          extensions: moduleExtensions,
        },
      },
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'import/order': [
        'warn',
        {
          'newlines-between': 'always',
          alphabetize: { order: 'asc' },
        },
      ],
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
];
