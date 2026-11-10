/** A fresh Idempotency-Key. Generate ONE per form submission attempt and reuse it on retries,
 *  so a retry after a timeout can never create a duplicate record. */
export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
