import { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Clock3,
  FolderOpen,
  Loader2,
  Plus,
  Search,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { fetchApi } from "../../api/fetchWithNgrok";
import { useAuth } from "../../auth/AuthContext";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface CaseItem {
  id: string;
  title: string;
  description?: string;
  status: "processing" | "completed" | "failed";
  created_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export default function CasesPage() {
  const navigate = useNavigate();
  const { isLoading: authLoading } = useAuth();

  const API_BASE = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '')

  const [loading, setLoading]       = useState(true);
  const [cases, setCases]           = useState<CaseItem[]>([]);
  const [search, setSearch]         = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newCaseName, setNewCaseName] = useState("");

  // ── Data fetching ──────────────────────────────────────────────────

  async function loadCases() {
    try {
      setLoading(true);
      const response = await fetchApi(`${API_BASE.replace(/\/$/, '')}/api/cases`);
      const data = await response.json();
      // Backend returns { cases: [...] }
      setCases(Array.isArray(data) ? data : (data.cases ?? []));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (authLoading) return   // wait for token to be populated
    void loadCases();
  }, [authLoading]);

  async function createCase() {
    if (!newCaseName.trim()) return;
    try {
      const response = await fetchApi(`${API_BASE.replace(/\/$/, '')}/api/cases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newCaseName }),
      });
      if (!response.ok) throw new Error("Failed to create case");
      setNewCaseName("");
      setShowCreate(false);
      void loadCases();
    } catch (err) {
      console.error(err);
    }
  }

  // ── Derived state ──────────────────────────────────────────────────

  const filteredCases = useMemo(
    () => cases.filter((c) =>
      (c.title ?? "").toLowerCase().includes(search.toLowerCase())
    ),
    [cases, search],
  );

  // ── Loading spinner ────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090B] flex items-center justify-center text-white">
        <Loader2 className="animate-spin" size={40} />
      </div>
    );
  }

  // ── Main render ────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#09090B] text-white p-8">

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold">Cases</h1>
          <p className="text-zinc-400 mt-2">
            Manage enterprise compliance investigations.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-cyan-500 hover:bg-cyan-600 px-5 py-3 rounded-xl flex items-center gap-2 transition"
        >
          <Plus size={18} />
          New Case
        </button>
      </div>

      {/* Search */}
      <div className="relative mt-10">
        <Search className="absolute left-4 top-3 text-zinc-500" size={18} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search cases…"
          className="w-full rounded-xl bg-zinc-900 border border-zinc-800 py-3 pl-12 pr-4 outline-none focus:border-cyan-500 transition"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 mt-8">
        <StatCard icon={<FolderOpen className="text-cyan-400" />}    label="Total Cases"  value={cases.length} />
        <StatCard icon={<Clock3 className="text-yellow-400" />}      label="Processing"   value={cases.filter((c) => c.status === "processing").length} />
        <StatCard icon={<CheckCircle2 className="text-emerald-400" />} label="Completed"  value={cases.filter((c) => c.status === "completed").length} />
        <StatCard icon={<FolderOpen className="text-violet-400" />}  label="Active"       value={cases.length} />
      </div>

      {/* Cases grid */}
      <div className="grid xl:grid-cols-3 lg:grid-cols-2 gap-6 mt-8">
        {filteredCases.map((item) => (
          <div
            key={item.id}
            className="rounded-2xl border border-zinc-800 bg-zinc-900 hover:border-cyan-500 transition-all duration-300 flex flex-col"
          >
            {/* Card header */}
            <div className="p-6 border-b border-zinc-800 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-xl font-semibold truncate">{item.title}</h2>
                <p className="text-sm text-zinc-500 mt-1 line-clamp-2">
                  {item.description || "No description"}
                </p>
              </div>
              <span
                className={`shrink-0 px-3 py-1 rounded-full text-xs font-medium ${
                  item.status === "completed"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : item.status === "processing"
                    ? "bg-yellow-500/10 text-yellow-400"
                    : "bg-red-500/10 text-red-400"
                }`}
              >
                {item.status}
              </span>
            </div>

            {/* Meta */}
            <div className="grid grid-cols-2 gap-4 p-6 flex-1">
              <div>
                <p className="text-xs text-zinc-500">Case ID</p>
                <p className="text-xs font-mono text-zinc-400 mt-1 truncate">
                  {item.id.slice(0, 16)}…
                </p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">Created</p>
                <p className="text-xs mt-1">
                  {new Date(item.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="border-t border-zinc-800 p-5 flex gap-3">
              <button
                onClick={() => {
                  localStorage.setItem("innova_active_case_id", item.id);
                  navigate(`/app/cases/${item.id}`);
                }}
                className="flex-1 rounded-xl bg-cyan-500 hover:bg-cyan-600 py-2.5 text-sm font-medium transition"
              >
                Open
              </button>
              <button
                onClick={() => {
                  localStorage.setItem("innova_active_case_id", item.id);
                  navigate("/app/upload");
                }}
                className="flex-1 rounded-xl border border-zinc-700 hover:border-cyan-500 py-2.5 text-sm transition"
              >
                Upload
              </button>
              <button
                onClick={() => {
                  localStorage.setItem("innova_active_case_id", item.id);
                  navigate("/app/ai-assistant");
                }}
                className="flex-1 rounded-xl border border-zinc-700 hover:border-emerald-500 py-2.5 text-sm transition"
              >
                Ask AI
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {filteredCases.length === 0 && (
        <div className="mt-16 rounded-2xl border border-dashed border-zinc-700 p-16 text-center">
          <FolderOpen size={60} className="mx-auto text-zinc-600" />
          <h2 className="text-2xl font-semibold mt-6">No Cases Found</h2>
          <p className="text-zinc-500 mt-3">Create your first investigation case.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-8 bg-cyan-500 hover:bg-cyan-600 px-6 py-3 rounded-xl transition"
          >
            Create Case
          </button>
        </div>
      )}

      {/* Footer */}
      <div className="mt-10 flex items-center justify-between text-sm text-zinc-500">
        <span>Showing {filteredCases.length} of {cases.length} case(s)</span>
        <button
          onClick={() => void loadCases()}
          className="rounded-lg border border-zinc-700 px-4 py-2 hover:border-cyan-500 hover:text-cyan-400 transition"
        >
          Refresh
        </button>
      </div>

      {/* Create case modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="w-full max-w-md rounded-2xl bg-zinc-900 border border-zinc-800 p-6">
            <h2 className="text-2xl font-bold">New Investigation Case</h2>
            <input
              value={newCaseName}
              onChange={(e) => setNewCaseName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void createCase(); }}
              placeholder="Case name…"
              className="mt-6 w-full rounded-xl bg-zinc-950 border border-zinc-700 px-4 py-3 outline-none focus:border-cyan-500 transition"
              autoFocus
            />
            <div className="flex justify-end gap-3 mt-8">
              <button
                onClick={() => setShowCreate(false)}
                className="px-5 py-3 rounded-xl border border-zinc-700 hover:bg-zinc-800 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => void createCase()}
                className="px-5 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-600 transition"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Stat card
// ─────────────────────────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
      <div className="mb-4">{icon}</div>
      <p className="text-zinc-400">{label}</p>
      <h2 className="text-4xl font-bold mt-3">{value}</h2>
    </div>
  );
}
