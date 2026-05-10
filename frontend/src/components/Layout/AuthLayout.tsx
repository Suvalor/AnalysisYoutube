import { ReactNode } from "react";

type AuthLayoutProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export default function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/30 via-sky-500/10 to-emerald-500/20 blur-3xl opacity-70 pointer-events-none" />
      <div className="relative z-10 w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-2xl bg-indigo-500 text-white font-bold text-xl shadow-lg shadow-indigo-500/40">
            C
          </div>
          <h1 className="mt-4 text-2xl font-semibold text-slate-50">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-yc-text-tertiary">{subtitle}</p>}
        </div>
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/80 shadow-2xl shadow-black/40 backdrop-blur-lg p-6">
          {children}
        </div>
      </div>
    </div>
  );
}

