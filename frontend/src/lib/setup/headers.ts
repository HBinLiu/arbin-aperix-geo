export function setupStepHeader(
  step: number,
  flags: { analyzingProfile: boolean; discoveringCompetitors: boolean; generatingPrompts: boolean },
): { title: string; subtitle: string } | null {
  if (step === 1 && flags.analyzingProfile) {
    return {
      title: "正在生成画像",
      subtitle: "我们正在分析品牌定位，并生成检索词与监测主题。",
    };
  }
  if (step === 2 && flags.discoveringCompetitors) {
    return {
      title: "搜索竞争对手",
      subtitle: "基于您确认的检索词，正在检索并交叉验算竞品。",
    };
  }
  if (step === 3 && flags.generatingPrompts) {
    return {
      title: "正在生成提示词",
      subtitle: "我们正基于您选择的主题、竞争对手和市场分析生成个性化提示词。",
    };
  }
  if (step === 1) {
    return {
      title: "审查检索词与监测主题",
      subtitle: "检索词用于搜索竞品；监测主题用于生成 AI 提示词。请核对品牌画像并勾选要保留的项。",
    };
  }
  if (step === 2) {
    return {
      title: "你们的主要竞争对手是谁？",
      subtitle: "我们将展示您的可见度与他们的相比如何。",
    };
  }
  if (step === 3) {
    return {
      title: "查看您的初始提示词",
      subtitle:
        "您的提示词列表基于品牌画像、所选主题、目标受众与竞争格局生成，用于监测 AI 对话中的品牌可见度。",
    };
  }
  return null;
}
