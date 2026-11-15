/**
 * Identity of a file across path pairs.
 *
 * A bare file name is only unique within one pair, so every map, index and
 * selection set in the file list is keyed by pair and name. Files without a
 * pair (a single, legacy setup) keep their bare name as the key.
 */
export function fileKey(pairId: string | null | undefined, name: string): string {
    return pairId ? `${pairId}\u0000${name}` : name;
}
