// Validation regexes for the create-config form (PRD §6.5).
//
//   Project: `^[a-z0-9][a-z0-9-_]*$` (max 255)
//   Key:     `^[a-z0-9][a-z0-9-_.]*$` (max 255)
//
// Both require a leading lowercase alphanumeric; subsequent chars may
// include `-` `_` and (for keys) `.`. We keep these in sync with the
// backend Pydantic models — Task 4 uses TextField so there's no
// server-side regex enforcement yet, but the frontend enforces them
// anyway so users get immediate feedback.

export const PROJECT_REGEX = /^[a-z0-9][a-z0-9-_]*$/;
export const KEY_REGEX = /^[a-z0-9][a-z0-9-_.]*$/;
export const MAX_NAME_LENGTH = 255;

export function validateProject(value: string): string | null {
  if (value.length === 0) return "Project is required";
  if (value.length > MAX_NAME_LENGTH) {
    return `Project must be ${MAX_NAME_LENGTH} characters or fewer`;
  }
  if (!PROJECT_REGEX.test(value)) {
    return "Project must start with a lowercase letter or digit and contain only lowercase letters, digits, hyphens, or underscores";
  }
  return null;
}

export function validateKey(value: string): string | null {
  if (value.length === 0) return "Key is required";
  if (value.length > MAX_NAME_LENGTH) {
    return `Key must be ${MAX_NAME_LENGTH} characters or fewer`;
  }
  if (!KEY_REGEX.test(value)) {
    return "Key must start with a lowercase letter or digit and contain only lowercase letters, digits, hyphens, underscores, or dots";
  }
  return null;
}

export function validateValue(value: string): string | null {
  if (value.length === 0) return "Value is required";
  return null;
}
