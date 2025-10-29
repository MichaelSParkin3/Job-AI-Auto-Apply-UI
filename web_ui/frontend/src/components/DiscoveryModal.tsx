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
  onRefreshQueue?: () => Promise<void>;
}

export const DiscoveryModal: React.FC<DiscoveryModalProps> = ({
  isOpen,
  onClose,
  profileId,
  onDiscoveryComplete,
  onRefreshQueue,
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
    // Validate before attempting discovery
    if (!validateOptions()) {
      return;
    }

    setIsDiscovering(true);
    setProgress(0);
    setDiscoveredCount(0);
    setStatusMessage("Initializing discovery...");
    setError(null);
    setStep("progress");

    try {
      // Step 1: Validate server connection
      try {
        const healthCheck = await apiClient.get("/api/v1/health");
        if (healthCheck.status !== 200) {
          throw new Error("Backend server is not responding");
        }
      } catch (healthErr) {
        throw new Error("Unable to connect to backend server. Please ensure it's running on localhost:5000");
      }

      // Step 2: Execute discovery with error handling
      let response;
      try {
        response = await apiClient.post("/api/v1/discover/execute", null, {
          params: {
            profile_id: profileId,
            search_window: searchWindow,
            job_cap: jobCap,
            custom_query: customQuery || undefined,
          },
        });
      } catch (discoverErr: any) {
        if (discoverErr.response?.status === 404) {
          throw new Error(`Profile "${profileId}" not found`);
        } else if (discoverErr.response?.status === 400) {
          throw new Error(`Invalid discovery parameters: ${discoverErr.response.data?.detail || "Bad request"}`);
        } else if (discoverErr.response?.status === 500) {
          throw new Error(`Server error during discovery: ${discoverErr.response.data?.detail || "Internal error"}`);
        } else if (discoverErr.message?.includes("timeout")) {
          throw new Error("Discovery timed out. Please try again with a smaller job cap.");
        }
        throw new Error(discoverErr.message || "Discovery failed");
      }

      // Step 3: Process results with validation
      const totalDiscovered = response.data?.total_discovered || 0;
      const totalEnqueued = response.data?.total_enqueued || 0;

      if (totalDiscovered < 0 || totalEnqueued < 0) {
        throw new Error("Invalid discovery results received from server");
      }

      // Update progress
      setProgress(100);
      setStatusMessage(
        totalDiscovered === 0
          ? "No new jobs found matching your criteria"
          : `Found ${totalDiscovered} jobs, ${totalEnqueued} added to queue`
      );

      setTotalDiscovered(totalDiscovered);
      setTotalEnqueued(totalEnqueued);

      // Step 4: Persist options for next time
      try {
        storage.setRunOptions(profileId, "discover", {
          search_window: searchWindow,
          job_cap: jobCap,
          custom_query: customQuery,
        });
      } catch (storageErr) {
        console.warn("Failed to save discovery options:", storageErr);
        // Don't fail the entire discovery if storage fails
      }

      // Step 5: Refresh the queue with newly discovered jobs
      if (onRefreshQueue) {
        try {
          setStatusMessage("Updating job queue...");
          await onRefreshQueue();
          setStatusMessage(
            totalDiscovered === 0
              ? "No new jobs found matching your criteria"
              : `Found ${totalDiscovered} jobs, ${totalEnqueued} added to queue`
          );
        } catch (refreshErr) {
          console.warn("Failed to refresh queue:", refreshErr);
          // Don't fail the entire operation if queue refresh fails
          setStatusMessage(
            totalDiscovered === 0
              ? "No new jobs found matching your criteria"
              : `Found ${totalDiscovered} jobs (queue refresh pending)`
          );
        }
      }

      setStep("results");
      setIsDiscovering(false);

      // Notify parent component of completion
      if (onDiscoveryComplete) {
        onDiscoveryComplete(totalDiscovered);
      }
    } catch (err: any) {
      // Enhanced error reporting
      const errorMessage = err.message || "An unexpected error occurred during discovery";
      setError(errorMessage);
      setStatusMessage("Discovery failed");
      setIsDiscovering(false);

      // Log error for debugging
      console.error("Discovery error:", err);

      // Return to options to allow retry
      setStep("options");
    }
  };

  const handleRetry = () => {
    setError(null);
    setProgress(0);
    setDiscoveredCount(0);
    setStatusMessage("");
    handleDiscover();
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

            <div className="space-y-4 py-4" role="region" aria-label="Discovery options">
              {/* Quick Start Section */}
              <div className="space-y-3">
                <div>
                  <Label
                    htmlFor="search-window"
                    className="text-sm font-medium"
                    aria-required="true"
                  >
                    Search Window
                  </Label>
                  <Select value={searchWindow} onValueChange={setSearchWindow}>
                    <SelectTrigger
                      id="search-window"
                      aria-describedby={errors.searchWindow ? "search-window-error" : undefined}
                      aria-invalid={!!errors.searchWindow}
                    >
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
                    <p
                      id="search-window-error"
                      className="text-xs text-red-500 mt-1"
                      role="alert"
                    >
                      {errors.searchWindow}
                    </p>
                  )}
                </div>

                <div>
                  <Label
                    htmlFor="job-cap"
                    className="text-sm font-medium"
                    aria-required="true"
                  >
                    Job Cap (max jobs to discover)
                  </Label>
                  <p className="text-xs text-gray-500 mb-1">
                    Enter a value between 1 and 1000
                  </p>
                  <Input
                    id="job-cap"
                    type="number"
                    min="1"
                    max="1000"
                    value={jobCap}
                    onChange={(e) => setJobCap(parseInt(e.target.value) || 10)}
                    className="mt-1"
                    aria-describedby={errors.jobCap ? "job-cap-error" : "job-cap-help"}
                    aria-invalid={!!errors.jobCap}
                  />
                  {errors.jobCap ? (
                    <p id="job-cap-error" className="text-xs text-red-500 mt-1" role="alert">
                      {errors.jobCap}
                    </p>
                  ) : (
                    <p id="job-cap-help" className="text-xs text-gray-400 mt-1">
                      Default: 10 jobs
                    </p>
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

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={handleClose}
                aria-label="Close discovery modal without discovering"
              >
                Cancel
              </Button>
              <Button
                onClick={handleDiscover}
                disabled={isDiscovering}
                className="bg-blue-600 hover:bg-blue-700"
                aria-label={isDiscovering ? "Discovery in progress" : "Start job discovery"}
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
              <DialogDescription>
                Searching for job postings. This may take a minute or two.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <label htmlFor="discovery-progress" className="font-medium">
                    Progress
                  </label>
                  <span className="font-medium" aria-live="polite">
                    {progress}%
                  </span>
                </div>
                <Progress
                  id="discovery-progress"
                  value={progress}
                  className="h-2"
                  aria-label="Discovery progress bar"
                />
              </div>

              <Alert>
                <AlertDescription aria-live="polite" aria-atomic="true">
                  {statusMessage || `Discovered ${discoveredCount} jobs...`}
                </AlertDescription>
              </Alert>

              {error && (
                <Alert variant="destructive" role="alert">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </div>

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={isDiscovering}
                aria-label="Cancel discovery"
              >
                Cancel
              </Button>
              {error && (
                <Button
                  onClick={handleRetry}
                  disabled={isDiscovering}
                  className="bg-orange-600 hover:bg-orange-700"
                  aria-label="Retry discovery"
                >
                  Retry
                </Button>
              )}
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
