/**
 * Centralized Environment Variable Reader & Runtime Validator for RepoPilot.
 *
 * NOTE: Next.js statically replaces explicit property accesses (e.g. process.env.NEXT_PUBLIC_VAR)
 * at compile time in browser bundles. Dynamic indexing like process.env[key] does not get replaced.
 */

function validateEnv(val: string | undefined, name: string): string {
  if (!val || val.trim() === '') {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return val.trim();
}

export const ENV = {
  API_BASE_URL:
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000',
  GOOGLE_FORM_URL: validateEnv(
    process.env.NEXT_PUBLIC_GOOGLE_FORM_URL,
    'NEXT_PUBLIC_GOOGLE_FORM_URL'
  ),
  GOOGLE_SPREADSHEET_ID: validateEnv(
    process.env.NEXT_PUBLIC_GOOGLE_SPREADSHEET_ID,
    'NEXT_PUBLIC_GOOGLE_SPREADSHEET_ID'
  ),
  GOOGLE_SHEETS_WEBHOOK_URL: validateEnv(
    process.env.NEXT_PUBLIC_GOOGLE_SHEETS_WEBHOOK_URL,
    'NEXT_PUBLIC_GOOGLE_SHEETS_WEBHOOK_URL'
  ),
  REPOPILOT_VERSION: validateEnv(
    process.env.NEXT_PUBLIC_REPOPILOT_VERSION,
    'NEXT_PUBLIC_REPOPILOT_VERSION'
  ),
} as const;
