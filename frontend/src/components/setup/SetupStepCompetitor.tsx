import * as React from "react";
import { Globe, Plus, Trash2 } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import { SetupTextInput } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import { Input, InputGroup } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  MAX_SETUP_COMPETITORS,
  newCompetitorRow,
} from "@/lib/setup";
import { registrableDomain } from "@/lib/domain";
import type { CompetitorRow, SubjectMode } from "@/types";
import { cn } from "@/lib/utils";

type SetupStepCompetitorProps = {
  mode: SubjectMode;
  rows: CompetitorRow[];
  onChange: (rows: CompetitorRow[]) => void;
};

/** 三列轨道：站点名（宽）| 主域名（窄）| Checkbox+删除 */
const COMPETITOR_COLS = "grid-cols-[minmax(0,1fr)_minmax(0,12rem)_auto]" as const;

const competitorTableGrid = cn("grid w-full items-center gap-x-4 gap-y-1", COMPETITOR_COLS);

const competitorHeaderGridClass = cn("col-span-full grid gap-x-4 gap-y-1 pl-2", COMPETITOR_COLS);

const competitorRowActionsClass = "flex h-9 items-center gap-0";

const competitorCheckboxClass =
  "size-[18px] shrink-0 rounded-[4px] border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground [&_svg]:size-3";

const competitorActionCellClass =
  "flex h-9 w-9 shrink-0 items-center justify-center justify-self-center self-center";

type CompetitorDomainTableProps = {
  rows: CompetitorRow[];
  draftDomain: string;
  allSelected: boolean;
  atMax: boolean;
  onDraftDomainChange: (value: string) => void;
  onToggleAll: (checked: boolean) => void;
  onUpdateRow: (id: string, patch: Partial<CompetitorRow>) => void;
  onRemoveRow: (id: string) => void;
  onAddFromDraft: () => void;
};

function CompetitorDomainTable({
  rows,
  draftDomain,
  allSelected,
  atMax,
  onDraftDomainChange,
  onToggleAll,
  onUpdateRow,
  onRemoveRow,
  onAddFromDraft,
}: CompetitorDomainTableProps) {
  return (
    <div className={competitorTableGrid}>
      <div className={competitorHeaderGridClass}>
        <span className="text-foreground flex h-9 items-center text-sm font-semibold">
          站点名称（{rows.length}/{MAX_SETUP_COMPETITORS}）
        </span>
        <span className="text-foreground flex h-9 items-center text-sm font-semibold">主域名</span>
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
                placeholder="站点名称"
                aria-label={`${row.domain || "竞品"} 站点名称`}
              />
              <div className="border-input relative min-w-0 border-l">
                <div className="pointer-events-none absolute top-1/2 left-2.5 flex -translate-y-1/2 items-center">
                  <FaviconImage domain={row.domain} size={20} iconClassName="size-5" />
                </div>
                <Input
                  variant="merged"
                  controlSize="sm"
                  value={row.domain}
                  onChange={(e) => onUpdateRow(row.id, { domain: e.target.value })}
                  onBlur={(e) => {
                    const main = registrableDomain(e.target.value);
                    if (main && main !== row.domain) {
                      onUpdateRow(row.id, { domain: main });
                    }
                  }}
                  placeholder="主域名"
                  aria-label={`${row.name || "竞品"} 主域名`}
                  className="w-full pl-10"
                />
              </div>
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
        <div className="col-span-full flex w-full items-center gap-x-4 px-1.5 pt-2">
          <SetupTextInput
            value={draftDomain}
            onChange={(e) => onDraftDomainChange(e.target.value)}
            placeholder="输入竞品主域名"
            leading={<Globe className="text-muted-foreground size-5" aria-hidden />}
            containerClassName="min-w-0 flex-1 basis-0"
            className="w-full"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                onAddFromDraft();
              }
            }}
          />
          <Button
            type="button"
            variant="outline"
            className="text-muted-foreground h-9 shrink-0 gap-1.5 whitespace-nowrap rounded-md bg-white px-4 text-sm font-normal"
            onClick={onAddFromDraft}
          >
            <Plus className="size-4 shrink-0" />
            添加竞争对手
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function CompetitorBrandTable({
  rows,
  allSelected,
  atMax,
  onToggleAll,
  onUpdateRow,
  onRemoveRow,
  onAddBrandRow,
}: {
  rows: CompetitorRow[];
  allSelected: boolean;
  atMax: boolean;
  onToggleAll: (checked: boolean) => void;
  onUpdateRow: (id: string, patch: Partial<CompetitorRow>) => void;
  onRemoveRow: (id: string) => void;
  onAddBrandRow: () => void;
}) {
  return (
    <div className={cn(competitorTableGrid, "grid-cols-[minmax(0,1fr)_auto]")}>
      <div className="text-muted-foreground flex min-h-9 items-center justify-between px-0.5 text-xs font-medium">
        <span>竞品品牌 ({rows.length}/{MAX_SETUP_COMPETITORS})</span>
        <div className={competitorRowActionsClass}>
          <div className={competitorActionCellClass}>
            <Checkbox
              checked={allSelected}
              onCheckedChange={(v) => onToggleAll(v === true)}
              aria-label="全选竞品品牌"
              className={competitorCheckboxClass}
            />
          </div>
          <span aria-hidden className={cn(competitorActionCellClass, "pointer-events-none")} />
        </div>
      </div>

      {rows.map((row) => (
        <React.Fragment key={row.id}>
          <Input
            controlSize="sm"
            value={row.name}
            onChange={(e) => onUpdateRow(row.id, { name: e.target.value })}
            placeholder="竞品品牌名称"
          />
          <div className={competitorRowActionsClass}>
            <div className={competitorActionCellClass}>
              <Checkbox
                checked={row.selected}
                onCheckedChange={(v) => onUpdateRow(row.id, { selected: v === true })}
                className={competitorCheckboxClass}
              />
            </div>
            <div className={competitorActionCellClass}>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-muted-foreground size-9"
                onClick={() => onRemoveRow(row.id)}
                aria-label="删除"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          </div>
        </React.Fragment>
      ))}

      {!atMax ? (
        <Button
          type="button"
          variant="outline"
          className="text-muted-foreground col-span-2 h-9 w-fit gap-1.5 rounded-md px-4 text-sm font-normal"
          onClick={onAddBrandRow}
        >
          <Plus className="size-4" />
          添加竞争对手
        </Button>
      ) : null}
    </div>
  );
}

export function SetupStepCompetitor({ mode, rows, onChange }: SetupStepCompetitorProps) {
  const [draftDomain, setDraftDomain] = React.useState("");
  const selectedCount = rows.filter((r) => r.selected).length;
  const allSelected = rows.length > 0 && rows.every((r) => r.selected);
  const atMax = rows.length >= MAX_SETUP_COMPETITORS;

  const updateRow = (id: string, patch: Partial<CompetitorRow>) => {
    onChange(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const removeRow = (id: string) => {
    onChange(rows.filter((r) => r.id !== id));
  };

  const toggleAll = (checked: boolean) => {
    onChange(rows.map((r) => ({ ...r, selected: checked })));
  };

  const addFromDraft = () => {
    const main = registrableDomain(draftDomain);
    if (!main || main.length < 3 || atMax) return;
    if (rows.some((r) => registrableDomain(r.domain) === main)) {
      setDraftDomain("");
      return;
    }
    onChange([
      ...rows,
      newCompetitorRow({
        name: main,
        domain: main,
        selected: true,
      }),
    ]);
    setDraftDomain("");
  };

  const addBrandRow = () => {
    if (atMax) return;
    onChange([...rows, newCompetitorRow({ name: "", selected: true })]);
  };

  return (
    <div className="flex w-full max-w-3xl flex-col gap-4">
      {mode === "domain" ? (
        <CompetitorDomainTable
          rows={rows}
          draftDomain={draftDomain}
          allSelected={allSelected}
          atMax={atMax}
          onDraftDomainChange={setDraftDomain}
          onToggleAll={toggleAll}
          onUpdateRow={updateRow}
          onRemoveRow={removeRow}
          onAddFromDraft={addFromDraft}
        />
      ) : (
        <CompetitorBrandTable
          rows={rows}
          allSelected={allSelected}
          atMax={atMax}
          onToggleAll={toggleAll}
          onUpdateRow={updateRow}
          onRemoveRow={removeRow}
          onAddBrandRow={addBrandRow}
        />
      )}

      <div className="text-muted-foreground flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
        <span>已选择 {selectedCount} 项</span>
        <span>最多可添加 {MAX_SETUP_COMPETITORS} 个竞争对手。</span>
      </div>
    </div>
  );
}
