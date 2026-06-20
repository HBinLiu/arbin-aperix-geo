/** 平台矩阵表：行标签列固定 minWidth，平台列等宽 minWidth；过窄时横向滚动。 */

export const PLATFORM_MATRIX_ROW_COLUMN_MIN = 240;
export const PLATFORM_MATRIX_PLATFORM_COLUMN_MIN = 120;

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

export const platformMatrixTableClasses = {
  row: "border-border h-11 border-t [&>td]:align-middle [&>td]:whitespace-nowrap [&>td]:px-4 [&>td]:py-0",
  skeletonRow: "border-border grid h-11 items-center border-t",
  skeletonHeader: "border-border grid h-11 items-center border-b",
} as const;
