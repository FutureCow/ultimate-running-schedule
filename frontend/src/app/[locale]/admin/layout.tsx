import { AuthGuard } from "@/components/ui/AuthGuard";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
