// frontend/src/app/ops/layout.tsx
import { OpsQueryProvider } from "@/components/ops/query-provider";

export const metadata = { title: "Naka Ops" };

export default function OpsLayout({ children }: { children: React.ReactNode }) {
  return <OpsQueryProvider>{children}</OpsQueryProvider>;
}
