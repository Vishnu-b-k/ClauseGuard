"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Scale, Cpu, Upload, FileText, ArrowRight, Activity, Terminal, Lock, Database, Search, 
  ShieldCheck, AlertTriangle, CheckCircle, Fingerprint, FolderClosed, Vault, Eye
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { analyzeContract, checkContractStatus } from "@/lib/api";
import { useRouter } from "next/navigation";

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
        } catch (err: any) {
          clearInterval(pollInterval);
          console.error(err);
          setError("Failed to check status.");
          setLoading(false);
          setPollingStatus(null);
        }
      }, 3000);

    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "An unexpected error occurred during investigation.");
      setLoading(false);
      setPollingStatus(null);
    }
  };

  const [logs, setLogs] = useState<string[]>([
    "System online.",
    "Awaiting investigation target...",
  ]);

  useEffect(() => {
    if (!showUpload) {
      const interval = setInterval(() => {
        const fakeLogs = [
          "Parsing clause sub-structure...",
          "Checking indemnification precedents...",
          "High Risk detected in Section 4(a).",
          "Cross-referencing liability caps...",
          "Validating against internal policy matrix..."
        ];
        setLogs(prev => {
          const next = [...prev, fakeLogs[Math.floor(Math.random() * fakeLogs.length)]];
          if (next.length > 5) next.shift();
          return next;
        });
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [showUpload]);

  return (
    <div className="min-h-screen bg-background text-foreground font-sans relative overflow-x-hidden selection:bg-primary/30 selection:text-primary">
      {/* Background Cinematic FX */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] mix-blend-overlay"></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(212,175,55,0.03)_0%,transparent_50%)]"></div>
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/20 to-transparent"></div>
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-background/80 backdrop-blur-md border-b border-primary/20">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 text-primary">
            <Scale className="w-5 h-5" />
            <span className="font-heading font-semibold text-lg tracking-wide uppercase text-foreground">ClauseGuard</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
            <a href="#" className="hover:text-foreground transition-colors">Investigations</a>
            <a href="#" className="hover:text-foreground transition-colors">Technology</a>
            <a href="#" className="hover:text-foreground transition-colors">Enterprise</a>
            <a href="#" className="hover:text-foreground transition-colors">Security</a>
          </div>
          <Button variant="outline" className="border-primary text-primary hover:bg-primary/10 rounded-none text-xs tracking-widest uppercase">
            Request Demo
          </Button>
        </div>
      </nav>

      <main className="relative z-10 pt-32 pb-24 px-6 max-w-7xl mx-auto">
        <AnimatePresence mode="wait">
          {!showUpload ? (
            <motion.div key="landing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              
              {/* HERO SECTION */}
              <div className="flex flex-col lg:flex-row gap-16 items-center mb-40">
                <div className="flex-1 space-y-8">
                  <h1 className="font-heading text-5xl md:text-7xl leading-[1.1] font-medium tracking-tight">
                    Every Contract<br/>
                    Has Something<br/>
                    It <span className="text-primary italic">Doesn't</span> Want<br/>
                    You To Find.
                  </h1>
                  <p className="text-muted-foreground text-lg max-w-xl leading-relaxed">
                    ClauseGuard is an AI-powered legal investigation platform. It interrogates every clause, cross-examines every obligation, validates every policy, and exposes liabilities before they become lawsuits.
                  </p>
                  <div className="flex gap-4 pt-4">
                    <Button 
                      onClick={() => setShowUpload(true)}
                      className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-none h-12 px-8 uppercase tracking-widest text-xs font-semibold"
                    >
                      Open Case File
                    </Button>
                    <Button variant="outline" className="border-border text-foreground hover:bg-card rounded-none h-12 px-8 uppercase tracking-widest text-xs">
                      Watch Investigation
                    </Button>
                  </div>
                </div>

                {/* Right Side: Alive Interface Mock */}
                <div className="flex-1 w-full max-w-lg relative">
                  <div className="absolute -inset-1 bg-gradient-to-tr from-primary/20 to-transparent blur-2xl"></div>
                  <div className="bg-card border border-border p-6 shadow-2xl relative">
                    <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
                      <div className="text-xs font-mono text-muted-foreground">CASE_ID: CG-8842-X</div>
                      <div className="flex items-center gap-2 text-destructive text-xs font-bold font-mono tracking-widest">
                        <AlertTriangle className="w-4 h-4" />
                        LIABILITY FOUND
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div className="p-3 bg-background border border-border">
                        <p className="font-mono text-xs text-muted-foreground mb-1">Clause 4.2 - Indemnification</p>
                        <p className="text-sm font-serif">"...Provider shall indemnify Client against <span className="bg-destructive/20 text-destructive-foreground px-1 border-b border-destructive">any and all claims</span> arising from..."</p>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="border border-border p-3">
                          <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Risk</p>
                          <p className="text-destructive font-mono font-bold">CRITICAL</p>
                        </div>
                        <div className="border border-border p-3">
                          <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Confidence</p>
                          <p className="text-foreground font-mono font-bold">98%</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* INVESTIGATION TIMELINE */}
              <div className="mb-40">
                <p className="text-xs font-mono text-primary uppercase tracking-widest mb-12 text-center">Investigation Protocol</p>
                <div className="flex flex-col md:flex-row items-center justify-between relative">
                  <div className="hidden md:block absolute top-1/2 left-0 w-full h-[1px] bg-border -z-10"></div>
                  {[
                    "UPLOAD", "AI ANALYSIS", "PRECEDENT SEARCH", "POLICY VALIDATION", "REDLINES", "LEGAL REPORT"
                  ].map((step, idx) => (
                    <motion.div 
                      key={step}
                      initial={{ opacity: 0, y: 10 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: idx * 0.1 }}
                      className="bg-card border border-primary/30 p-3 flex items-center justify-center min-w-[120px] mb-4 md:mb-0 relative"
                    >
                      <span className="text-[10px] font-mono tracking-widest">{step}</span>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* SPLIT LAYOUT: CONTRACT & CONSOLE */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-40">
                <div className="bg-card border border-border p-8 h-[400px] overflow-hidden relative group">
                  <div className="absolute top-4 right-4"><Eye className="w-4 h-4 text-muted-foreground" /></div>
                  <h3 className="font-heading text-xl mb-6 border-b border-border pb-4">Master Services Agreement</h3>
                  <div className="space-y-4 font-serif text-sm text-muted-foreground leading-relaxed">
                    <p>1. Term. This Agreement shall commence on the Effective Date...</p>
                    <div className="relative cursor-pointer transition-colors hover:text-foreground">
                      <span className="group-hover:bg-primary/10 transition-colors duration-300">
                        2. Termination. Either party may terminate for convenience with 30 days notice.
                      </span>
                      <motion.div 
                        initial={{ opacity: 0 }} 
                        whileHover={{ opacity: 1 }}
                        className="absolute left-full top-0 ml-4 w-48 bg-background border border-border p-3 shadow-xl z-20 pointer-events-none"
                      >
                        <p className="text-[10px] font-mono text-primary mb-1">Termination</p>
                        <p className="text-xs font-sans">Risk: 87%<br/>Conflicting Clause</p>
                      </motion.div>
                    </div>
                    <p>3. Jurisdiction. This Agreement shall be governed by the laws of...</p>
                  </div>
                </div>

                <div className="bg-[#050505] border border-[#222] p-6 h-[400px] font-mono text-xs overflow-hidden flex flex-col">
                  <div className="flex items-center gap-2 mb-4 border-b border-[#222] pb-2 text-[#666]">
                    <Terminal className="w-4 h-4" />
                    <span>SYSTEM_CONSOLE // INVESTIGATION_ACTIVE</span>
                  </div>
                  <div className="flex-1 space-y-2 text-[#00FF41]">
                    <AnimatePresence>
                      {logs.map((log, i) => (
                        <motion.div key={i} initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} className={log.includes("High Risk") ? "text-destructive font-bold" : ""}>
                          &gt; {log}
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </div>
              </div>

              {/* AI AGENTS DOSSIER */}
              <div className="mb-40">
                <p className="text-xs font-mono text-primary uppercase tracking-widest mb-12 text-center">Classified Assets</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="border border-border bg-card p-6 relative overflow-hidden group hover:border-primary/50 transition-colors">
                    <Fingerprint className="absolute -right-10 -bottom-10 w-48 h-48 text-muted/10 group-hover:text-primary/5 transition-colors" />
                    <div className="flex justify-between items-start mb-8">
                      <div>
                        <h4 className="font-heading text-2xl">COUNSEL</h4>
                        <p className="font-mono text-xs text-muted-foreground mt-1">ID: AGT-99-A</p>
                      </div>
                      <div className="border border-primary text-primary text-[10px] px-2 py-1 uppercase tracking-widest font-mono">Active</div>
                    </div>
                    <div className="space-y-4 font-mono text-xs">
                      <div className="grid grid-cols-2 border-b border-border pb-2">
                        <span className="text-muted-foreground">ROLE</span>
                        <span>Legal Reasoning</span>
                      </div>
                      <div className="grid grid-cols-2 border-b border-border pb-2">
                        <span className="text-muted-foreground">CLEARANCE</span>
                        <span>Level 5</span>
                      </div>
                      <div className="grid grid-cols-2">
                        <span className="text-muted-foreground">CONFIDENCE</span>
                        <span className="text-primary">96%</span>
                      </div>
                    </div>
                  </div>

                  <div className="border border-border bg-card p-6 relative overflow-hidden group hover:border-primary/50 transition-colors">
                    <Fingerprint className="absolute -right-10 -bottom-10 w-48 h-48 text-muted/10 group-hover:text-primary/5 transition-colors" />
                    <div className="flex justify-between items-start mb-8">
                      <div>
                        <h4 className="font-heading text-2xl">LEX</h4>
                        <p className="font-mono text-xs text-muted-foreground mt-1">ID: AGT-22-B</p>
                      </div>
                      <div className="border border-primary text-primary text-[10px] px-2 py-1 uppercase tracking-widest font-mono">Active</div>
                    </div>
                    <div className="space-y-4 font-mono text-xs">
                      <div className="grid grid-cols-2 border-b border-border pb-2">
                        <span className="text-muted-foreground">ROLE</span>
                        <span>Policy Validation</span>
                      </div>
                      <div className="grid grid-cols-2 border-b border-border pb-2">
                        <span className="text-muted-foreground">CLEARANCE</span>
                        <span>Level 5</span>
                      </div>
                      <div className="grid grid-cols-2">
                        <span className="text-muted-foreground">ACCURACY</span>
                        <span className="text-primary">99%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* CASE STUDIES */}
              <div className="mb-40">
                <p className="text-xs font-mono text-primary uppercase tracking-widest mb-12 text-center">Declassified Case Files</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="border border-border bg-background p-6">
                    <FolderClosed className="w-6 h-6 text-muted-foreground mb-4" />
                    <h5 className="font-heading text-lg mb-4">M&A Agreement</h5>
                    <div className="space-y-2 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                      <p>46 Pages Analyzed</p>
                      <p className="text-destructive">18 Hidden Liabilities</p>
                      <p className="text-primary">Estimated Savings: $3.2M</p>
                    </div>
                  </div>
                  <div className="border border-border bg-background p-6">
                    <FolderClosed className="w-6 h-6 text-muted-foreground mb-4" />
                    <h5 className="font-heading text-lg mb-4">Employment Agreement</h5>
                    <div className="space-y-2 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                      <p>12 Critical Risks</p>
                      <p className="text-primary">Negotiation Time Reduced 4 Days</p>
                    </div>
                  </div>
                  <div className="border border-border bg-background p-6">
                    <FolderClosed className="w-6 h-6 text-muted-foreground mb-4" />
                    <h5 className="font-heading text-lg mb-4">Vendor Contract</h5>
                    <div className="space-y-2 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                      <p className="text-destructive">Unlimited Liability Found</p>
                      <p className="text-primary">Generated Safer Language</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* SECURITY VAULT */}
              <div className="mb-40 border border-border bg-card p-12 text-center relative overflow-hidden">
                <Vault className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 text-muted/5 -z-10" />
                <Lock className="w-8 h-8 text-primary mx-auto mb-6" />
                <h3 className="font-heading text-3xl mb-8">Secure Government Facility</h3>
                <div className="flex flex-wrap justify-center gap-4 max-w-2xl mx-auto font-mono text-xs uppercase tracking-widest text-muted-foreground">
                  <span className="border border-border px-3 py-1">SOC2</span>
                  <span className="border border-border px-3 py-1">End-to-End Encryption</span>
                  <span className="border border-border px-3 py-1">Zero Data Retention</span>
                  <span className="border border-border px-3 py-1">Private Cloud</span>
                  <span className="border border-border px-3 py-1">Audit Logs</span>
                  <span className="border border-border px-3 py-1">Role-Based Access</span>
                </div>
              </div>

              {/* FINAL CTA */}
              <div className="text-center mb-32">
                <h2 className="font-heading text-4xl md:text-5xl mb-8">
                  The strongest contracts aren't written.<br/>
                  <span className="text-primary">They're investigated.</span>
                </h2>
                <Button 
                  onClick={() => setShowUpload(true)}
                  className="bg-foreground text-background hover:bg-muted-foreground rounded-none h-14 px-12 uppercase tracking-widest text-sm font-semibold"
                >
                  Start Investigation
                </Button>
              </div>

            </motion.div>
          ) : (
            
            /* UPLOAD MODAL (Restyled for Dark Luxury) */
            <motion.div 
              key="upload"
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="w-full max-w-md z-10 mx-auto"
            >
              <Card className="border border-border bg-card rounded-none shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[2px] bg-primary"></div>
                <CardHeader className="pt-8 border-b border-border bg-background">
                  <CardTitle className="text-xl font-heading font-medium tracking-wide">Initiate Investigation</CardTitle>
                  <CardDescription className="text-xs font-mono uppercase tracking-widest text-muted-foreground mt-2">Upload target document (PDF, DOCX, TXT)</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-4 p-8">
                  <div 
                    className={`border border-dashed p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-300 ${file ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40 hover:bg-background'}`}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      className="hidden" 
                      accept=".pdf,.docx,.txt"
                      onChange={handleFileChange}
                    />
                    {file ? (
                      <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center">
                        <div className="mb-3 text-primary">
                          <FileText className="w-8 h-8" strokeWidth={1} />
                        </div>
                        <p className="font-mono text-xs text-foreground">{file.name}</p>
                        <p className="text-[10px] font-mono text-muted-foreground mt-2 tracking-widest">{(file.size / 1024).toFixed(1)} KB</p>
                      </motion.div>
                    ) : (
                      <motion.div whileHover={{ scale: 1.05 }} className="flex flex-col items-center">
                        <div className="mb-3 text-muted-foreground">
                          <Upload className="w-8 h-8" strokeWidth={1} />
                        </div>
                        <p className="text-xs font-mono uppercase tracking-widest text-muted-foreground">Select File</p>
                      </motion.div>
                    )}
                  </div>

                  <AnimatePresence>
                    {error && (
                      <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-destructive/10 text-destructive text-[10px] font-mono uppercase tracking-wider p-3 border border-destructive/20"
                      >
                        [ERROR] {error}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardContent>
                <CardFooter className="p-6 flex flex-col gap-3 border-t border-border bg-background">
                  <Button 
                    className="w-full h-12 text-xs uppercase tracking-widest rounded-none font-bold bg-primary text-primary-foreground hover:bg-primary/90 transition-all" 
                    onClick={handleUpload} 
                    disabled={!file || loading}
                  >
                    {loading ? (pollingStatus || "Processing...") : "Execute Agent Sequence"}
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full h-12 text-xs uppercase tracking-widest rounded-none font-medium border-border text-foreground hover:bg-card"
                    onClick={() => setShowUpload(false)}
                    disabled={loading}
                  >
                    Abort
                  </Button>
                </CardFooter>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* FOOTER */}
      <footer className="border-t border-border bg-background py-12 relative z-10">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-8 text-xs font-mono text-muted-foreground uppercase tracking-widest">
          <div className="col-span-2 lg:col-span-2 flex items-center gap-2 text-foreground">
             <Scale className="w-4 h-4" /> ClauseGuard
          </div>
          <div className="flex flex-col gap-3">
            <span className="text-foreground font-semibold mb-2">Company</span>
            <a href="#" className="hover:text-primary">About</a>
            <a href="#" className="hover:text-primary">Contact</a>
          </div>
          <div className="flex flex-col gap-3">
            <span className="text-foreground font-semibold mb-2">Technology</span>
            <a href="#" className="hover:text-primary">Agents</a>
            <a href="#" className="hover:text-primary">Security</a>
          </div>
          <div className="flex flex-col gap-3">
            <span className="text-foreground font-semibold mb-2">Resources</span>
            <a href="#" className="hover:text-primary">Documentation</a>
            <a href="#" className="hover:text-primary">Terms</a>
            <a href="#" className="hover:text-primary">Privacy</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
