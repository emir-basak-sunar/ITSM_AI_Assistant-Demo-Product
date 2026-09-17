import { Shield } from "lucide-react";
import { FormEvent, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { BtcLogo } from "./ui/BtcLogo";

export function LoginPage() {
  const { login, llmActive, llmProvider } = useAuth();
  const [email, setEmail] = useState("admin@kurumsal.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Giriş başarısız.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen">
      {/* Sağ üst logo */}
      <div className="absolute right-6 top-6 z-10">
        <BtcLogo className="h-11 w-auto" />
      </div>

      {/* Sol panel — marka */}
      <div className="hidden w-[480px] flex-col justify-between bg-brand-700 p-12 text-white lg:flex">
        <div>
          <div className="inline-block rounded-lg bg-white px-5 py-3 shadow-sm">
            <BtcLogo className="h-10 w-auto" />
          </div>
          <h1 className="mt-12 text-3xl font-bold leading-tight">
            Kurumsal destek taleplerinizi tek platformdan yönetin
          </h1>
          <p className="mt-4 leading-relaxed text-brand-100">
            AI destekli sınıflandırma, otomatik bilet oluşturma, önceliklendirme
            ve raporlama — hepsi tek bir profesyonel arayüzde.
          </p>
        </div>

        <div className="space-y-4">
          {[
            "4 kademeli otomatik talep sınıflandırma",
            "Self-service çözüm önerileri",
            "Şema bazlı alan tamamlama",
            "Günlük analitik rapor JOB",
          ].map((item) => (
            <div key={item} className="flex items-center gap-3 text-sm text-brand-100">
              <Shield className="h-4 w-4 shrink-0 text-brand-200" />
              {item}
            </div>
          ))}
        </div>
      </div>

      {/* Sağ panel — form */}
      <div className="flex flex-1 items-center justify-center bg-surface-muted p-8 pt-20 lg:pt-8">
        <div className="card w-full max-w-md p-8">
          <div className="mb-8 flex justify-center lg:hidden">
            <BtcLogo className="h-12 w-auto" />
          </div>

          <h2 className="text-2xl font-bold text-slate-900">Hoş geldiniz</h2>
          <p className="mt-1 text-sm text-slate-500">
            Hesabınıza giriş yapın
            <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
              {llmActive ? llmProvider : "Standart Mod"}
            </span>
          </p>

          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            <label className="block space-y-1.5">
              <span className="text-sm font-medium text-slate-700">E-posta</span>
              <input
                className="input-field"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label className="block space-y-1.5">
              <span className="text-sm font-medium text-slate-700">Şifre</span>
              <input
                className="input-field"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>

            {error ? (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            ) : null}

            <button type="submit" className="btn-primary w-full !py-3" disabled={loading}>
              {loading ? "Giriş yapılıyor..." : "Giriş Yap"}
            </button>
          </form>

          <div className="mt-6 rounded-lg bg-slate-50 p-4 text-xs text-slate-500">
            <p className="font-medium text-slate-700">Demo hesaplar</p>
            <p className="mt-1">admin@kurumsal.local / admin123</p>
            <p>kullanici@kurumsal.local / kullanici123</p>
          </div>
        </div>
      </div>
    </div>
  );
}
