export function setupStepHeader(
  step: number,
  flags: { analyzingProfile: boolean; discoveringCompetitors: boolean; generatingPrompts: boolean },
): { title: string; subtitle: string } | null {
  if (step === 1 && flags.analyzingProfile) {
    return {
      title: "正在生成主题",
      subtitle: "我们正在分析您的品牌定位，并生成主题关键词。",
    };
  }
  if (step === 2 && flags.discoveringCompetitors) {
    return {
      title: "搜索竞争对手",
      subtitle: "基于您确认的主题关键词，正在检索并交叉验算竞品。",
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
      title: "审查已生成的主题",
      subtitle: "我们已根据您的品牌定位生成主题。请选择您要用于搜索竞品和生成提示词的主题。",
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
