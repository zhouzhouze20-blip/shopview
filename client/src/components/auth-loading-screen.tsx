import { Loader2, ShieldCheck } from "lucide-react";

export default function AuthLoadingScreen() {
  return (
    <main className="grid min-h-screen min-h-[100dvh] place-items-center bg-slate-950 px-6 text-white">
      <div className="text-center">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl border border-teal-300/30 bg-teal-400/10 shadow-[0_18px_50px_rgba(13,148,136,0.2)]">
          <ShieldCheck className="h-8 w-8 text-teal-300" />
        </div>
        <h1 className="mt-6 text-xl font-semibold tracking-wide">ShopView</h1>
        <div className="mt-4 inline-flex items-center gap-2 text-sm text-slate-300">
          <Loader2 className="h-4 w-4 animate-spin text-teal-300" />
          <span>正在安全进入工作台…</span>
        </div>
      </div>
    </main>
  );
}
