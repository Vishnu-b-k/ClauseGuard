"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence, useScroll, useTransform } from "framer-motion";
import {
  Scale, Upload, FileText, AlertTriangle, CheckCircle,
  Fingerprint, FolderOpen, Lock, Shield, Terminal,
  ArrowRight, ChevronRight, Zap, Search, Database,
  ShieldCheck, Eye, Activity, X
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { analyzeContract, checkContractStatus } from "@/lib/api";
import { useRouter } from "next/navigation";

// ─────────────────────────────────────────────
// PARTICLE CANVAS — subtle floating dust
// ─────────────────────────────────────────────
function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const particles: { x: number; y: number; r: number; vx: number; vy: number; alpha: number }[] = [];
    for (let i = 0; i < 60; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.2 + 0.3,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.15,
        alpha: Math.random() * 0.25 + 0.05,
      });
    }
    let animId: number;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(212,175,55,${p.alpha})`;
        ctx.fill();
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
      });
      animId = requestAnimationFrame(draw);
    };
    draw();
    const onResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", onResize);
    return () => { cancelAnimationFrame(animId); window.removeEventListener("resize", onResize); };
  }, []);
  return <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none z-0 opacity-60" />;
}

// ─────────────────────────────────────────────
// TYPING TERMINAL
// ─────────────────────────────────────────────
const TERMINAL_LINES = [
  { text: "$ clauseguard --init investigation", color: "#D4AF37" },
  { text: "  Connecting to legal precedent database...", color: "#9A9A9A" },
  { text: "  Qdrant hybrid search — ONLINE", color: "#22c55e" },
  { text: "  Parsing clause sub-structure...", color: "#9A9A9A" },
  { text: "  [ALERT] HIGH RISK in §4.2 — Indemnification", color: "#ef4444" },
  { text: "  Cross-referencing policy matrix...", color: "#9A9A9A" },
  { text: "  [ALERT] CRITICAL — Uncapped liability exposure", color: "#ef4444" },
  { text: "  Generating compliant redline suggestion...", color: "#9A9A9A" },
  { text: "  ✓ Protective clause drafted", color: "#22c55e" },
  { text: "  Dispatching to human review workspace...", color: "#9A9A9A" },
  { text: "$ Investigation complete. 3 risks escalated.", color: "#D4AF37" },
];

function TypingTerminal() {
  const [displayedLines, setDisplayedLines] = useState<typeof TERMINAL_LINES>([]);
  const [lineIdx, setLineIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [currentText, setCurrentText] = useState("");
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (lineIdx >= TERMINAL_LINES.length) {
      const reset = setTimeout(() => {
        setDisplayedLines([]);
        setLineIdx(0);
        setCharIdx(0);
        setCurrentText("");
      }, 4000);
      return () => clearTimeout(reset);
    }
    const line = TERMINAL_LINES[lineIdx];
    if (charIdx < line.text.length) {
      const t = setTimeout(() => {
        setCurrentText(line.text.slice(0, charIdx + 1));
        setCharIdx(c => c + 1);
      }, 28);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(() => {
        setDisplayedLines(prev => [...prev, { text: currentText, color: line.color }]);
        setLineIdx(i => i + 1);
        setCharIdx(0);
        setCurrentText("");
      }, 180);
      return () => clearTimeout(t);
    }
  }, [lineIdx, charIdx, currentText]);

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [displayedLines, currentText]);

  return (
    <div className="bg-[#050505] border border-[#1a1a1a] h-full flex flex-col">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-[#1a1a1a]">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E]" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#28C840]" />
        </div>
        <span className="font-mono text-[10px] text-[#444] uppercase tracking-widest ml-2">CLAUSEGUARD // INVESTIGATION_ACTIVE</span>
      </div>
      <div ref={terminalRef} className="flex-1 p-5 overflow-hidden space-y-1 font-mono text-xs leading-relaxed">
        {displayedLines.map((l, i) => (
          <div key={i} style={{ color: l.color }}>{l.text}</div>
        ))}
        {lineIdx < TERMINAL_LINES.length && (
          <div style={{ color: TERMINAL_LINES[lineIdx].color }}>
            {currentText}<span className="animate-pulse">█</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// ANIMATED WORKFLOW TIMELINE
// ─────────────────────────────────────────────
const WORKFLOW_STEPS = [
  { id: "01", label: "UPLOAD", sub: "PDF / DOCX / TXT", icon: Upload },
  { id: "02", label: "PARSE", sub: "Clause extraction", icon: FileText },
  { id: "03", label: "AI ANALYSIS", sub: "Google ADK agents", icon: Zap },
  { id: "04", label: "PRECEDENT SEARCH", sub: "Qdrant hybrid RAG", icon: Search },
  { id: "05", label: "POLICY VALIDATION", sub: "Deterministic rules", icon: ShieldCheck },
  { id: "06", label: "REDLINE", sub: "Protective rewrites", icon: Activity },
  { id: "07", label: "FINAL REPORT", sub: "Human review workspace", icon: CheckCircle },
];

function WorkflowTimeline() {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setActive(a => (a + 1) % WORKFLOW_STEPS.length), 1800);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="relative">
      {/* Connector line */}
      <div className="hidden lg:block absolute top-[28px] left-0 right-0 h-[1px] bg-[#1e1e1e] z-0" />
      <motion.div
        className="hidden lg:block absolute top-[28px] left-0 h-[1px] bg-gradient-to-r from-[#D4AF37] to-[#D4AF3755] z-0"
        animate={{ width: `${((active + 1) / WORKFLOW_STEPS.length) * 100}%` }}
        transition={{ duration: 0.8, ease: "easeInOut" }}
      />

      <div className="grid grid-cols-2 lg:grid-cols-7 gap-4 relative z-10">
        {WORKFLOW_STEPS.map((step, i) => {
          const Icon = step.icon;
          const isActive = i <= active;
          const isCurrent = i === active;
          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.07 }}
              className="flex flex-col items-center text-center"
            >
              <motion.div
                animate={{
                  borderColor: isCurrent ? "#D4AF37" : isActive ? "#D4AF3780" : "#222",
                  backgroundColor: isCurrent ? "#D4AF3715" : "#0a0a0a",
                  boxShadow: isCurrent ? "0 0 16px #D4AF3740" : "none",
                }}
                transition={{ duration: 0.4 }}
                className="w-14 h-14 border flex items-center justify-center mb-3"
              >
                <Icon className={`w-5 h-5 transition-colors duration-300 ${isActive ? "text-[#D4AF37]" : "text-[#333]"}`} strokeWidth={1.5} />
              </motion.div>
              <span className={`font-mono text-[9px] tracking-widest uppercase transition-colors duration-300 ${isActive ? "text-[#D4AF37]" : "text-[#333]"}`}>{step.id}</span>
              <span className={`font-mono text-[10px] font-bold mt-1 transition-colors duration-300 ${isActive ? "text-[#F5F5F5]" : "text-[#444]"}`}>{step.label}</span>
              <span className="font-mono text-[9px] text-[#555] mt-0.5 leading-tight">{step.sub}</span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// AGENT DOSSIER CARD
// ─────────────────────────────────────────────
const AGENTS = [
  {
    codename: "COUNSEL",
    id: "AGT-99-ALPHA",
    role: "Legal Intelligence",
    clearance: "LEVEL 5 — TOP SECRET",
    confidence: "96%",
    model: "Google Gemini Flash",
    lastAnalysis: "3 min ago",
    status: "ACTIVE",
    tasks: ["Clause interrogation", "Risk classification", "Evidence citation"],
  },
  {
    codename: "LEX",
    id: "AGT-22-BRAVO",
    role: "Redline & Policy Synthesis",
    clearance: "LEVEL 5 — TOP SECRET",
    confidence: "99%",
    model: "Google Gemini Flash",
    lastAnalysis: "3 min ago",
    status: "ACTIVE",
    tasks: ["Redline generation", "Policy enforcement", "Executive summary"],
  },
];

function AgentDossier({ agent }: { agent: typeof AGENTS[0] }) {
  const [hovered, setHovered] = useState(false);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="relative border border-[#1e1e1e] bg-[#0a0a0a] p-8 overflow-hidden cursor-default group transition-all duration-500 hover:border-[#D4AF3740]"
    >
      {/* Fingerprint BG */}
      <Fingerprint className="absolute -right-8 -bottom-8 w-56 h-56 transition-all duration-700 text-[#D4AF37]"
        style={{ opacity: hovered ? 0.04 : 0.015 }} />

      {/* Status Badge */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <div className="font-mono text-[10px] text-[#555] tracking-widest mb-2">CLASSIFIED PERSONNEL FILE</div>
          <h3 className="font-heading text-4xl text-[#F5F5F5] tracking-wide">{agent.codename}</h3>
          <div className="font-mono text-[10px] text-[#666] mt-1">{agent.id}</div>
        </div>
        <motion.div
          animate={{ opacity: [1, 0.4, 1] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className="flex items-center gap-2 border border-[#D4AF3740] px-3 py-1.5"
        >
          <div className="w-1.5 h-1.5 rounded-full bg-[#22c55e]" />
          <span className="font-mono text-[9px] text-[#D4AF37] tracking-widest">{agent.status}</span>
        </motion.div>
      </div>

      {/* Data Grid */}
      <div className="space-y-3 font-mono text-xs">
        {[
          ["ROLE", agent.role],
          ["SECURITY CLEARANCE", agent.clearance],
          ["AI MODEL", agent.model],
          ["CONFIDENCE SCORE", agent.confidence],
          ["LAST ANALYSIS", agent.lastAnalysis],
        ].map(([label, value]) => (
          <div key={label} className="grid grid-cols-2 gap-4 border-b border-[#111] pb-3 last:border-0">
            <span className="text-[#555] uppercase tracking-wider text-[9px]">{label}</span>
            <span className={`text-[#ccc] ${label === "CONFIDENCE SCORE" ? "text-[#D4AF37] font-bold" : ""}`}>{value}</span>
          </div>
        ))}
      </div>

      {/* Tasks */}
      <div className="mt-6 pt-4 border-t border-[#111]">
        <div className="font-mono text-[9px] text-[#555] uppercase tracking-widest mb-3">Authorized Operations</div>
        <div className="flex flex-wrap gap-2">
          {agent.tasks.map(t => (
            <span key={t} className="font-mono text-[9px] border border-[#222] px-2 py-1 text-[#888] uppercase tracking-wider">{t}</span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────
// CASE STUDY FILES
// ─────────────────────────────────────────────
const CASES = [
  {
    ref: "CG-4421",
    title: "M&A Agreement",
    pages: 46,
    risks: 18,
    type: "CRITICAL",
    finding: "Unlimited liability clause detected in §7.3",
    exposure: "$4.2M",
    outcome: "Protective cap language generated",
  },
  {
    ref: "CG-3887",
    title: "Employment Agreement",
    pages: 12,
    risks: 9,
    type: "HIGH",
    finding: "Non-compete scope exceeds jurisdictional limits",
    exposure: "$820K",
    outcome: "Compliant territorial restrictions drafted",
  },
  {
    ref: "CG-5503",
    title: "Vendor Contract",
    pages: 28,
    risks: 14,
    type: "CRITICAL",
    finding: "Auto-renewal with no termination right in §11.2",
    exposure: "$2.1M",
    outcome: "Exit clause and notice period inserted",
  },
];

function CaseFile({ c, delay }: { c: typeof CASES[0]; delay: number }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay }}
      className="relative border border-[#1e1e1e] bg-[#0a0a0a] overflow-hidden group cursor-pointer hover:border-[#D4AF3740] transition-all duration-300"
      onClick={() => setOpen(!open)}
    >
      {/* Tab */}
      <div className="absolute top-0 left-6 w-16 h-1 bg-[#D4AF37]" />

      <div className="p-6 pt-8">
        <div className="flex justify-between items-start mb-5">
          <div className="flex items-center gap-3">
            <FolderOpen className="w-5 h-5 text-[#555]" strokeWidth={1.5} />
            <div>
              <div className="font-mono text-[9px] text-[#555] tracking-widest">CASE REF: {c.ref}</div>
              <h4 className="font-heading text-xl text-[#F5F5F5] mt-0.5">{c.title}</h4>
            </div>
          </div>
          <span className={`font-mono text-[9px] border px-2 py-1 tracking-widest ${c.type === "CRITICAL" ? "border-red-900 text-red-500" : "border-orange-900 text-orange-500"}`}>
            {c.type}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            ["Pages", c.pages],
            ["Risks", c.risks],
            ["Exposure", c.exposure],
          ].map(([k, v]) => (
            <div key={String(k)} className="border border-[#111] p-3 text-center">
              <div className="font-mono text-[9px] text-[#555] uppercase tracking-widest mb-1">{k}</div>
              <div className="font-mono text-sm font-bold text-[#D4AF37]">{v}</div>
            </div>
          ))}
        </div>

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="pt-4 border-t border-[#111] space-y-3">
                <div>
                  <div className="font-mono text-[9px] text-[#555] uppercase tracking-widest mb-1">Finding</div>
                  <p className="font-mono text-xs text-red-400">{c.finding}</p>
                </div>
                <div>
                  <div className="font-mono text-[9px] text-[#555] uppercase tracking-widest mb-1">Outcome</div>
                  <p className="font-mono text-xs text-[#22c55e]">{c.outcome}</p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-center justify-between mt-4 pt-3 border-t border-[#0f0f0f]">
          <span className="font-mono text-[9px] text-[#444] uppercase tracking-widest">Click to {open ? "collapse" : "expand"}</span>
          <ChevronRight className={`w-3 h-3 text-[#444] transition-transform duration-300 ${open ? "rotate-90" : ""}`} />
        </div>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────
// SECURITY VAULT SECTION
// ─────────────────────────────────────────────
const SECURITY_FEATURES = [
  { label: "End-to-End Encryption", detail: "AES-256 at rest & TLS 1.3 in transit" },
  { label: "SOC2 Type II Ready", detail: "Annual third-party security audits" },
  { label: "Zero Data Retention", detail: "Documents purged post-analysis" },
  { label: "ISO 27001 Compliant", detail: "Information security management" },
  { label: "Private Cloud Deploy", detail: "VPC isolation on your infrastructure" },
  { label: "Immutable Audit Logs", detail: "Every action timestamped & signed" },
  { label: "Role-Based Access", detail: "Granular permission matrix per team" },
  { label: "Version History", detail: "Full redline diff history preserved" },
];

// ─────────────────────────────────────────────
// LIVE CONTRACT PREVIEW
// ─────────────────────────────────────────────
const CLAUSES = [
  { id: "§1.1", text: "This Agreement shall commence on the Effective Date and continue for an initial term of two (2) years...", risk: null },
  { id: "§4.2", text: "Provider shall indemnify, defend, and hold harmless Client against any and all claims, damages, losses, or liabilities arising from any cause whatsoever...", risk: "CRITICAL" },
  { id: "§7.3", text: "Either party may terminate this Agreement for any reason, without notice, with unlimited liability remaining in effect perpetually...", risk: "CRITICAL" },
  { id: "§9.1", text: "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware...", risk: null },
  { id: "§11.2", text: "This Agreement shall automatically renew for successive one-year terms unless terminated with 90 days written notice prior to each renewal date...", risk: "MEDIUM" },
];

function LiveContractPreview() {
  const [hoveredClause, setHoveredClause] = useState<string | null>(null);
  return (
    <div className="border border-[#1a1a1a] bg-[#080808] p-6 h-full">
      <div className="flex items-center justify-between mb-5 pb-4 border-b border-[#111]">
        <div>
          <div className="font-mono text-[9px] text-[#555] tracking-widest">DOCUMENT</div>
          <div className="font-heading text-lg text-[#F5F5F5] mt-0.5">Master Services Agreement</div>
        </div>
        <div className="font-mono text-[9px] border border-red-900 text-red-500 px-2 py-1 tracking-widest">2 CRITICAL RISKS</div>
      </div>
      <div className="space-y-3">
        {CLAUSES.map((clause) => (
          <div
            key={clause.id}
            className="relative group cursor-default"
            onMouseEnter={() => setHoveredClause(clause.id)}
            onMouseLeave={() => setHoveredClause(null)}
          >
            <div className={`p-3 border transition-all duration-200 ${
              clause.risk === "CRITICAL" ? "border-red-900/50 bg-red-950/20" :
              clause.risk === "MEDIUM" ? "border-yellow-900/50 bg-yellow-950/10" :
              "border-[#111] bg-[#0a0a0a]"
            }`}>
              <div className="flex items-start gap-3">
                <span className={`font-mono text-[9px] tracking-widest shrink-0 mt-0.5 ${
                  clause.risk === "CRITICAL" ? "text-red-500" :
                  clause.risk === "MEDIUM" ? "text-yellow-500" :
                  "text-[#555]"
                }`}>{clause.id}</span>
                <p className="font-serif text-xs text-[#999] leading-relaxed">{clause.text}</p>
              </div>
              {clause.risk && (
                <div className="mt-2 flex items-center gap-2">
                  <AlertTriangle className={`w-3 h-3 ${clause.risk === "CRITICAL" ? "text-red-500" : "text-yellow-500"}`} />
                  <span className={`font-mono text-[9px] tracking-widest ${clause.risk === "CRITICAL" ? "text-red-500" : "text-yellow-500"}`}>{clause.risk} RISK DETECTED</span>
                </div>
              )}
            </div>
            {/* Tooltip annotation */}
            <AnimatePresence>
              {hoveredClause === clause.id && clause.risk && (
                <motion.div
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="absolute right-0 top-0 w-52 bg-[#0d0d0d] border border-[#D4AF3730] p-3 z-20 shadow-2xl"
                  style={{ transform: "translateX(calc(100% + 12px))" }}
                >
                  <div className="font-mono text-[9px] text-[#D4AF37] tracking-widest mb-1">AI ANNOTATION</div>
                  <div className="font-mono text-[9px] text-[#777] mb-2">Risk: {clause.risk} · Confidence: 97%</div>
                  <div className="font-mono text-[9px] text-[#22c55e]">→ Protective clause available</div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// UPLOAD MODAL (preserved business logic)
// ─────────────────────────────────────────────
function UploadModal({
  onClose, loading, pollingStatus, error, file,
  onFileChange, onUpload, fileInputRef
}: {
  onClose: () => void;
  loading: boolean;
  pollingStatus: string | null;
  error: string | null;
  file: File | null;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onUpload: () => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
    >
      <motion.div
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
        transition={{ duration: 0.25 }}
        className="w-full max-w-md bg-[#0a0a0a] border border-[#D4AF3740] relative"
      >
        {/* Gold top bar */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#D4AF37] to-transparent" />

        <div className="p-8">
          <div className="flex justify-between items-start mb-8">
            <div>
              <div className="font-mono text-[9px] text-[#D4AF37] tracking-widest mb-2">INITIATING CASE FILE</div>
              <h2 className="font-heading text-3xl text-[#F5F5F5]">Upload Contract</h2>
              <p className="font-mono text-[10px] text-[#555] mt-1">PDF · DOCX · TXT — Max 25MB</p>
            </div>
            <button onClick={onClose} disabled={loading} className="text-[#555] hover:text-[#F5F5F5] transition-colors disabled:opacity-30">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drop Zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className={`border border-dashed p-12 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 mb-6 ${
              file ? "border-[#D4AF37] bg-[#D4AF3710]" : "border-[#222] hover:border-[#D4AF3740] hover:bg-[#D4AF3705]"
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              accept=".pdf,.docx,.txt"
              onChange={onFileChange}
            />
            {file ? (
              <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center">
                <FileText className="w-8 h-8 text-[#D4AF37] mb-3" strokeWidth={1} />
                <p className="font-mono text-xs text-[#F5F5F5] text-center">{file.name}</p>
                <p className="font-mono text-[10px] text-[#555] mt-1">{(file.size / 1024).toFixed(1)} KB</p>
              </motion.div>
            ) : (
              <div className="flex flex-col items-center">
                <Upload className="w-8 h-8 text-[#444] mb-3" strokeWidth={1} />
                <p className="font-mono text-[10px] text-[#555] uppercase tracking-widest">Select or drop file</p>
              </div>
            )}
          </div>

          {/* Status / Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                className="bg-red-950/30 border border-red-900/50 p-3 mb-4 font-mono text-[10px] text-red-400 tracking-wider"
              >
                [SYSTEM ERROR] {error}
              </motion.div>
            )}
            {loading && pollingStatus && (
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="flex items-center gap-3 mb-4 font-mono text-[10px] text-[#D4AF37]"
              >
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
                  className="w-3 h-3 border border-[#D4AF37] border-t-transparent rounded-full" />
                {pollingStatus}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Actions */}
          <button
            onClick={onUpload}
            disabled={!file || loading}
            className="w-full h-12 bg-[#D4AF37] text-[#090909] font-mono text-xs uppercase tracking-widest font-bold hover:bg-[#c9a430] disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 mb-3"
          >
            {loading ? (pollingStatus || "Processing...") : "Execute Agent Sequence →"}
          </button>
          <button
            onClick={onClose}
            disabled={loading}
            className="w-full h-10 border border-[#222] text-[#555] font-mono text-[10px] uppercase tracking-widest hover:border-[#444] hover:text-[#999] disabled:opacity-30 transition-all duration-200"
          >
            Abort
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────
// MAIN PAGE COMPONENT
// ─────────────────────────────────────────────
export default function Home() {
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [pollingStatus, setPollingStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setPollingStatus("Scanning document...");
    setError(null);

    try {
      const { task_id } = await analyzeContract(file);
      setPollingStatus("Searching precedent database...");
      let pollCount = 0;
      const pollInterval = setInterval(async () => {
        pollCount++;
        if (pollCount === 2) setPollingStatus("Running policy validation...");
        if (pollCount === 4) setPollingStatus("Generating compliant rewrite...");
        try {
          const statusRes = await checkContractStatus(task_id);
          if (statusRes.status === "completed" && statusRes.result) {
            clearInterval(pollInterval);
            sessionStorage.setItem("analysisResult", JSON.stringify(statusRes.result));
            router.push("/review");
          } else if (statusRes.state === "FAILURE") {
            clearInterval(pollInterval);
            setError("Investigation failed in background worker.");
            setLoading(false);
            setPollingStatus(null);
          }
        } catch {
          clearInterval(pollInterval);
          setError("Failed to check status.");
          setLoading(false);
          setPollingStatus(null);
        }
      }, 3000);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || "An unexpected error occurred during investigation.");
      setLoading(false);
      setPollingStatus(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#090909] text-[#F5F5F5] overflow-x-hidden selection:bg-[#D4AF3730] selection:text-[#D4AF37]">
      <ParticleCanvas />

      {/* Vignette */}
      <div className="fixed inset-0 pointer-events-none z-0"
        style={{ background: "radial-gradient(ellipse at 50% 0%, transparent 60%, #090909 100%)" }} />

      {/* Gold grid overlay */}
      <div className="fixed inset-0 pointer-events-none z-0 opacity-[0.015]"
        style={{ backgroundImage: "linear-gradient(#D4AF37 1px, transparent 1px), linear-gradient(90deg, #D4AF37 1px, transparent 1px)", backgroundSize: "80px 80px" }} />

      {/* ── NAVIGATION ── */}
      <nav className="fixed top-0 w-full z-40 bg-[#09090980] backdrop-blur-md border-b border-[#D4AF3715]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <Shield className="w-5 h-5 text-[#D4AF37]" strokeWidth={1.5} />
            </div>
            <span className="font-heading text-lg tracking-[0.2em] uppercase text-[#F5F5F5] font-medium">
              Clause<span className="text-[#D4AF37]">Guard</span>
            </span>
          </div>

          <div className="hidden md:flex items-center gap-8 font-mono text-[10px] tracking-widest uppercase text-[#555]">
            {["Investigations", "Technology", "Enterprise", "Security"].map(item => (
              <a key={item} href="#" className="hover:text-[#D4AF37] transition-colors duration-200">{item}</a>
            ))}
          </div>

          <button
            onClick={() => setShowUpload(true)}
            className="border border-[#D4AF3750] text-[#D4AF37] font-mono text-[9px] tracking-widest uppercase px-5 py-2.5 hover:bg-[#D4AF3710] transition-all duration-200"
          >
            Request Demo
          </button>
        </div>
      </nav>

      <main className="relative z-10">

        {/* ── HERO ── */}
        <section className="min-h-screen flex items-center pt-16 px-6">
          <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center py-24">

            {/* Left */}
            <div className="space-y-8">
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="flex items-center gap-3"
              >
                <div className="w-12 h-[1px] bg-[#D4AF37]" />
                <span className="font-mono text-[9px] text-[#D4AF37] tracking-widest uppercase">Legal Intelligence System v2.0</span>
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.1 }}
                className="font-heading text-6xl md:text-7xl lg:text-8xl leading-[0.95] tracking-tight"
              >
                Every Contract<br />
                Has Something<br />
                It <span className="text-[#D4AF37] italic">Doesn't</span> Want<br />
                You To Find.
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.25 }}
                className="font-sans text-[#9A9A9A] text-lg leading-relaxed max-w-lg"
              >
                ClauseGuard investigates every clause, validates against legal precedents,
                detects hidden liabilities, and generates safer legal language — before you sign.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.4 }}
                className="flex flex-col sm:flex-row gap-4 pt-2"
              >
                <button
                  onClick={() => setShowUpload(true)}
                  className="group flex items-center gap-3 bg-[#D4AF37] text-[#090909] font-mono text-[10px] uppercase tracking-widest font-bold px-8 h-13 hover:bg-[#c9a430] transition-all duration-200"
                  style={{ height: "52px" }}
                >
                  Open Case File
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  className="flex items-center gap-3 border border-[#222] text-[#999] font-mono text-[10px] uppercase tracking-widest px-8 hover:border-[#444] hover:text-[#F5F5F5] transition-all duration-200"
                  style={{ height: "52px" }}
                >
                  Watch Investigation
                </button>
              </motion.div>

              {/* Stats row */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="flex gap-8 pt-4 border-t border-[#111]"
              >
                {[["99.2%", "Accuracy Rate"], ["< 45s", "Per Contract"], ["SOC2", "Certified"]].map(([val, lab]) => (
                  <div key={lab}>
                    <div className="font-heading text-2xl text-[#D4AF37]">{val}</div>
                    <div className="font-mono text-[9px] text-[#555] uppercase tracking-widest mt-0.5">{lab}</div>
                  </div>
                ))}
              </motion.div>
            </div>

            {/* Right — Live Interface Split */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="hidden lg:flex flex-col gap-4 h-[580px]"
            >
              <div className="flex-1 relative">
                <div className="absolute -inset-0.5 bg-gradient-to-br from-[#D4AF3720] to-transparent blur-lg" />
                <div className="relative h-full">
                  <LiveContractPreview />
                </div>
              </div>
              <div className="h-[180px] relative">
                <div className="absolute -inset-0.5 bg-gradient-to-tr from-transparent to-[#D4AF3710] blur-lg" />
                <div className="relative h-full">
                  <TypingTerminal />
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* ── INVESTIGATION WORKFLOW ── */}
        <section className="py-32 px-6 border-t border-[#0f0f0f]">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-3 mb-6">
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
                <span className="font-mono text-[9px] text-[#D4AF37] tracking-widest uppercase">Investigation Protocol</span>
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
              </div>
              <h2 className="font-heading text-5xl md:text-6xl mb-4">How We Investigate</h2>
              <p className="font-sans text-[#555] max-w-xl mx-auto text-base">A deterministic, auditable pipeline designed for enterprise-grade legal review.</p>
            </div>
            <WorkflowTimeline />
          </div>
        </section>

        {/* ── PRODUCT SHOWCASE ── */}
        <section className="py-32 px-6 border-t border-[#0f0f0f]">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-3 mb-6">
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
                <span className="font-mono text-[9px] text-[#D4AF37] tracking-widest uppercase">Product Showcase</span>
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
              </div>
              <h2 className="font-heading text-5xl md:text-6xl mb-4">The Investigation Console</h2>
              <p className="font-sans text-[#555] max-w-xl mx-auto text-base">Watch the AI examine each clause in real time, surfacing risks and drafting protective language.</p>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 border border-[#111]">
              <div className="h-[520px] border-r border-[#111]">
                <LiveContractPreview />
              </div>
              <div className="h-[520px]">
                <TypingTerminal />
              </div>
            </div>
          </div>
        </section>

        {/* ── AI AGENTS DOSSIER ── */}
        <section className="py-32 px-6 border-t border-[#0f0f0f]">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-3 mb-6">
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
                <span className="font-mono text-[9px] text-[#D4AF37] tracking-widest uppercase">Classified Assets</span>
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
              </div>
              <h2 className="font-heading text-5xl md:text-6xl mb-4">AI Agent Dossiers</h2>
              <p className="font-sans text-[#555] max-w-xl mx-auto text-base">Two specialized legal intelligence agents, each cleared for high-value contract operations.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {AGENTS.map(agent => <AgentDossier key={agent.codename} agent={agent} />)}
            </div>
          </div>
        </section>

        {/* ── CASE STUDIES ── */}
        <section className="py-32 px-6 border-t border-[#0f0f0f]">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-3 mb-6">
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
                <span className="font-mono text-[9px] text-[#D4AF37] tracking-widest uppercase">Declassified Case Files</span>
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
              </div>
              <h2 className="font-heading text-5xl md:text-6xl mb-4">Past Investigations</h2>
              <p className="font-sans text-[#555] max-w-xl mx-auto text-base">Real-world risk exposures detected and neutralized. Click a file to read the investigation report.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {CASES.map((c, i) => <CaseFile key={c.ref} c={c} delay={i * 0.1} />)}
            </div>
          </div>
        </section>

        {/* ── SECURITY VAULT ── */}
        <section className="py-32 px-6 border-t border-[#0f0f0f]">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-3 mb-6">
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
                <span className="font-mono text-[9px] text-[#D4AF37] tracking-widest uppercase">Secure Facility</span>
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
              </div>
              <h2 className="font-heading text-5xl md:text-6xl mb-4">Government-Grade Security</h2>
              <p className="font-sans text-[#555] max-w-xl mx-auto text-base">Your contracts never leave the vault unprotected. Every access is authenticated, logged, and auditable.</p>
            </div>

            <div className="border border-[#111] bg-[#050505] relative overflow-hidden">
              <div className="absolute inset-0 pointer-events-none">
                <Lock className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] text-[#D4AF37] opacity-[0.015]" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 relative z-10">
                {SECURITY_FEATURES.map((feat, i) => (
                  <motion.div
                    key={feat.label}
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.07 }}
                    className="p-6 border-r border-b border-[#0f0f0f] hover:bg-[#D4AF3705] transition-colors duration-300"
                  >
                    <ShieldCheck className="w-5 h-5 text-[#D4AF37] mb-4" strokeWidth={1.5} />
                    <div className="font-mono text-xs text-[#F5F5F5] font-bold mb-1">{feat.label}</div>
                    <div className="font-mono text-[9px] text-[#555] leading-relaxed">{feat.detail}</div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── FINAL CTA ── */}
        <section className="py-40 px-6 border-t border-[#0f0f0f] text-center relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_50%,#D4AF3708,transparent_70%)]" />
          </div>
          <div className="max-w-4xl mx-auto relative z-10">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <div className="inline-flex items-center gap-3 mb-10">
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
                <span className="font-mono text-[9px] text-[#D4AF37] tracking-widest uppercase">Begin</span>
                <div className="w-8 h-[1px] bg-[#D4AF37]" />
              </div>
              <h2 className="font-heading text-6xl md:text-7xl lg:text-8xl mb-6 leading-tight">
                The strongest contracts<br />
                aren&apos;t written.<br />
                <span className="text-[#D4AF37] italic">They&apos;re investigated.</span>
              </h2>
              <p className="font-sans text-[#555] text-lg mb-12">
                Upload your contract. Our agents will find what it doesn&apos;t want you to find.
              </p>
              <button
                onClick={() => setShowUpload(true)}
                className="group inline-flex items-center gap-4 border border-[#D4AF37] text-[#D4AF37] font-mono text-xs uppercase tracking-widest px-12 hover:bg-[#D4AF37] hover:text-[#090909] transition-all duration-300"
                style={{ height: "60px" }}
              >
                Start Investigation
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </motion.div>
          </div>
        </section>

      </main>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[#D4AF3715] bg-[#050505] py-14 px-6 relative z-10">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
            <div className="col-span-2">
              <div className="flex items-center gap-2.5 mb-4">
                <Shield className="w-4 h-4 text-[#D4AF37]" strokeWidth={1.5} />
                <span className="font-heading text-lg tracking-[0.2em] uppercase">Clause<span className="text-[#D4AF37]">Guard</span></span>
              </div>
              <p className="font-mono text-[10px] text-[#444] leading-relaxed max-w-xs">
                Enterprise AI contract intelligence for legal teams who can&apos;t afford to miss a clause.
              </p>
            </div>
            {[
              { title: "Technology", links: ["AI Agents", "RAG Engine", "API Docs"] },
              { title: "Security", links: ["SOC2", "Encryption", "Compliance"] },
              { title: "Enterprise", links: ["Pricing", "SLA", "Contact"] },
              { title: "Legal", links: ["Privacy", "Terms", "DPA"] },
            ].map(col => (
              <div key={col.title}>
                <div className="font-mono text-[9px] text-[#D4AF37] uppercase tracking-widest mb-4">{col.title}</div>
                <div className="space-y-2.5">
                  {col.links.map(l => (
                    <a key={l} href="#" className="block font-mono text-[10px] text-[#444] hover:text-[#D4AF37] transition-colors duration-200 uppercase tracking-wider">{l}</a>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="border-t border-[#0f0f0f] pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
            <span className="font-mono text-[9px] text-[#333] uppercase tracking-widest">© 2026 ClauseGuard Intelligence Systems</span>
            <div className="flex gap-6">
              <span className="font-mono text-[9px] text-[#333] uppercase tracking-widest">Version 2.0.0</span>
              <span className="font-mono text-[9px] text-[#333] uppercase tracking-widest">Case Ref: CG-PROD-2026</span>
            </div>
          </div>
        </div>
      </footer>

      {/* ── UPLOAD MODAL ── */}
      <AnimatePresence>
        {showUpload && (
          <UploadModal
            onClose={() => { if (!loading) setShowUpload(false); }}
            loading={loading}
            pollingStatus={pollingStatus}
            error={error}
            file={file}
            onFileChange={handleFileChange}
            onUpload={handleUpload}
            fileInputRef={fileInputRef}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
