import js from "@eslint/js";
import globals from "globals";

export default [
  {
    ignores: ["node_modules/**", "backend/**", "tests/**", "workspace/**"],
  },
  {
    files: ["frontend/assets/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
        VIGIEPP_BUILD: "readonly",
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      "no-empty": ["error", { allowEmptyCatch: true }],
    },
  },
];
