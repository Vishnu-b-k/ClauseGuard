"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, ShieldAlert, FileText, ArrowRight, Loader2, Sparkles, Zap, ShieldCheck } from "lucide-react";
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
    setPollingStatus("Uploading to S3 & Queuing Task...");
    setError(null);
    
    try {
      const { task_id } = await analyzeContract(file);
      
      // Polling loop
      setPollingStatus("Processing Document with AI Agents...");
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await checkContractStatus(task_id);
          
          if (statusRes.status === "completed" && statusRes.result) {
            clearInterval(pollInterval);
            sessionStorage.setItem("analysisResult", JSON.stringify(statusRes.result));
            router.push("/review");
          } else if (statusRes.state === "FAILURE") {
            clearInterval(pollInterval);
            setError("Analysis failed in background worker.");
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
      setError(err.response?.data?.detail || "An unexpected error occurred during analysis.");
      setLoading(false);
      setPollingStatus(null);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 lg:p-24 bg-[#F1EFE8] relative overflow-hidden text-[#2C2C2A]">
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
            <h1 className="text-4xl lg:text-5xl font-semibold tracking-tight mb-4 text-[#2C2C2A]">
              ClauseGuard contract intelligence
            </h1>
            
            <p className="text-lg text-[#2C2C2A]/80 max-w-3xl mb-12 leading-relaxed font-light">
              Automate enterprise contract review with dual-agent reasoning and deterministic risk validation. Identify liabilities and generate redlines in seconds.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 mb-16">
              <Button 
                size="lg" 
                className="h-12 px-8 text-base rounded-md bg-[#2C2C2A] text-white hover:bg-[#2C2C2A]/90 shadow-md transition-all hover:scale-105"
                onClick={() => setShowUpload(true)}
              >
                Dive in
              </Button>
            </div>

            <motion.div 
              initial="hidden"
              animate="visible"
              variants={{
                hidden: { opacity: 0 },
                visible: {
                  opacity: 1,
                  transition: { staggerChildren: 0.1, delayChildren: 0.1 }
                }
              }}
              className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl text-left"
            >
              <motion.div variants={{ hidden: { opacity: 0, y: 15 }, visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } } }} whileHover={{ y: -4, scale: 1.02 }} className="p-6 rounded-xl bg-white border border-gray-200 shadow-sm transition-all hover:shadow-md">
                <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-[#2C2C2A] mb-4 border border-gray-200">
                  Dual-agent reasoning
                </div>
                <p className="text-[#2C2C2A]/90 text-sm leading-relaxed">Agentic AI analyzes risks and suggests actionable redlines directly on the document text.</p>
              </motion.div>
              <motion.div variants={{ hidden: { opacity: 0, y: 15 }, visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } } }} whileHover={{ y: -4, scale: 1.02 }} className="p-6 rounded-xl bg-white border border-gray-200 shadow-sm transition-all hover:shadow-md">
                <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-[#2C2C2A] mb-4 border border-gray-200">
                  Hybrid retrieval
                </div>
                <p className="text-[#2C2C2A]/90 text-sm leading-relaxed">Grounds every decision against your standard clauses using Qdrant vector search.</p>
              </motion.div>
              <motion.div variants={{ hidden: { opacity: 0, y: 15 }, visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } } }} whileHover={{ y: -4, scale: 1.02 }} className="p-6 rounded-xl bg-white border border-gray-200 shadow-sm transition-all hover:shadow-md">
                <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 mb-4 border border-red-100">
                  Policy validator
                </div>
                <p className="text-[#2C2C2A]/90 text-sm leading-relaxed">Deterministic rule engine ensures no high-risk clause slips past the automated review.</p>
              </motion.div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.6 }}
              className="mt-16 w-full max-w-4xl"
            >
              <p className="text-xs text-[#2C2C2A]/60 font-medium tracking-wide uppercase mb-6">The greatest legal minds agree</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <motion.div whileHover={{ scale: 1.03, y: -2 }} className="flex flex-col items-start text-left p-6 bg-white rounded-xl border border-gray-200 shadow-sm transition-all hover:shadow-md">
                  <p className="text-[#2C2C2A] italic text-sm leading-relaxed mb-4">"When you need a *criminal* lawyer... but for contracts, ClauseGuard is the only call you make."</p>
                  <p className="font-semibold text-[#2C2C2A] text-sm">Saul Goodman</p>
                  <p className="text-xs text-[#2C2C2A]/60 font-medium">Albuquerque, NM</p>
                </motion.div>
                <motion.div whileHover={{ scale: 1.03, y: -2 }} className="flex flex-col items-start text-left p-6 bg-white rounded-xl border border-gray-200 shadow-sm transition-all hover:shadow-md">
                  <p className="text-[#2C2C2A] italic text-sm leading-relaxed mb-4">"Justice is blind, but ClauseGuard's radar-sense precision sees every hidden liability."</p>
                  <p className="font-semibold text-[#2C2C2A] text-sm">Matt Murdock</p>
                  <p className="text-xs text-[#2C2C2A]/60 font-medium">Hell's Kitchen, NY</p>
                </motion.div>
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
            <Card className="border border-gray-200 shadow-lg bg-white rounded-xl overflow-hidden">
              <CardHeader className="pt-6 border-b border-gray-100 bg-gray-50/50">
                <CardTitle className="text-lg font-semibold text-[#2C2C2A]">Analyze contract</CardTitle>
                <CardDescription className="text-sm text-[#2C2C2A]/70">Upload a PDF, DOCX, or TXT file</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-4 p-8">
                <div 
                  className={`border-2 border-dashed rounded-lg p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-300 ${file ? 'border-blue-300 bg-blue-50/50' : 'border-gray-300 hover:border-[#2C2C2A]/40 hover:bg-gray-50'}`}
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
                      <div className="p-3 border border-blue-200 rounded-lg mb-3 bg-white shadow-sm">
                        <FileText className="w-8 h-8 text-blue-600" strokeWidth={1.5} />
                      </div>
                      <p className="font-semibold text-[#2C2C2A] text-sm">{file.name}</p>
                      <p className="text-xs text-[#2C2C2A]/60 mt-1 font-medium">{(file.size / 1024).toFixed(1)} KB</p>
                    </motion.div>
                  ) : (
                    <motion.div whileHover={{ scale: 1.05 }} className="flex flex-col items-center">
                      <div className="p-3 border border-gray-200 rounded-lg mb-3 bg-white shadow-sm">
                        <Upload className="w-8 h-8 text-gray-500" strokeWidth={1.5} />
                      </div>
                      <p className="text-sm font-medium text-[#2C2C2A]/80">Click to browse files</p>
                    </motion.div>
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
              <CardFooter className="p-6 flex flex-col gap-3 border-t border-gray-100 bg-gray-50/50">
                <Button 
                  className="w-full h-12 text-sm rounded-md font-medium bg-[#2C2C2A] text-white hover:bg-[#2C2C2A]/90 transition-all shadow-sm" 
                  onClick={handleUpload} 
                  disabled={!file || loading}
                >
                  {loading ? (pollingStatus || "Processing...") : "Run AI analysis"}
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full h-12 text-sm rounded-md font-medium border-gray-300 text-[#2C2C2A] hover:bg-gray-100"
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
