import { Navbar } from "@/components/ui/Navbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-6xl mx-auto">
        {children}
      </main>
    </div>
  );
}
