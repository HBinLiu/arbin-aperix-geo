import { Building2, Globe, Languages, MapPin } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import {
  SetupFieldGroup,
  SetupFieldLabel,
  SetupSelect,
  SetupTextInput,
} from "@/components/setup/SetupField";
import { SetupLoader } from "@/components/setup/SetupLoader";
import { SetupStepCompetitor } from "@/components/setup/SetupStepCompetitor";
import { SetupStepPrompt } from "@/components/setup/SetupStepPrompt";
import { SetupStepTopic } from "@/components/setup/SetupStepTopic";
import type { CompetitorRow, PromptRow, SubjectMode, TopicRow } from "@/types";
import { cn } from "@/lib/utils";

type SelectOption = { value: string; label: string; flag?: string };

type SetupStepContentView = {
  step: number;
  mode: SubjectMode;
  websiteUrl: string;
  brandName: string;
  region: string;
  language: string;
  faviconHost: string | null;
  topicRows: TopicRow[];
  competitorRows: CompetitorRow[];
  promptRows: PromptRow[];
  activeTopics: TopicRow[];
  regionOptions: SelectOption[];
  languageOptions: SelectOption[];
  analyzingProfile: boolean;
  discoveringCompetitors: boolean;
  generatingPrompts: boolean;
};

type SetupStepContentActions = {
  onModeChange: (mode: SubjectMode) => void;
  onWebsiteUrlChange: (value: string) => void;
  onBrandNameChange: (value: string) => void;
  onRegionChange: (value: string) => void;
  onLanguageChange: (value: string) => void;
  onTopicRowsChange: (rows: TopicRow[]) => void;
  onCompetitorRowsChange: (rows: CompetitorRow[]) => void;
  onPromptRowsChange: (rows: PromptRow[]) => void;
};

type SetupStepContentProps = {
  view: SetupStepContentView;
  actions: SetupStepContentActions;
};

export function SetupStepContent({ view, actions }: SetupStepContentProps) {
  const {
    step,
    mode,
    websiteUrl,
    brandName,
    region,
    language,
    faviconHost,
    topicRows,
    competitorRows,
    promptRows,
    activeTopics,
    regionOptions,
    languageOptions,
    analyzingProfile,
    discoveringCompetitors,
    generatingPrompts,
  } = view;
  const {
    onModeChange,
    onWebsiteUrlChange,
    onBrandNameChange,
    onRegionChange,
    onLanguageChange,
    onTopicRowsChange,
    onCompetitorRowsChange,
    onPromptRowsChange,
  } = actions;
  if (step === 0) {
    return (
      <>
        <div className="mb-4 grid h-9 max-w-md grid-cols-2 gap-1 rounded-lg bg-muted p-1">
          <button
            type="button"
            className={cn(
              "rounded-md text-xs font-medium transition-all sm:text-sm",
              mode === "domain"
                ? "bg-white text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onModeChange("domain")}
          >
            按网站
          </button>
          <button
            type="button"
            className={cn(
              "rounded-md text-xs font-medium transition-all sm:text-sm",
              mode === "brand"
                ? "bg-white text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onModeChange("brand")}
          >
            按品牌
          </button>
        </div>

        {mode === "domain" ? (
          <SetupFieldGroup>
            <SetupFieldLabel icon={Globe} htmlFor="wiz-url">
              网站 URL
            </SetupFieldLabel>
            <SetupTextInput
              id="wiz-url"
              value={websiteUrl}
              onChange={(e) => onWebsiteUrlChange(e.target.value)}
              placeholder="请确保网站能正常访问"
              autoComplete="url"
              leading={
                faviconHost ? (
                  <FaviconImage domain={faviconHost} size={20} className="size-5" />
                ) : (
                  <Globe className="text-muted-foreground size-5" aria-hidden />
                )
              }
            />
          </SetupFieldGroup>
        ) : (
          <SetupFieldGroup>
            <SetupFieldLabel icon={Building2} htmlFor="wiz-brand">
              品牌名称
            </SetupFieldLabel>
            <SetupTextInput
              id="wiz-brand"
              value={brandName}
              onChange={(e) => onBrandNameChange(e.target.value)}
              placeholder="例如：你的品牌简称"
              leading={<Building2 className="text-muted-foreground size-5" aria-hidden />}
            />
          </SetupFieldGroup>
        )}

        <SetupFieldGroup>
          <SetupFieldLabel icon={MapPin} htmlFor="wiz-region">
            目标地区
          </SetupFieldLabel>
          <SetupSelect id="wiz-region" value={region} onChange={onRegionChange} options={regionOptions} />
        </SetupFieldGroup>

        <SetupFieldGroup>
          <SetupFieldLabel icon={Languages} htmlFor="wiz-lang">
            语言
          </SetupFieldLabel>
          <SetupSelect id="wiz-lang" value={language} onChange={onLanguageChange} options={languageOptions} />
        </SetupFieldGroup>
      </>
    );
  }

  if (step === 1) {
    return analyzingProfile ? (
      <SetupLoader />
    ) : (
      <SetupStepTopic
        rows={topicRows}
        onChange={(rows) => {
          onTopicRowsChange(rows);
          onPromptRowsChange([]);
        }}
      />
    );
  }

  if (step === 2) {
    return discoveringCompetitors ? (
      <SetupLoader />
    ) : (
      <SetupStepCompetitor mode={mode} rows={competitorRows} onChange={onCompetitorRowsChange} />
    );
  }

  return generatingPrompts ? (
    <SetupLoader />
  ) : (
    <SetupStepPrompt rows={promptRows} topics={activeTopics} onChange={onPromptRowsChange} />
  );
}
