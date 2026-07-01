import * as React from "react";
import { Plus, Trash2 } from "lucide-react";

import { FaviconUrlInput } from "@/components/common/FaviconUrlInput";
import { Button } from "@/components/ui/button";
import { Input, InputGroup } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import { maxCompetitorsPerSubject } from "@/lib/billing/limits";
import {
  competitorDuplicateMessage,
  findCompetitorDuplicate,
  newCompetitorRow,
  type SubjectIdentity,
} from "@/lib/setup";
import { registrableDomain, websiteUrlFromInput } from "@/lib/domain";
import { toast } from "@/lib/toast";
import type { CompetitorRow, SubjectMode } from "@/types";
import { cn } from "@/lib/utils";

type SetupStepCompetitorProps = {
  mode: SubjectMode;
  subject: SubjectIdentity;
  rows: CompetitorRow[];
  onChange: (rows: CompetitorRow[]) => void;
};

/** 三列轨道：竞品名称 | 主域名 | Checkbox+删除 */
const COMPETITOR_COLS = "grid-cols-[minmax(0,12.5rem)_minmax(0,1fr)_auto]" as const;

const competitorTableGrid = cn("grid w-full items-center gap-x-4 gap-y-1", COMPETITOR_COLS);

const competitorHeaderGridClass = cn("col-span-full grid gap-x-4 gap-y-1 pl-2", COMPETITOR_COLS);

const competitorRowActionsClass = "flex h-9 items-center gap-0";

const competitorCheckboxClass =
  "size-[18px] shrink-0 rounded-[4px] border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground [&_svg]:size-3";

const competitorActionCellClass =
  "flex h-9 w-9 shrink-0 items-center justify-center justify-self-center self-center";

type CompetitorTableProps = {
  mode: SubjectMode;
  rows: CompetitorRow[];
  draftName: string;
  draftDomain: string;
  allSelected: boolean;
  atMax: boolean;
  maxCompetitors: number;
  onDraftNameChange: (value: string) => void;
  onDraftDomainChange: (value: string) => void;
  onToggleAll: (checked: boolean) => void;
  onUpdateRow: (id: string, patch: Partial<CompetitorRow>) => void;
  onRemoveRow: (id: string) => void;
  onAddFromDraft: () => void;
};

function DomainInput({
  value,
  websiteUrl,
  onChange,
  onBlurNormalize,
  placeholder,
  ariaLabel,
  className,
  onKeyDown,
}: {
  value: string;
  websiteUrl?: string;
  onChange: (value: string) => void;
  onBlurNormalize?: (raw: string) => void;
  placeholder: string;
  ariaLabel: string;
  className?: string;
  onKeyDown?: (e: React.KeyboardEvent) => void;
}) {
  return (
    <div className={cn("border-input relative min-w-0 border-l", className)}>
      <FaviconUrlInput
        layout="merged"
        faviconMode="domain"
        websiteUrl={websiteUrl}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={
          onBlurNormalize
            ? (e) => {
                onBlurNormalize(e.target.value.trim());
              }
            : undefined
        }
        placeholder={placeholder}
        aria-label={ariaLabel}
        onKeyDown={onKeyDown}
      />
    </div>
  );
}

function CompetitorTable({
  mode,
  rows,
  draftName,
  draftDomain,
  allSelected,
  atMax,
  maxCompetitors,
  onDraftNameChange,
  onDraftDomainChange,
  onToggleAll,
  onUpdateRow,
  onRemoveRow,
  onAddFromDraft,
}: CompetitorTableProps) {
  const isDomainMode = mode === "domain";

  const handleDraftKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      onAddFromDraft();
    }
  };

  const normalizeDomain = (raw: string, onPatch: (main: string, websiteUrl: string) => void) => {
    const main = registrableDomain(raw);
    if (!main) return;
    onPatch(main, websiteUrlFromInput(raw) || raw.trim());
  };

  return (
    <div className={competitorTableGrid}>
      <div className={competitorHeaderGridClass}>
        <span className="text-foreground flex h-9 items-center text-sm font-semibold">
          竞品名称（{rows.length}/{maxCompetitors}）
        </span>
        <span className="text-foreground flex h-9 items-center text-sm font-semibold">
          主域名
        </span>
        <div className={cn(competitorRowActionsClass, "col-start-3")}>
          <div className={competitorActionCellClass}>
            <Checkbox
              checked={allSelected}
              onCheckedChange={(v) => onToggleAll(v === true)}
              aria-label="全选竞争对手"
              className={competitorCheckboxClass}
            />
          </div>
          <span aria-hidden className={cn(competitorActionCellClass, "pointer-events-none")} />
        </div>
      </div>

      <div className={cn("col-span-full grid gap-x-4 gap-y-2 pl-2", COMPETITOR_COLS)}>
        {rows.map((row) => (
          <React.Fragment key={row.id}>
            <InputGroup className="col-span-2 grid h-9 grid-cols-subgrid">
              <Input
                variant="merged"
                controlSize="sm"
                value={row.name}
                onChange={(e) => onUpdateRow(row.id, { name: e.target.value })}
                placeholder="竞品名称"
                aria-label={`${row.domain || "竞品"} 名称`}
              />
              <DomainInput
                value={row.domain}
                websiteUrl={row.websiteUrl}
                onChange={(value) => onUpdateRow(row.id, { domain: value })}
                onBlurNormalize={(raw) =>
                  normalizeDomain(raw, (main, websiteUrl) =>
                    onUpdateRow(row.id, { domain: main, websiteUrl }),
                  )
                }
                placeholder="主域名"
                ariaLabel={`${row.name || "竞品"} 主域名`}
              />
            </InputGroup>
            <div className={cn(competitorRowActionsClass, "col-start-3")}>
              <div className={competitorActionCellClass}>
                <Checkbox
                  checked={row.selected}
                  onCheckedChange={(v) => onUpdateRow(row.id, { selected: v === true })}
                  aria-label={`选择 ${row.name || row.domain}`}
                  className={competitorCheckboxClass}
                />
              </div>
              <div className={competitorActionCellClass}>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground hover:text-foreground size-9"
                  onClick={() => onRemoveRow(row.id)}
                  aria-label="删除"
                >
                  <Trash2 className="size-4 stroke-[1.5]" />
                </Button>
              </div>
            </div>
          </React.Fragment>
        ))}
      </div>

      {!atMax ? (
        <div className={cn("col-span-full grid gap-x-4 px-1.5 pt-2", COMPETITOR_COLS)}>
          <InputGroup className="col-span-2 grid h-9 grid-cols-subgrid">
            <Input
              variant="merged"
              controlSize="sm"
              value={draftName}
              onChange={(e) => onDraftNameChange(e.target.value)}
              placeholder={isDomainMode ? "填写竞品名称" : "填写竞品品牌"}
              aria-label="新竞品名称"
              onKeyDown={handleDraftKeyDown}
            />
            <DomainInput
              value={draftDomain}
              onChange={onDraftDomainChange}
              placeholder="填写网站域名"
              ariaLabel="新竞品主域名"
              onBlurNormalize={(raw) => {
                const main = registrableDomain(raw);
                if (!main) return;
                onDraftDomainChange(main);
              }}
              onKeyDown={handleDraftKeyDown}
            />
          </InputGroup>
          <div className={cn(competitorRowActionsClass, "col-start-3")}>
            <Button
              type="button"
              variant="outline"
              className="text-muted-foreground h-9 shrink-0 gap-1.5 whitespace-nowrap rounded-md bg-muted-background px-4 text-sm font-normal"
              onClick={onAddFromDraft}
            >
              <Plus className="size-4 shrink-0" />
              添加竞品
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function SetupStepCompetitor({ mode, subject, rows, onChange }: SetupStepCompetitorProps) {
  const [draftName, setDraftName] = React.useState("");
  const [draftDomain, setDraftDomain] = React.useState("");
  const { data: subscription } = useTenantSubscription();
  const maxCompetitors = maxCompetitorsPerSubject(subscription);
  const selectedCount = rows.filter((r) => r.selected).length;
  const allSelected = rows.length > 0 && rows.every((r) => r.selected);
  const atMax = rows.length >= maxCompetitors;

  const updateRow = (id: string, patch: Partial<CompetitorRow>) => {
    onChange(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const removeRow = (id: string) => {
    onChange(rows.filter((r) => r.id !== id));
  };

  const toggleAll = (checked: boolean) => {
    onChange(rows.map((r) => ({ ...r, selected: checked })));
  };

  const clearDraft = () => {
    setDraftName("");
    setDraftDomain("");
  };

  const addFromDraft = () => {
    if (atMax) return;
    const name = draftName.trim();
    const raw = draftDomain.trim();
    const main = registrableDomain(raw);

    if (mode === "domain") {
      if (!name) {
        toast.error("请填写竞品名称。");
        return;
      }
      if (!main || main.length < 3) {
        toast.error("请填写有效的竞品主域名。");
        return;
      }
      const duplicate = findCompetitorDuplicate(mode, rows, { name, domain: main }, subject);
      if (duplicate) {
        toast.error(competitorDuplicateMessage(duplicate));
        return;
      }
      onChange([
        ...rows,
        newCompetitorRow({
          name,
          domain: main,
          websiteUrl: websiteUrlFromInput(raw) || main,
          selected: true,
        }),
      ]);
    } else {
      if (!name) {
        toast.error("请填写竞品品牌名称。");
        return;
      }
      if (raw && (!main || main.length < 3)) {
        toast.error("请填写有效的竞品网站域名，或留空。");
        return;
      }
      const duplicate = findCompetitorDuplicate(
        mode,
        rows,
        {
          name,
          domain: main && main.length >= 3 ? main : "",
        },
        subject,
      );
      if (duplicate) {
        toast.error(competitorDuplicateMessage(duplicate));
        return;
      }
      onChange([
        ...rows,
        newCompetitorRow({
          name,
          domain: main && main.length >= 3 ? main : "",
          websiteUrl:
            main && main.length >= 3
              ? websiteUrlFromInput(raw) || main
              : "",
          selected: true,
        }),
      ]);
    }
    clearDraft();
  };

  return (
    <div className="flex w-full max-w-3xl flex-col gap-4">
      <CompetitorTable
        mode={mode}
        rows={rows}
        draftName={draftName}
        draftDomain={draftDomain}
        allSelected={allSelected}
        atMax={atMax}
        maxCompetitors={maxCompetitors}
        onDraftNameChange={setDraftName}
        onDraftDomainChange={setDraftDomain}
        onToggleAll={toggleAll}
        onUpdateRow={updateRow}
        onRemoveRow={removeRow}
        onAddFromDraft={addFromDraft}
      />

      <div className="text-muted-foreground flex flex-wrap items-center justify-between gap-2 pt-1 pl-2.5 text-xs">
        <span>已选择 {selectedCount} 项</span>
        <span>最多可添加 {maxCompetitors} 个竞争对手</span>
      </div>
    </div>
  );
}
