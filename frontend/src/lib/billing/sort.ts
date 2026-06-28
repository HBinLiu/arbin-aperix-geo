export type BillingSortDir = "asc" | "desc" | "default";

export type BillingSortState<T extends string> = {
  column: T;
  dir: BillingSortDir;
};

export function cycleBillingSort<T extends string>(
  state: BillingSortState<T>,
  column: T,
): BillingSortState<T> {
  if (state.column !== column || state.dir === "default") {
    return { column, dir: "asc" };
  }
  if (state.dir === "asc") {
    return { column, dir: "desc" };
  }
  return { column, dir: "default" };
}

export function billingSortParams<T extends string>(
  state: BillingSortState<T>,
  defaultColumn: T,
): { sortBy: T; order: "asc" | "desc" } {
  if (state.dir === "default") {
    return { sortBy: defaultColumn, order: "desc" };
  }
  return { sortBy: state.column, order: state.dir };
}
