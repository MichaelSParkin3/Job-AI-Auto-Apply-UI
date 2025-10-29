import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ChevronDown } from "lucide-react";
import { apiClient } from "@/services/api";
import { storage } from "@/services/storage";

interface DiscoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  profileId: string;
  onDiscoveryComplete?: (discoveredCount: number) => void;
}

export const DiscoveryModal: React.FC<DiscoveryModalProps> = ({
  isOpen,
  onClose,
  profileId,
  onDiscoveryComplete,
}) => {
  const [step, setStep] = useState<"options" | "progress" | "results">("options");

  // Form state
  const [searchWindow, setSearchWindow] = useState("24h");
  const [jobCap, setJobCap] = useState(10);
  const [customQuery, setCustomQuery] = useState("");
  const [browserMode, setBrowserMode] = useState("headful");

  // Progress state
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [progress, setProgress] = useState(0);
  const [discoveredCount, setDiscoveredCount] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Results state
  const [totalDiscovered, setTotalDiscovered] = useState(0);
  const [totalEnqueued, setTotalEnqueued] = useState(0);

  // Validation state
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Load last-used options on modal open
  useEffect(() => {
    if (isOpen) {
      loadLastOptions();
    }
  }, [isOpen, profileId]);

  const loadLastOptions = async () => {
    try {
      const response = await apiClient.get(`/api/v1/discover/last-options/${profileId}`);
      const lastOptions = response.data;

      setSearchWindow(lastOptions.search_window || "24h");
      setJobCap(lastOptions.job_cap || 10);
      setCustomQuery(lastOptions.custom_query || "");
    } catch (err) {
      // If loading fails, just use defaults
      console.warn("Failed to load last discovery options", err);
    }
  };

  const validateOptions = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (jobCap < 1 || jobCap > 1000) {
      newErrors.jobCap = "Job cap must be between 1 and 1000";
    }

    if (!searchWindow) {
      newErrors.searchWindow = "Search window is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleDiscover = async () => {
    if (!validateOptions()) {
      return;
    }

    setIsDiscovering(true);
    setProgress(0);
    setDiscoveredCount(0);
    setStatusMessage("Starting discovery...");
    setError(null);
    setStep("progress");

    try {
      // Execute discovery
      const response = await apiClient.post("/api/v1/discover/execute", null, {
        params: {
          profile_id: profileId,
          search_window: searchWindow,
          job_cap: jobCap,
          custom_query: customQuery || undefined,
        },
      });

      // Simulate progress (in real implementation, this would stream from SSE or polling)
      setProgress(100);
      setStatusMessage("Discovery completed");
      setTotalDiscovered(response.data.total_discovered || 0);
      setTotalEnqueued(response.data.total_enqueued || 0);

      // Save options for next time
      storage.setRunOptions(profileId, "discover", {
        search_window: searchWindow,
        job_cap: jobCap,
        custom_query: customQuery,
      });

      setStep("results");
      setIsDiscovering(false);

      if (onDiscoveryComplete) {
        onDiscoveryComplete(response.data.total_discovered || 0);
      }
    } catch (err: any) {
      setError(err.message || "Discovery failed");
      setIsDiscovering(false);
      setStep("options");
    }
  };

  const handleReset = () => {
    setStep("options");
    setProgress(0);
    setDiscoveredCount(0);
    setStatusMessage("");
    setError(null);
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  if (!isOpen) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="w-full max-w-md">
        {step === "options" && (
          <>
            <DialogHeader>
              <DialogTitle>Discover Jobs</DialogTitle>
              <DialogDescription>
                Configure search parameters and discover new job postings
              </DialogDescription>
            </DialogHeader>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-4 py-4">
              {/* Quick Start Section */}
              <div className="space-y-3">
                <div>
                  <Label htmlFor="search-window" className="text-sm font-medium">
                    Search Window
                  </Label>
                  <Select value={searchWindow} onValueChange={setSearchWindow}>
                    <SelectTrigger id="search-window">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1h">Last 1 Hour</SelectItem>
                      <SelectItem value="12h">Last 12 Hours</SelectItem>
                      <SelectItem value="24h">Last 24 Hours</SelectItem>
                      <SelectItem value="7d">Last 7 Days</SelectItem>
                      <SelectItem value="2w">Last 2 Weeks</SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.searchWindow && (
                    <p className="text-xs text-red-500 mt-1">{errors.searchWindow}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="job-cap" className="text-sm font-medium">
                    Job Cap (max jobs to discover)
                  </Label>
                  <Input
                    id="job-cap"
                    type="number"
                    min="1"
                    max="1000"
                    value={jobCap}
                    onChange={(e) => setJobCap(parseInt(e.target.value) || 10)}
                    className="mt-1"
                  />
                  {errors.jobCap && (
                    <p className="text-xs text-red-500 mt-1">{errors.jobCap}</p>
                  )}
                </div>
              </div>

              {/* Advanced Options */}
              <Collapsible>
                <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:text-gray-700 dark:hover:text-gray-300">
                  <ChevronDown className="h-4 w-4" />
                  Advanced Options
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-3 pt-3">
                  <div>
                    <Label htmlFor="custom-query" className="text-sm font-medium">
                      Custom Search Query (optional)
                    </Label>
                    <Input
                      id="custom-query"
                      type="text"
                      placeholder="e.g., Python developer remote"
                      value={customQuery}
                      onChange={(e) => setCustomQuery(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <Label htmlFor="browser-mode" className="text-sm font-medium">
                      Browser Mode
                    </Label>
                    <Select value={browserMode} onValueChange={setBrowserMode}>
                      <SelectTrigger id="browser-mode">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="headful">Visible Browser</SelectItem>
                        <SelectItem value="headless">Headless (Hidden)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={handleDiscover}
                disabled={isDiscovering}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isDiscovering ? "Discovering..." : "Discover"}
              </Button>
            </DialogFooter>
          </>
        )}

        {step === "progress" && (
          <>
            <DialogHeader>
              <DialogTitle>Discovery in Progress</DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Progress</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>

              <Alert>
                <AlertDescription>
                  {statusMessage || `Discovered ${discoveredCount} jobs...`}
                </AlertDescription>
              </Alert>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose} disabled={isDiscovering}>
                Cancel
              </Button>
            </DialogFooter>
          </>
        )}

        {step === "results" && (
          <>
            <DialogHeader>
              <DialogTitle>Discovery Complete</DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <Alert>
                <AlertDescription>
                  <div className="space-y-2">
                    <div>
                      <span className="font-medium">Total Discovered:</span> {totalDiscovered}
                    </div>
                    <div>
                      <span className="font-medium">Added to Queue:</span> {totalEnqueued}
                    </div>
                  </div>
                </AlertDescription>
              </Alert>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleReset}>
                Discover Again
              </Button>
              <Button onClick={handleClose} className="bg-blue-600 hover:bg-blue-700">
                Done
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
