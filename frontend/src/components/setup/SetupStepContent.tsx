import { Boxes, Globe, Languages, MapPin } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import { resolveFaviconInput } from "@/lib/favicon";
import {
  SetupFieldGroup,
  SetupFieldLabel,
  SetupSelect,
  SetupTextInput,
} from "@/components/setup/SetupField";
import { SetupLoader } from "@/components/setup/SetupLoader";
import { SetupStepCompetitor } from "@/components/setup/SetupStepCompetitor";
import { SetupStepMaterials } from "@/components/setup/SetupStepMaterials";
import { SetupStepPrompt } from "@/components/setup/SetupStepPrompt";
import { SetupStepTopic } from "@/components/setup/SetupStepTopic";
import { setupCompetitorStep, setupTopicsStep } from "@/lib/setup";
import type { CompetitorRow, PromptRow, SetupUploadFile, SubjectMode, TopicRow } from "@/types";
import { cn } from "@/lib/utils";

type SelectOption = { value: string; label: string; flag?: string };

type SetupStepContentView = {
  step: number;
  mode: SubjectMode;
  websiteUrl: string;
  brandName: string;
  brandIntro: string;
  brandWebsiteUrl: string;
  uploadFiles: SetupUploadFile[];
  region: string;
  language: string;
  topicRows: TopicRow[];
  competitorRows: CompetitorRow[];
  promptRows: PromptRow[];
  activeTopics: TopicRow[];
  regionOptions: SelectOption[];
  languageOptions: SelectOption[];
  analyzingProfile: boolean;
  discoveringCompetitors: boolean;
  loadingTopics: boolean;
  generatingPrompts: boolean;
  uploadingFiles: boolean;
};

type SetupStepContentActions = {
  onModeChange: (mode: SubjectMode) => void;
  onWebsiteUrlChange: (value: string) => void;
  onBrandNameChange: (value: string) => void;
  onBrandIntroChange: (value: string) => void;
  onBrandWebsiteUrlChange: (value: string) => void;
  onUploadFiles: (files: FileList | null) => void;
  onRemoveUploadFile: (fileId: string) => void;
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
    brandIntro,
    brandWebsiteUrl,
    uploadFiles,
    region,
    language,
    topicRows,
    competitorRows,
    promptRows,
    activeTopics,
    regionOptions,
    languageOptions,
    analyzingProfile,
    discoveringCompetitors,
    loadingTopics,
    generatingPrompts,
    uploadingFiles,
  } = view;
  const {
    onModeChange,
    onWebsiteUrlChange,
    onBrandNameChange,
    onBrandIntroChange,
    onBrandWebsiteUrlChange,
    onUploadFiles,
    onRemoveUploadFile,
    onRegionChange,
    onLanguageChange,
    onTopicRowsChange,
    onCompetitorRowsChange,
    onPromptRowsChange,
  } = actions;

  const competitorStep = setupCompetitorStep(mode);
  const topicsStep = setupTopicsStep(mode);

  if (step === 0) {
    return (
      <>
        <div className="mb-4 grid h-9 max-w-md grid-cols-2 gap-1 rounded-lg bg-background p-1">
          <button
            type="button"
            className={cn(
              "rounded-md text-xs font-medium transition-all sm:text-sm",
              mode === "domain"
                ? "bg-muted-background text-foreground shadow-xs"
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
                ? "bg-muted-background text-foreground shadow-xs"
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
                resolveFaviconInput(websiteUrl) ? (
                  <FaviconImage url={websiteUrl} size={20} className="size-5" />
                ) : (
                  <Globe className="text-muted-foreground size-5" aria-hidden />
                )
              }
            />
          </SetupFieldGroup>
        ) : (
          <SetupFieldGroup>
            <SetupFieldLabel icon={Boxes} htmlFor="wiz-brand">
              品牌名称
            </SetupFieldLabel>
            <SetupTextInput
              id="wiz-brand"
              value={brandName}
              onChange={(e) => onBrandNameChange(e.target.value)}
              placeholder="该名称将用于品牌的识别，请准确填写"
              leading={<Boxes className="text-muted-foreground size-5" aria-hidden />}
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
            目标语言
          </SetupFieldLabel>
          <SetupSelect id="wiz-lang" value={language} onChange={onLanguageChange} options={languageOptions} />
        </SetupFieldGroup>
      </>
    );
  }

  if (mode === "brand" && step === 1) {
    return analyzingProfile || discoveringCompetitors ? (
      <SetupLoader />
    ) : (
      <SetupStepMaterials
        brandWebsiteUrl={brandWebsiteUrl}
        brandIntro={brandIntro}
        uploadFiles={uploadFiles}
        uploading={uploadingFiles}
        onBrandWebsiteUrlChange={onBrandWebsiteUrlChange}
        onBrandIntroChange={onBrandIntroChange}
        onUploadFiles={onUploadFiles}
        onRemoveFile={onRemoveUploadFile}
      />
    );
  }

  if (step === competitorStep) {
    return analyzingProfile || discoveringCompetitors ? (
      <SetupLoader />
    ) : (
      <SetupStepCompetitor mode={mode} rows={competitorRows} onChange={onCompetitorRowsChange} />
    );
  }

  if (step === topicsStep) {
    return generatingPrompts || loadingTopics ? (
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

  return (
    <SetupStepPrompt rows={promptRows} topics={activeTopics} onChange={onPromptRowsChange} />
  );
}
