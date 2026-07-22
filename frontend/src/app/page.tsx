"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, ShieldAlert, FileText, ArrowRight, Loader2, Sparkles, Zap, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { analyzeContract } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function Home() {
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
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
    setError(null);
    
    try {
      const result = await analyzeContract(file);
      sessionStorage.setItem("analysisResult", JSON.stringify(result));
      router.push("/review");
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "An unexpected error occurred during analysis.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 lg:p-24 bg-gradient-to-br from-background via-background to-secondary/30 relative overflow-hidden">
      
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-3xl opacity-50 pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl opacity-50 pointer-events-none" />

      <AnimatePresence mode="wait">
        {!showUpload ? (
          <motion.div 
            key="hero"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="w-full max-w-5xl flex flex-col items-center text-center z-10"
          >
            <motion.div 
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className="bg-primary/10 border border-primary/20 p-4 rounded-2xl mb-8 backdrop-blur-md shadow-lg shadow-primary/5"
            >
              <ShieldCheck className="w-16 h-16 text-primary" />
            </motion.div>
            
            <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
              ClauseGuard <span className="text-primary block mt-2">AI Compliance</span>
            </h1>
            
            <p className="text-xl lg:text-2xl text-muted-foreground max-w-3xl mb-12 leading-relaxed">
              Automate enterprise contract review with dual-agent reasoning and deterministic risk validation. Identify liabilities and generate redlines in seconds.
            </p>

            <div className="flex flex-col sm:flex-row gap-6 mb-16">
              <Button 
                size="lg" 
                className="h-14 px-8 text-lg rounded-full group shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-all"
                onClick={() => setShowUpload(true)}
              >
                Dive In
                <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl text-left">
              <div className="p-6 rounded-2xl bg-card border border-border/50 shadow-sm backdrop-blur-sm hover:border-primary/50 transition-colors">
                <Sparkles className="w-8 h-8 text-primary mb-4" />
                <h3 className="font-semibold text-lg mb-2">Dual-Agent AI</h3>
                <p className="text-muted-foreground text-sm">Powered by Google ADK to analyze risks and suggest actionable redlines.</p>
              </div>
              <div className="p-6 rounded-2xl bg-card border border-border/50 shadow-sm backdrop-blur-sm hover:border-blue-500/50 transition-colors">
                <Zap className="w-8 h-8 text-blue-500 mb-4" />
                <h3 className="font-semibold text-lg mb-2">Hybrid Retrieval</h3>
                <p className="text-muted-foreground text-sm">Grounds every decision using Qdrant Cloud against your standard clauses.</p>
              </div>
              <div className="p-6 rounded-2xl bg-card border border-border/50 shadow-sm backdrop-blur-sm hover:border-orange-500/50 transition-colors">
                <ShieldAlert className="w-8 h-8 text-orange-500 mb-4" />
                <h3 className="font-semibold text-lg mb-2">Policy Validator</h3>
                <p className="text-muted-foreground text-sm">Deterministic rule engine ensures no high-risk clause slips past.</p>
              </div>
            </div>

            {/* Pop-Culture Lawyer Vibes */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.8 }}
              className="mt-16 w-full max-w-4xl"
            >
              <p className="text-sm uppercase tracking-widest text-muted-foreground mb-6 font-semibold">The Greatest Legal Minds Agree</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="flex flex-col items-center text-center p-6 bg-card/40 rounded-2xl border border-border/50 shadow-sm backdrop-blur-sm">
                  <p className="italic text-lg text-foreground mb-4">"When you need a *criminal* lawyer... but for contracts, ClauseGuard is the only call you make."</p>
                  <p className="font-bold text-primary text-xl">— Saul Goodman</p>
                  <p className="text-sm text-muted-foreground">Albuquerque, NM</p>
                </div>
                <div className="flex flex-col items-center text-center p-6 bg-card/40 rounded-2xl border border-border/50 shadow-sm backdrop-blur-sm">
                  <p className="italic text-lg text-foreground mb-4">"Justice is blind, but ClauseGuard's radar-sense precision sees every hidden liability."</p>
                  <p className="font-bold text-primary text-xl">— Matt Murdock</p>
                  <p className="text-sm text-muted-foreground">Hell's Kitchen, NY</p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        ) : (
          <motion.div 
            key="upload"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.5, type: "spring" }}
            className="w-full max-w-md z-10"
          >
            <Card className="border-primary/20 shadow-2xl bg-background/80 backdrop-blur-xl rounded-2xl overflow-hidden">
              <div className="h-2 w-full bg-gradient-to-r from-primary/40 via-primary to-primary/40" />
              <CardHeader className="pt-8">
                <CardTitle className="text-2xl text-center">Analyze Contract</CardTitle>
                <CardDescription className="text-center text-base">Upload a PDF, DOCX, or TXT file</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-6 p-6">
                <div 
                  className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-300 ${file ? 'border-primary bg-primary/5 shadow-inner' : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30'}`}
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
                    <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }} className="flex flex-col items-center">
                      <div className="p-3 bg-primary/10 rounded-full mb-4">
                        <FileText className="w-12 h-12 text-primary" />
                      </div>
                      <p className="font-semibold text-foreground text-lg">{file.name}</p>
                      <p className="text-sm text-muted-foreground mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                    </motion.div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <div className="p-3 bg-muted rounded-full mb-4">
                        <Upload className="w-10 h-10 text-muted-foreground" />
                      </div>
                      <p className="font-medium text-foreground">Click to browse files</p>
                      <p className="text-xs text-muted-foreground mt-2 max-w-[200px]">Secure upload processing for enterprise compliance.</p>
                    </div>
                  )}
                </div>

                <AnimatePresence>
                  {error && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="bg-destructive/10 text-destructive text-sm p-4 rounded-lg border border-destructive/20"
                    >
                      {error}
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
              <CardFooter className="p-6 pt-0 flex flex-col gap-3">
                <Button 
                  className="w-full h-12 text-md rounded-xl group relative overflow-hidden" 
                  onClick={handleUpload} 
                  disabled={!file || loading}
                >
                  {loading && (
                    <div className="absolute inset-0 bg-primary flex items-center justify-center">
                      <Loader2 className="h-5 w-5 animate-spin mr-2" />
                      Processing via Agentic AI...
                    </div>
                  )}
                  {!loading && (
                    <span className="flex items-center">
                      Run AI Analysis
                      <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                    </span>
                  )}
                </Button>
                <Button 
                  variant="ghost" 
                  className="w-full text-muted-foreground hover:text-foreground"
                  onClick={() => setShowUpload(false)}
                  disabled={loading}
                >
                  Cancel
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
