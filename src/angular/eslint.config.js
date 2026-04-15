// @ts-check

const eslint = require("@eslint/js");
const tseslint = require("typescript-eslint");
const globals = require("globals");

module.exports = tseslint.config(
    {
        ignores: ["node_modules/", "dist/", "e2e/", "**/*.js"]
    },
    eslint.configs.recommended,
    ...tseslint.configs.recommended,
    {
        files: ["**/*.ts"],
        languageOptions: {
            parser: tseslint.parser,
            parserOptions: {
                project: ["tsconfig.json"],
                createDefaultProgram: true
            },
            globals: {
                ...globals.browser
            }
        },
        plugins: {
            "@typescript-eslint": tseslint.plugin
        },
        rules: {
            "@typescript-eslint/no-inferrable-types": ["error", { "ignoreParameters": true }],
            "@typescript-eslint/no-non-null-assertion": "off",
            "@typescript-eslint/no-shadow": "error",
            "@typescript-eslint/no-unused-expressions": "error",
            "@typescript-eslint/prefer-function-type": "error",
            "@typescript-eslint/unified-signatures": "error",
            "@typescript-eslint/no-empty-function": "warn",
            "@typescript-eslint/no-explicit-any": "warn",
            "@typescript-eslint/explicit-function-return-type": "warn",
            "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
            "@typescript-eslint/no-namespace": "off",
            "@typescript-eslint/no-this-alias": "off",
            "@typescript-eslint/no-empty-object-type": "off",
            "arrow-body-style": "off",
            "curly": "error",
            "eol-last": "error",
            "eqeqeq": ["error", "always", { "null": "ignore" }],
            "guard-for-in": "error",
            "max-len": ["error", { "code": 140 }],
            "no-bitwise": "error",
            "no-caller": "error",
            "no-console": ["error", { "allow": ["warn", "error", "debug"] }],
            "no-debugger": "error",
            "no-eval": "error",
            "no-fallthrough": "error",
            "no-labels": "error",
            "no-new-wrappers": "error",
            "no-throw-literal": "error",
            "no-trailing-spaces": "error",
            "no-var": "error",
            "prefer-const": "error",
            "quotes": ["error", "double", { "allowTemplateLiterals": true }],
            "radix": "error",
            "semi": ["error", "always"],
            "spaced-comment": ["error", "always"]
        }
    }
);
