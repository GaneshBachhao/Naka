// frontend/src/app/ops/(console)/layout.tsx
import { AuthGate } from "@/components/ops/auth-gate";
import { ConsoleShell } from "@/components/ops/console-shell";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <ConsoleShell>{children}</ConsoleShell>
    </AuthGate>
  );
}
