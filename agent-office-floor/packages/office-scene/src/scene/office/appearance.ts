import { OFFICE_CAST, type OfficeCharacterName } from './cast.ts';
/** Stable recipe assignment; business display names never come from the source cast. */
export function recipeFor(avatarKey: string): OfficeCharacterName {
  let hash = 2166136261;
  for (let i=0;i<avatarKey.length;i++) hash = Math.imul(hash ^ avatarKey.charCodeAt(i), 16777619);
  return OFFICE_CAST[(hash >>> 0) % OFFICE_CAST.length].name;
}
