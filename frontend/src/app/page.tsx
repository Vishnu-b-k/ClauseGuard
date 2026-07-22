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
    <main className="flex min-h-screen flex-col items-center justify-center p-6 lg:p-24 bg-background relative overflow-hidden">
      <AnimatePresence mode="wait">
        {!showUpload ? (
          <motion.div 
            key="hero"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="w-full max-w-5xl flex flex-col items-center text-center z-10"
          >
            <h1 className="text-4xl lg:text-5xl font-medium tracking-tight mb-4 text-foreground">
              ClauseGuard contract intelligence
            </h1>
            
            <p className="text-lg text-muted-foreground max-w-3xl mb-12 leading-relaxed">
              Automate enterprise contract review with dual-agent reasoning and deterministic risk validation. Identify liabilities and generate redlines in seconds.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 mb-16">
              <Button 
                size="lg" 
                className="h-12 px-6 text-base rounded-md"
                onClick={() => setShowUpload(true)}
              >
                Dive in
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl text-left">
              <div className="p-6 rounded-xl bg-card border border-border shadow-none">
                <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-foreground mb-4 border border-border">
                  Dual-agent reasoning
                </div>
                <p className="text-foreground text-sm leading-relaxed">Agentic AI analyzes risks and suggests actionable redlines directly on the document text.</p>
              </div>
              <div className="p-6 rounded-xl bg-card border border-border shadow-none">
                <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-muted text-foreground mb-4 border border-border">
                  Hybrid retrieval
                </div>
                <p className="text-foreground text-sm leading-relaxed">Grounds every decision against your standard clauses using Qdrant vector search.</p>
              </div>
              <div className="p-6 rounded-xl bg-card border border-border shadow-none">
                <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-destructive text-destructive-foreground mb-4 border border-destructive">
                  Policy validator
                </div>
                <p className="text-foreground text-sm leading-relaxed">Deterministic rule engine ensures no high-risk clause slips past the automated review.</p>
              </div>
            </div>

            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.4 }}
              className="mt-16 w-full max-w-4xl"
            >
              <p className="text-xs text-muted-foreground mb-4">The greatest legal minds agree</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex flex-col items-start text-left p-6 bg-card rounded-xl border border-border shadow-none">
                  <p className="text-foreground text-sm leading-relaxed mb-4">"When you need a *criminal* lawyer... but for contracts, ClauseGuard is the only call you make."</p>
                  <p className="font-medium text-foreground text-sm">Saul Goodman</p>
                  <p className="text-xs text-muted-foreground">Albuquerque, NM</p>
                </div>
                <div className="flex flex-col items-start text-left p-6 bg-card rounded-xl border border-border shadow-none">
                  <p className="text-foreground text-sm leading-relaxed mb-4">"Justice is blind, but ClauseGuard's radar-sense precision sees every hidden liability."</p>
                  <p className="font-medium text-foreground text-sm">Matt Murdock</p>
                  <p className="text-xs text-muted-foreground">Hell's Kitchen, NY</p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        ) : (
          <motion.div 
            key="upload"
            initial={{ opacity: 0, scale: 0.98, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="w-full max-w-md z-10"
          >
            <Card className="border border-border shadow-none bg-card rounded-xl overflow-hidden">
              <CardHeader className="pt-6 border-b border-border">
                <CardTitle className="text-lg font-medium">Analyze contract</CardTitle>
                <CardDescription className="text-sm">Upload a PDF, DOCX, or TXT file</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-4 p-6 bg-muted/30">
                <div 
                  className={`border border-dashed rounded-md p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${file ? 'border-border bg-card' : 'border-border hover:bg-card'}`}
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
                    <div className="flex flex-col items-center">
                      <div className="p-2 border border-border rounded-md mb-3 bg-muted">
                        <FileText className="w-6 h-6 text-foreground" strokeWidth={1.5} />
                      </div>
                      <p className="font-medium text-foreground text-sm">{file.name}</p>
                      <p className="text-xs text-muted-foreground mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <div className="p-2 border border-border rounded-md mb-3 bg-background">
                        <Upload className="w-6 h-6 text-muted-foreground" strokeWidth={1.5} />
                      </div>
                      <p className="text-sm text-foreground">Click to browse files</p>
                      <p className="text-xs text-muted-foreground mt-1">Secure upload processing</p>
                    </div>
                  )}
                </div>

                <AnimatePresence>
                  {error && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="bg-[#F8D7DA] text-[#791F1F] text-xs p-3 rounded-md border border-[#F5C6CB]"
                    >
                      {error}
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
              <CardFooter className="p-6 flex flex-col gap-2 border-t border-border bg-card">
                <Button 
                  className="w-full h-10 text-sm rounded-md" 
                  onClick={handleUpload} 
                  disabled={!file || loading}
                >
                  {loading ? "Processing..." : "Run AI analysis"}
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full h-10 text-sm rounded-md"
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
