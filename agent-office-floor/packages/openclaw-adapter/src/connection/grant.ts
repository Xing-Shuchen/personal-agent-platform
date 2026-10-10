/** A shared bootstrap credential must never widen the office observer's effective grant. */
export function isReadOnlyGrant(auth: { role: string; scopes: readonly string[] }): boolean {
  return auth.role === 'operator' && auth.scopes.length === 1 && auth.scopes[0] === 'operator.read';
}
