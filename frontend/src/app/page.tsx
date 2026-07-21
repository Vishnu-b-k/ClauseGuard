"use client";

import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Upload, ShieldAlert, FileText, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { analyzeContract } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function Home() {
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
      // Store result in sessionStorage to pass to the review page
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
    <main className="flex min-h-screen flex-col items-center justify-center p-6 lg:p-24 bg-gradient-to-br from-background to-secondary/20">
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-5xl flex flex-col items-center text-center mb-12"
      >
        <div className="bg-primary/10 p-4 rounded-full mb-6">
          <ShieldAlert className="w-12 h-12 text-primary" />
        </div>
        <h1 className="text-4xl lg:text-6xl font-extrabold tracking-tight mb-6">
          Legal AI <span className="text-primary">Contract Compliance</span>
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl">
          Enterprise-grade automated contract review. Powered by dual-agent reasoning and deterministic policy validation to identify, evaluate, and redline risks.
        </p>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="w-full max-w-md"
      >
        <Card className="border-primary/20 shadow-2xl bg-background/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Analyze Contract</CardTitle>
            <CardDescription>Upload a PDF, DOCX, or TXT file for instant AI analysis.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-6">
            <div 
              className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${file ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}`}
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
                <>
                  <FileText className="w-10 h-10 text-primary mb-4" />
                  <p className="font-medium text-foreground">{file.name}</p>
                  <p className="text-xs text-muted-foreground mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                </>
              ) : (
                <>
                  <Upload className="w-10 h-10 text-muted-foreground mb-4" />
                  <p className="font-medium text-foreground">Click to upload a document</p>
                  <p className="text-xs text-muted-foreground mt-1">Supports .pdf, .docx, .txt (Max 25MB)</p>
                </>
              )}
            </div>

            {error && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {error}
              </div>
            )}
          </CardContent>
          <CardFooter>
            <Button 
              className="w-full group" 
              size="lg" 
              onClick={handleUpload} 
              disabled={!file || loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Analyzing with Agents...
                </>
              ) : (
                <>
                  Start Analysis
                  <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </Button>
          </CardFooter>
        </Card>
      </motion.div>
    </main>
  );
}
