export function isJobTerminal(status: string): boolean {
  return status === "succeed" || status === "partial" || status === "failed";
}
