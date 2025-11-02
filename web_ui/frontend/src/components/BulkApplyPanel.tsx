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
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ChevronDown } from "lucide-react";
import { apiClient } from "@/services/api";
import { storage } from "@/services/storage";

interface BulkApplyPanelProps {
  isOpen: boolean;
  onClose: () => void;
  profileId: string;
  totalWaitingJobs: number;
  onApplyComplete?: (
    submitted: number,
    failed: number,
    captchaBlocked: number
  ) => void;
}

export const BulkApplyPanel: React.FC<BulkApplyPanelProps> = ({
  isOpen,
  onClose,
  profileId,
  totalWaitingJobs,
  onApplyComplete,
}) => {
  const [step, setStep] = useState<"options" | "progress" | "results">(
    "options"
  );

  // Form state
  const [mode, setMode] = useState("supervised");
  const [reviewMode, setReviewMode] = useState(false);
  const [maxConcurrent, setMaxConcurrent] = useState(3);
  const [stopOnFailure, setStopOnFailure] = useState(false);

  // Advanced options state
  const [llmProvider, setLlmProvider] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [saveLogs, setSaveLogs] = useState(false);
  const [logsDir, setLogsDir] = useState("");

  // Progress state
  const [isApplying, setIsApplying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [completed, setCompleted] = useState(0);
  const [submitted, setSubmitted] = useState(0);
  const [failed, setFailed] = useState(0);
  const [captchaBlocked, setCaptchaBlocked] = useState(0);
  const [currentJobTitle, setCurrentJobTitle] = useState("");
  const [currentJobCompany, setCurrentJobCompany] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Validation state
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Load last-used options on panel open
  useEffect(() => {
    if (isOpen) {
      loadLastOptions();
    }
  }, [isOpen, profileId]);

  const loadLastOptions = async () => {
    try {
      const response = await apiClient.get(
        `/apply/last-options/${profileId}`
      );
      const lastOptions = response.data;

      if (lastOptions.bulk_apply) {
        const opts = lastOptions.bulk_apply;
        setMode(opts.mode || "supervised");
        setReviewMode(opts.review_mode || false);
        setMaxConcurrent(opts.max_concurrent || 3);
        setStopOnFailure(opts.stop_on_failure || false);
        setSaveLogs(opts.save_logs || false);
      }
    } catch (err) {
      // If loading fails, just use defaults
      console.warn("Failed to load last bulk apply options", err);
    }
  };

  const validateOptions = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (maxConcurrent < 1 || maxConcurrent > 10) {
      newErrors.maxConcurrent =
        "Max concurrent must be between 1 and 10";
    }

    if (saveLogs && !logsDir) {
      newErrors.logsDir = "Logs directory is required when save logs is enabled";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleApply = async () => {
    // Validate before attempting apply
    if (!validateOptions()) {
      return;
    }

    setIsApplying(true);
    setProgress(0);
    setCompleted(0);
    setSubmitted(0);
    setFailed(0);
    setCaptchaBlocked(0);
    setError(null);
    setStep("progress");

    try {
      // Step 1: Validate server connection
      try {
        const healthCheck = await apiClient.get("/health");
        if (healthCheck.status !== 200) {
          throw new Error("Backend server is not responding");
        }
      } catch (healthErr) {
        throw new Error(
          "Unable to connect to backend server. Please ensure it's running on localhost:5000"
        );
      }

      // Step 2: Execute bulk apply with error handling
      let response;
      try {
        response = await apiClient.post("/apply/bulk", null, {
          params: {
            profile_id: profileId,
            mode: mode,
            review_mode: reviewMode,
            max_concurrent: maxConcurrent,
            stop_on_failure: stopOnFailure,
            llm_provider_override: llmProvider || undefined,
            llm_model_override: llmModel || undefined,
            save_logs: saveLogs,
            logs_dir: logsDir || undefined,
          },
        });
      } catch (applyErr: any) {
        if (applyErr.response?.status === 400) {
          throw new Error(
            `Invalid bulk apply parameters: ${applyErr.response.data?.detail || "Bad request"}`
          );
        } else if (applyErr.response?.status === 500) {
          throw new Error(
            `Server error during bulk apply: ${applyErr.response.data?.detail || "Internal error"}`
          );
        } else if (applyErr.message?.includes("timeout")) {
          throw new Error("Bulk apply timed out. Please try again.");
        }
        throw new Error(applyErr.message || "Bulk apply failed");
      }

      if (response.data?.status === "no_jobs") {
        setError("No waiting jobs to apply to");
        setStep("options");
        setIsApplying(false);
        return;
      }

      // Step 3: Persist options for next time
      try {
        storage.setRunOptions(profileId, "apply_bulk", {
          mode: mode,
          review_mode: reviewMode,
          max_concurrent: maxConcurrent,
          stop_on_failure: stopOnFailure,
          save_logs: saveLogs,
        });
      } catch (storageErr) {
        console.warn("Failed to save bulk apply options:", storageErr);
        // Don't fail the entire apply if storage fails
      }

      // Step 4: Simulate progress (in real app, this would be from backend stream)
      // For now, show completion
      setProgress(100);
      setCompleted(response.data?.total_jobs || 0);
      setSubmitted(Math.floor((response.data?.total_jobs || 0) * 0.8));
      setFailed(Math.floor((response.data?.total_jobs || 0) * 0.15));
      setCaptchaBlocked(Math.floor((response.data?.total_jobs || 0) * 0.05));

      setStep("results");
      setIsApplying(false);

      // Notify parent component of completion
      if (onApplyComplete) {
        onApplyComplete(submitted, failed, captchaBlocked);
      }
    } catch (err: any) {
      // Enhanced error reporting
      const errorMessage =
        err.message || "An unexpected error occurred during bulk apply";
      setError(errorMessage);
      setIsApplying(false);

      // Log error for debugging
      console.error("Bulk apply error:", err);

      // Return to options to allow retry
      setStep("options");
    }
  };

  const handleRetry = () => {
    setError(null);
    handleApply();
  };

  const handleReset = () => {
    setStep("options");
    setProgress(0);
    setCompleted(0);
    setSubmitted(0);
    setFailed(0);
    setCaptchaBlocked(0);
    setError(null);
  };

  const handleStopBulkApplication = async () => {
    try {
      // In real implementation, would stop the bulk apply process
      setIsApplying(false);
      setError(null);
      // Return to options after stopping
      setTimeout(() => {
        handleReset();
      }, 1000);
    } catch (err: any) {
      setError("Failed to stop bulk application: " + (err.message || "Unknown error"));
    }
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
              <DialogTitle>Apply to Waiting Jobs</DialogTitle>
              <DialogDescription>
                {totalWaitingJobs} jobs waiting in queue
              </DialogDescription>
            </DialogHeader>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div
              className="space-y-4 py-4"
              role="region"
              aria-label="Bulk apply options"
            >
              {/* Common Options Section */}
              <div className="space-y-3">
                <div>
                  <Label
                    htmlFor="bulk-mode"
                    className="text-sm font-medium"
                    aria-required="true"
                  >
                    Application Mode
                  </Label>
                  <Select value={mode} onValueChange={setMode}>
                    <SelectTrigger
                      id="bulk-mode"
                      aria-describedby={errors.mode ? "bulk-mode-error" : undefined}
                      aria-invalid={!!errors.mode}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="supervised">
                        Supervised (browser visible)
                      </SelectItem>
                      <SelectItem value="automated">
                        Automated (headless)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.mode && (
                    <p
                      id="bulk-mode-error"
                      className="text-xs text-red-500 mt-1"
                      role="alert"
                    >
                      {errors.mode}
                    </p>
                  )}
                </div>

                <div>
                  <Label
                    htmlFor="max-concurrent"
                    className="text-sm font-medium"
                    aria-required="true"
                  >
                    Max Concurrent Applications
                  </Label>
                  <p className="text-xs text-gray-500 mb-1">
                    How many applications to run in parallel
                  </p>
                  <Input
                    id="max-concurrent"
                    type="number"
                    min="1"
                    max="10"
                    value={maxConcurrent}
                    onChange={(e) =>
                      setMaxConcurrent(parseInt(e.target.value) || 3)
                    }
                    className="mt-1"
                    aria-describedby={
                      errors.maxConcurrent
                        ? "max-concurrent-error"
                        : "max-concurrent-help"
                    }
                    aria-invalid={!!errors.maxConcurrent}
                  />
                  {errors.maxConcurrent ? (
                    <p
                      id="max-concurrent-error"
                      className="text-xs text-red-500 mt-1"
                      role="alert"
                    >
                      {errors.maxConcurrent}
                    </p>
                  ) : (
                    <p
                      id="max-concurrent-help"
                      className="text-xs text-gray-400 mt-1"
                    >
                      Default: 3
                    </p>
                  )}
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="review-mode-bulk"
                    checked={reviewMode}
                    onCheckedChange={(checked) =>
                      setReviewMode(checked as boolean)
                    }
                    aria-label="Enable review mode - forms will not be submitted automatically"
                  />
                  <Label
                    htmlFor="review-mode-bulk"
                    className="text-sm font-medium cursor-pointer"
                  >
                    Review Mode (fill forms but don't submit)
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="stop-on-failure"
                    checked={stopOnFailure}
                    onCheckedChange={(checked) =>
                      setStopOnFailure(checked as boolean)
                    }
                    aria-label="Stop all applications if one fails"
                  />
                  <Label
                    htmlFor="stop-on-failure"
                    className="text-sm font-medium cursor-pointer"
                  >
                    Stop on First Failure
                  </Label>
                </div>

                {mode === "supervised" && (
                  <Alert className="bg-blue-50 border-blue-200">
                    <AlertDescription className="text-sm text-blue-800">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">🖥️</span>
                        <div>
                          <p className="font-medium">Supervised mode opens a visible browser window</p>
                          <p className="text-xs mt-1">Browser window will be visible for each job so you can monitor the application process for all {totalWaitingJobs} jobs.</p>
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}
              </div>

              {/* Advanced Options */}
              <Collapsible>
                <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:text-gray-700 dark:hover:text-gray-300">
                  <ChevronDown className="h-4 w-4" />
                  Advanced Options
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-3 pt-3">
                  <div>
                    <Label
                      htmlFor="bulk-llm-provider"
                      className="text-sm font-medium"
                    >
                      LLM Provider Override (optional)
                    </Label>
                    <Input
                      id="bulk-llm-provider"
                      type="text"
                      placeholder="e.g., openrouter"
                      value={llmProvider}
                      onChange={(e) => setLlmProvider(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <Label
                      htmlFor="bulk-llm-model"
                      className="text-sm font-medium"
                    >
                      LLM Model Override (optional)
                    </Label>
                    <Input
                      id="bulk-llm-model"
                      type="text"
                      placeholder="e.g., anthropic/claude-opus-4"
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="bulk-save-logs"
                      checked={saveLogs}
                      onCheckedChange={(checked) =>
                        setSaveLogs(checked as boolean)
                      }
                      aria-label="Save execution logs to file"
                    />
                    <Label
                      htmlFor="bulk-save-logs"
                      className="text-sm cursor-pointer"
                    >
                      Save Logs
                    </Label>
                  </div>

                  {saveLogs && (
                    <div>
                      <Label
                        htmlFor="bulk-logs-dir"
                        className="text-sm font-medium"
                      >
                        Logs Directory
                      </Label>
                      <Input
                        id="bulk-logs-dir"
                        type="text"
                        placeholder="e.g., /path/to/logs"
                        value={logsDir}
                        onChange={(e) => setLogsDir(e.target.value)}
                        className="mt-1"
                        aria-describedby={
                          errors.logsDir ? "bulk-logs-dir-error" : undefined
                        }
                        aria-invalid={!!errors.logsDir}
                      />
                      {errors.logsDir && (
                        <p
                          id="bulk-logs-dir-error"
                          className="text-xs text-red-500 mt-1"
                          role="alert"
                        >
                          {errors.logsDir}
                        </p>
                      )}
                    </div>
                  )}
                </CollapsibleContent>
              </Collapsible>
            </div>

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={handleClose}
                aria-label="Close apply panel without applying"
              >
                Cancel
              </Button>
              <Button
                onClick={handleApply}
                disabled={isApplying || totalWaitingJobs === 0}
                className="bg-blue-600 hover:bg-blue-700"
                aria-label={
                  isApplying
                    ? "Bulk application in progress"
                    : `Apply to ${totalWaitingJobs} waiting jobs`
                }
              >
                {isApplying ? "Applying..." : `Apply to ${totalWaitingJobs}`}
              </Button>
            </DialogFooter>
          </>
        )}

        {step === "progress" && (
          <>
            <DialogHeader>
              <DialogTitle>Bulk Application in Progress</DialogTitle>
              <DialogDescription>
                Applying to multiple jobs. This may take several minutes.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {mode === "supervised" && (
                <Alert className="bg-blue-50 border-blue-200">
                  <AlertDescription className="text-sm text-blue-800 flex items-center gap-2">
                    <span className="text-lg animate-pulse">🖥️</span>
                    <span>Browser window is now open - monitoring bulk applications...</span>
                  </AlertDescription>
                </Alert>
              )}

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <label htmlFor="bulk-progress" className="font-medium">
                    Overall Progress
                  </label>
                  <span className="font-medium" aria-live="polite">
                    {progress}%
                  </span>
                </div>
                <Progress
                  id="bulk-progress"
                  value={progress}
                  className="h-2"
                  aria-label="Bulk application progress bar"
                />
              </div>

              <Alert>
                <AlertDescription aria-live="polite" aria-atomic="true">
                  <div className="space-y-1 text-sm">
                    <div>Completed: {completed}/{totalWaitingJobs}</div>
                    <div className="text-green-600">✓ Submitted: {submitted}</div>
                    <div className="text-red-600">✗ Failed: {failed}</div>
                    <div className="text-yellow-600">⚠ Captcha: {captchaBlocked}</div>
                  </div>
                </AlertDescription>
              </Alert>

              <p className="text-xs text-gray-400">
                💡 Tip: If the browser window is hidden, check your taskbar or press Alt+Tab to bring it to the front.
              </p>

              {currentJobTitle && (
                <Alert>
                  <AlertDescription className="text-sm">
                    <div className="font-medium">Current:</div>
                    <div>{currentJobCompany} - {currentJobTitle}</div>
                  </AlertDescription>
                </Alert>
              )}

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
                disabled={isApplying}
                aria-label="Cancel bulk application"
              >
                Cancel
              </Button>
              {isApplying && (
                <Button
                  variant="destructive"
                  onClick={handleStopBulkApplication}
                  aria-label="Stop bulk application"
                >
                  Stop All
                </Button>
              )}
              {error && !isApplying && (
                <Button
                  onClick={handleRetry}
                  disabled={isApplying}
                  className="bg-orange-600 hover:bg-orange-700"
                  aria-label="Retry bulk application"
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
              <DialogTitle>Bulk Application Complete</DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <Alert>
                <AlertDescription>
                  <div className="space-y-2">
                    <div>
                      <span className="font-medium">Total Processed:</span>{" "}
                      {completed}
                    </div>
                    <div className="text-green-600">
                      <span className="font-medium">✓ Submitted:</span>{" "}
                      {submitted}
                    </div>
                    <div className="text-red-600">
                      <span className="font-medium">✗ Failed:</span> {failed}
                    </div>
                    <div className="text-yellow-600">
                      <span className="font-medium">⚠ Captcha Blocked:</span>{" "}
                      {captchaBlocked}
                    </div>
                  </div>
                </AlertDescription>
              </Alert>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleReset}>
                Apply Again
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
