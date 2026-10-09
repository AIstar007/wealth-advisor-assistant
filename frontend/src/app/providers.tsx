"use client";

import type { ReactNode } from "react";
import { CopilotKitProvider } from "@copilotkit/react-core/v2";
import "@copilotkit/react-core/v2/styles.css";
import { wealthAdvisorCatalog } from "@/lib/a2ui-catalog";

export default function Providers({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <CopilotKitProvider
      runtimeUrl="/api/copilotkit"
      a2ui={{ catalog: wealthAdvisorCatalog }}
    >
      {children}
    </CopilotKitProvider>
  );
}