/** 在 2 / 3 列之间选择，避免 pillar 最后一行只剩 1 个 */
export function solutionPillarColumns(count: number): 2 | 3 {
  if (count <= 2) return 2;
  if (count === 3) return 3;
  if (count % 3 === 0) return 3;
  if (count % 3 === 1) return 2;
  return count % 2 === 0 ? 2 : 3;
}
