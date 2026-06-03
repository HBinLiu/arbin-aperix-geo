import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { SetupWizard } from "@/pages/setup/SetupWizard";
import { setStoredActiveSubjectId } from "@/lib/subject";
import { dashboardNavToPath } from "@/lib/dashboard";
import { queryKeys } from "@/lib/queries";

export function SetupRoute() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const onCompleted = async (subjectId: string) => {
    setStoredActiveSubjectId(subjectId);
    await queryClient.refetchQueries({ queryKey: queryKeys.subjects });
    void queryClient.invalidateQueries({ queryKey: queryKeys.me });
    void queryClient.invalidateQueries({ queryKey: queryKeys.pipelineStatus(subjectId) });
    navigate(dashboardNavToPath("brand"), { replace: true });
  };

  return <SetupWizard onCompleted={onCompleted} />;
}
