/** 平台矩阵表：行标签列固定 minWidth，平台列等宽 minWidth；过窄时横向滚动。 */

export const PLATFORM_MATRIX_ROW_COLUMN_MIN = 200;
export const PLATFORM_MATRIX_PLATFORM_COLUMN_MIN = 156;

export function platformMatrixTableMinWidth(platformCount: number): number {
  return (
    PLATFORM_MATRIX_ROW_COLUMN_MIN +
    Math.max(platformCount, 1) * PLATFORM_MATRIX_PLATFORM_COLUMN_MIN
  );
}

export function platformMatrixSkeletonGridColumns(platformCount: number): string {
  const count = Math.max(platformCount, 1);
  return `${PLATFORM_MATRIX_ROW_COLUMN_MIN}px repeat(${count}, ${PLATFORM_MATRIX_PLATFORM_COLUMN_MIN}px)`;
}
