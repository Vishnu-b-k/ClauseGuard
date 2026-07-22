"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PipelineResultResponse, PolicyDecisionResponse, RedlineSuggestionResponse } from "@/types";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, ShieldAlert, AlertTriangle, CheckCircle, ArrowLeft, Download, FileText, FileWarning, Eye, PenTool, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";

const getRiskColor = (level: string) => {
  switch (level.toLowerCase()) {
    case 'critical': return 'bg-red-500/10 text-red-500 border-red-500/20';
    case 'high': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
    case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    case 'low': return 'bg-green-500/10 text-green-500 border-green-500/20';
    default: return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
  }
};

const getRiskIcon = (level: string) => {
  switch (level.toLowerCase()) {
    case 'critical': return <ShieldAlert className="w-4 h-4 mr-1 text-red-500" />;
    case 'high': return <FileWarning className="w-4 h-4 mr-1 text-orange-500" />;
    case 'medium': return <AlertTriangle className="w-4 h-4 mr-1 text-yellow-500" />;
    default: return <CheckCircle className="w-4 h-4 mr-1 text-green-500" />;
  }
};

export default function ReviewWorkspace() {
  const router = useRouter();
  const [data, setData] = useState<PipelineResultResponse | null>(null);
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);
  const [resolvedClauses, setResolvedClauses] = useState<Record<string, 'approved' | 'rejected'>>({});
  const [exporting, setExporting] = useState(false);

  const handleExport = () => {
    if (!data) return;
    setExporting(true);
    setTimeout(() => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `compliance_report_${data.contract_id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setExporting(false);
    }, 500);
  };

  const advanceToNext = (currentId: string) => {
    if (!data) return;
    const allIds = data.policy_decisions.map(pd => pd.clause_id);
    const currentIndex = allIds.indexOf(currentId);
    if (currentIndex >= 0 && currentIndex < allIds.length - 1) {
      setSelectedClauseId(allIds[currentIndex + 1]);
    }
  };

  const handleApprove = () => {
    if (!selectedClauseId) return;
    setResolvedClauses(prev => ({ ...prev, [selectedClauseId]: 'approved' }));
    advanceToNext(selectedClauseId);
  };

  const handleReject = () => {
    if (!selectedClauseId) return;
    setResolvedClauses(prev => ({ ...prev, [selectedClauseId]: 'rejected' }));
    advanceToNext(selectedClauseId);
  };

  useEffect(() => {
    const storedData = sessionStorage.getItem("analysisResult");
    if (!storedData) {
      router.push("/");
      return;
    }
    const parsedData: PipelineResultResponse = JSON.parse(storedData);
    setData(parsedData);
    
    // Select the first flagged clause by default
    if (parsedData.flagged_for_review.length > 0) {
      setSelectedClauseId(parsedData.flagged_for_review[0]);
    } else if (parsedData.policy_decisions.length > 0) {
      setSelectedClauseId(parsedData.policy_decisions[0].clause_id);
    }
  }, [router]);

  if (!data) return null; // Or a loading spinner

  const selectedDecision = data.policy_decisions.find(pd => pd.clause_id === selectedClauseId);
  const selectedRedline = data.redlines.find(rl => rl.clause_id === selectedClauseId);
  const selectedFinding = data.findings.find(f => f.clause_id === selectedClauseId);

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/")}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-xl font-semibold flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              Human Review Workspace
            </h1>
            <p className="text-sm text-muted-foreground">{data.contract_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="px-3 py-1">
            {data.clauses_processed} Clauses Analyzed
          </Badge>
          <Badge variant="destructive" className="px-3 py-1">
            {data.flagged_for_review.length} Flagged
          </Badge>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting}>
            <Download className="w-4 h-4 mr-2" />
            {exporting ? "Exporting..." : "Export Report"}
          </Button>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Left Sidebar: Clause List */}
        <aside className="w-1/3 border-r border-border flex flex-col bg-muted/20">
          <div className="p-4 border-b border-border bg-card">
            <h2 className="font-semibold text-lg">Analyzed Clauses</h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 flex flex-col gap-3">
              {data.policy_decisions.map((decision) => (
                <Card 
                  key={decision.clause_id} 
                  className={`cursor-pointer transition-all hover:border-primary/50 ${selectedClauseId === decision.clause_id ? 'border-primary ring-1 ring-primary shadow-md' : 'border-border'}`}
                  onClick={() => setSelectedClauseId(decision.clause_id)}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        {resolvedClauses[decision.clause_id] === 'approved' && <CheckCircle className="w-4 h-4 text-green-500" />}
                        {resolvedClauses[decision.clause_id] === 'rejected' && <XCircle className="w-4 h-4 text-red-500" />}
                        <span className={`text-sm font-medium ${resolvedClauses[decision.clause_id] ? 'text-muted-foreground line-through' : 'text-foreground'}`}>
                          {decision.clause_id}
                        </span>
                      </div>
                      <Badge variant="outline" className={getRiskColor(decision.final_risk_level)}>
                        {getRiskIcon(decision.final_risk_level)}
                        {decision.final_risk_level.toUpperCase()}
                      </Badge>
                    </div>
                    {decision.requires_human_review && !resolvedClauses[decision.clause_id] && (
                      <Badge variant="destructive" className="mt-2 text-[10px]">REQUIRES REVIEW</Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </aside>

        {/* Right Panel: Clause Details */}
        <main className="w-2/3 flex flex-col bg-background relative overflow-hidden">
          <AnimatePresence mode="wait">
            {selectedClauseId && selectedDecision && (
              <motion.div 
                key={selectedClauseId}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="flex flex-col h-full"
              >
                <div className="p-6 border-b border-border bg-card">
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                        Clause {selectedDecision.clause_id}
                        {selectedDecision.requires_human_review && (
                          <Badge variant="destructive">Needs Review</Badge>
                        )}
                      </h2>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center">
                          Risk: <Badge variant="outline" className={`ml-2 ${getRiskColor(selectedDecision.final_risk_level)}`}>{selectedDecision.final_risk_level.toUpperCase()}</Badge>
                        </span>
                        <Separator orientation="vertical" className="h-4" />
                        <span className="flex items-center gap-2">
                          AI Confidence: 
                          <Progress value={selectedDecision.original_confidence * 100} className="w-24 h-2" />
                          <span className="font-medium text-foreground">{(selectedDecision.original_confidence * 100).toFixed(0)}%</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-6">
                  <Tabs defaultValue="review" className="w-full">
                    <TabsList className="mb-6 bg-muted/50 border border-border">
                      <TabsTrigger value="review" className="data-[state=active]:bg-background"><Eye className="w-4 h-4 mr-2" /> Evaluation</TabsTrigger>
                      {selectedRedline && <TabsTrigger value="redline" className="data-[state=active]:bg-background"><PenTool className="w-4 h-4 mr-2" /> Redline Suggestion</TabsTrigger>}
                      <TabsTrigger value="evidence" className="data-[state=active]:bg-background"><FileText className="w-4 h-4 mr-2" /> Evidence & Rules</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="review" className="space-y-6">
                      <Card className="border-border">
                        <CardHeader>
                          <CardTitle className="text-lg text-primary">Original Clause Text</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="p-4 bg-muted/30 rounded-md whitespace-pre-wrap text-sm leading-relaxed border border-border/50">
                            {selectedRedline?.original_text || "Text not available in redline context."}
                          </div>
                        </CardContent>
                      </Card>
                      
                      {selectedFinding && (
                        <Card className="border-border">
                          <CardHeader>
                            <CardTitle className="text-lg">Agent Rationale</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className="text-muted-foreground leading-relaxed text-sm">
                              {selectedFinding.rationale}
                            </p>
                          </CardContent>
                        </Card>
                      )}
                    </TabsContent>
                    
                    {selectedRedline && (
                      <TabsContent value="redline" className="space-y-6">
                        <div className="grid grid-cols-2 gap-6">
                          <Card className="border-destructive/20 bg-destructive/5">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm text-destructive flex items-center"><ShieldAlert className="w-4 h-4 mr-2"/> Original Text</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="whitespace-pre-wrap text-sm line-through text-muted-foreground">
                                {selectedRedline.original_text}
                              </div>
                            </CardContent>
                          </Card>
                          
                          <Card className="border-green-500/20 bg-green-500/5">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm text-green-500 flex items-center"><CheckCircle className="w-4 h-4 mr-2"/> Suggested Redline</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="whitespace-pre-wrap text-sm text-foreground">
                                {selectedRedline.suggested_text}
                              </div>
                            </CardContent>
                          </Card>
                        </div>
                        
                        <Card className="border-border">
                          <CardHeader>
                            <CardTitle className="text-lg">Redline Rationale</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className="text-muted-foreground leading-relaxed text-sm mb-4">
                              {selectedRedline.rationale}
                            </p>
                            <div className="p-3 bg-primary/10 text-primary-foreground border border-primary/20 rounded-md text-sm font-medium">
                              <span className="text-primary font-bold mr-2">Executive Summary:</span>
                              {selectedRedline.executive_summary}
                            </div>
                          </CardContent>
                        </Card>
                      </TabsContent>
                    )}

                    <TabsContent value="evidence" className="space-y-6">
                      <Card className="border-border">
                        <CardHeader>
                          <CardTitle className="text-lg">Deterministic Rules Fired</CardTitle>
                          <CardDescription>Rules that influenced the final risk score and routing.</CardDescription>
                        </CardHeader>
                        <CardContent>
                          {selectedDecision.rules_fired.length > 0 ? (
                            <div className="space-y-4">
                              {selectedDecision.rules_fired.map(rule => (
                                <div key={rule.rule_id} className="p-4 border border-border rounded-md bg-muted/20">
                                  <div className="flex justify-between items-center mb-2">
                                    <span className="font-semibold text-primary">{rule.rule_id}</span>
                                    <Badge variant="secondary">{rule.action}</Badge>
                                  </div>
                                  <p className="text-sm text-muted-foreground">{rule.description}</p>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground italic">No specific deterministic rules fired for this clause.</p>
                          )}
                        </CardContent>
                      </Card>
                      
                      {selectedFinding && selectedFinding.policy_refs.length > 0 && (
                        <Card className="border-border">
                          <CardHeader>
                            <CardTitle className="text-lg">Policy References</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="flex flex-wrap gap-2">
                              {selectedFinding.policy_refs.map((ref, idx) => (
                                <Badge key={idx} variant="outline" className="bg-primary/5 text-primary border-primary/20">
                                  {ref}
                                </Badge>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </TabsContent>
                  </Tabs>
                </div>
                
                <div className="p-4 border-t border-border bg-card flex justify-between items-center gap-4">
                  <div className="text-sm font-medium">
                    {resolvedClauses[selectedClauseId] === 'approved' && <span className="text-green-500 flex items-center"><CheckCircle className="w-4 h-4 mr-2"/> Approved</span>}
                    {resolvedClauses[selectedClauseId] === 'rejected' && <span className="text-red-500 flex items-center"><XCircle className="w-4 h-4 mr-2"/> Rejected</span>}
                  </div>
                  <div className="flex gap-4">
                    <Button variant="outline" onClick={handleReject} disabled={!!resolvedClauses[selectedClauseId]}>Reject AI Suggestion</Button>
                    <Button onClick={handleApprove} disabled={!!resolvedClauses[selectedClauseId]}>Approve & Save</Button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
