import tseslint from "typescript-eslint"

export default [
  {
    ignores: [".next/**", "node_modules/**", "out/**"],
  },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
        sourceType: "module",
      },
    },
  },
]
