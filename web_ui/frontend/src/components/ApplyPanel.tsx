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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ChevronDown } from "lucide-react";
import { apiClient } from "@/services/api";
import { storage } from "@/services/storage";

interface ApplyPanelProps {
  isOpen: boolean;
  onClose: () => void;
  profileId: string;
  jobId: string;
  jobTitle: string;
  jobCompany: string;
  onApplyComplete?: (jobId: string, status: string) => void;
}

export const ApplyPanel: React.FC<ApplyPanelProps> = ({
  isOpen,
  onClose,
  profileId,
  jobId,
  jobTitle,
  jobCompany,
  onApplyComplete,
}) => {
  const [step, setStep] = useState<"options" | "progress" | "results">(
    "options"
  );

  // Form state
  const [mode, setMode] = useState("supervised");
  const [reviewMode, setReviewMode] = useState(false);

  // Advanced options state
  const [llmProvider, setLlmProvider] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [useLlmLocator, setUseLlmLocator] = useState(false);
  const [debugResumeWidget, setDebugResumeWidget] = useState(false);
  const [resumeWaitTimeout, setResumeWaitTimeout] = useState(25);
  const [auditAfterSubmit, setAuditAfterSubmit] = useState(false);
  const [saveLogs, setSaveLogs] = useState(false);
  const [logsDir, setLogsDir] = useState("");

  // Progress state
  const [isApplying, setIsApplying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Results state
  const [resultStatus, setResultStatus] = useState("");
  const [confirmationId, setConfirmationId] = useState("");
  const [confirmationText, setConfirmationText] = useState("");

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
        `/api/v1/apply/last-options/${profileId}`
      );
      const lastOptions = response.data;

      if (lastOptions.single_apply) {
        const opts = lastOptions.single_apply;
        setMode(opts.mode || "supervised");
        setReviewMode(opts.review_mode || false);
        setUseLlmLocator(opts.use_llm_locator || false);
        setDebugResumeWidget(opts.debug_resume_widget || false);
        setResumeWaitTimeout(opts.resume_wait_timeout || 25);
        setAuditAfterSubmit(opts.audit_after_submit || false);
        setSaveLogs(opts.save_logs || false);
      }
    } catch (err) {
      // If loading fails, just use defaults
      console.warn("Failed to load last apply options", err);
    }
  };

  const validateOptions = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (resumeWaitTimeout < 5 || resumeWaitTimeout > 120) {
      newErrors.resumeWaitTimeout =
        "Resume timeout must be between 5 and 120 seconds";
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
    setStatusMessage("Initializing application...");
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
        throw new Error(
          "Unable to connect to backend server. Please ensure it's running on localhost:5000"
        );
      }

      // Step 2: Execute apply with error handling
      let response;
      try {
        response = await apiClient.post("/api/v1/apply/single", null, {
          params: {
            profile_id: profileId,
            job_id: jobId,
            mode: mode,
            review_mode: reviewMode,
            llm_provider_override: llmProvider || undefined,
            llm_model_override: llmModel || undefined,
            use_llm_locator: useLlmLocator,
            debug_resume_widget: debugResumeWidget,
            resume_wait_timeout: resumeWaitTimeout,
            audit_after_submit: auditAfterSubmit,
            save_logs: saveLogs,
            logs_dir: logsDir || undefined,
          },
        });
      } catch (applyErr: any) {
        if (applyErr.response?.status === 404) {
          throw new Error(`Job "${jobId}" not found`);
        } else if (applyErr.response?.status === 400) {
          throw new Error(
            `Invalid apply parameters: ${applyErr.response.data?.detail || "Bad request"}`
          );
        } else if (applyErr.response?.status === 500) {
          throw new Error(
            `Server error during apply: ${applyErr.response.data?.detail || "Internal error"}`
          );
        } else if (applyErr.message?.includes("timeout")) {
          throw new Error("Application timed out. Please try again.");
        }
        throw new Error(applyErr.message || "Application failed");
      }

      // Step 3: Update progress to completion
      setProgress(100);
      setStatusMessage("Application submitted successfully!");

      setResultStatus("submitted");
      setConfirmationId(response.data?.confirmation_id || "");
      setConfirmationText(response.data?.confirmation_text || "");

      // Step 4: Persist options for next time
      try {
        storage.setRunOptions(profileId, "apply_single", {
          mode: mode,
          review_mode: reviewMode,
          use_llm_locator: useLlmLocator,
          debug_resume_widget: debugResumeWidget,
          resume_wait_timeout: resumeWaitTimeout,
          audit_after_submit: auditAfterSubmit,
          save_logs: saveLogs,
        });
      } catch (storageErr) {
        console.warn("Failed to save apply options:", storageErr);
        // Don't fail the entire apply if storage fails
      }

      setStep("results");
      setIsApplying(false);

      // Notify parent component of completion
      if (onApplyComplete) {
        onApplyComplete(jobId, "submitted");
      }
    } catch (err: any) {
      // Enhanced error reporting
      const errorMessage =
        err.message || "An unexpected error occurred during application";
      setError(errorMessage);
      setStatusMessage("Application failed");
      setIsApplying(false);

      // Log error for debugging
      console.error("Apply error:", err);

      // Return to options to allow retry
      setStep("options");
    }
  };

  const handleRetry = () => {
    setError(null);
    setProgress(0);
    setStatusMessage("");
    handleApply();
  };

  const handleReset = () => {
    setStep("options");
    setProgress(0);
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
              <DialogTitle>Apply to Job</DialogTitle>
              <DialogDescription>
                {jobCompany} - {jobTitle}
              </DialogDescription>
            </DialogHeader>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-4 py-4" role="region" aria-label="Apply options">
              {/* Quick Start Section */}
              <div className="space-y-3">
                <div>
                  <Label
                    htmlFor="apply-mode"
                    className="text-sm font-medium"
                    aria-required="true"
                  >
                    Application Mode
                  </Label>
                  <Select value={mode} onValueChange={setMode}>
                    <SelectTrigger
                      id="apply-mode"
                      aria-describedby={errors.mode ? "apply-mode-error" : undefined}
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
                      id="apply-mode-error"
                      className="text-xs text-red-500 mt-1"
                      role="alert"
                    >
                      {errors.mode}
                    </p>
                  )}
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="review-mode"
                    checked={reviewMode}
                    onCheckedChange={(checked) => setReviewMode(checked as boolean)}
                    aria-label="Enable review mode - form will not be submitted automatically"
                  />
                  <Label
                    htmlFor="review-mode"
                    className="text-sm font-medium cursor-pointer"
                  >
                    Review Mode (fill form but don't submit)
                  </Label>
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
                    <Label
                      htmlFor="llm-provider"
                      className="text-sm font-medium"
                    >
                      LLM Provider Override (optional)
                    </Label>
                    <Input
                      id="llm-provider"
                      type="text"
                      placeholder="e.g., openrouter"
                      value={llmProvider}
                      onChange={(e) => setLlmProvider(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <Label htmlFor="llm-model" className="text-sm font-medium">
                      LLM Model Override (optional)
                    </Label>
                    <Input
                      id="llm-model"
                      type="text"
                      placeholder="e.g., anthropic/claude-opus-4"
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm font-medium">Resume Upload Diagnostics</p>

                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="use-llm-locator"
                        checked={useLlmLocator}
                        onCheckedChange={(checked) =>
                          setUseLlmLocator(checked as boolean)
                        }
                        aria-label="Use LLM for resume upload element finding"
                      />
                      <Label
                        htmlFor="use-llm-locator"
                        className="text-sm cursor-pointer"
                      >
                        Use LLM Element Locator
                      </Label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="debug-resume-widget"
                        checked={debugResumeWidget}
                        onCheckedChange={(checked) =>
                          setDebugResumeWidget(checked as boolean)
                        }
                        aria-label="Enable resume widget debugging"
                      />
                      <Label
                        htmlFor="debug-resume-widget"
                        className="text-sm cursor-pointer"
                      >
                        Debug Resume Widget
                      </Label>
                    </div>

                    <div>
                      <Label
                        htmlFor="resume-timeout"
                        className="text-sm font-medium"
                        aria-required="true"
                      >
                        Resume Upload Timeout (seconds)
                      </Label>
                      <Input
                        id="resume-timeout"
                        type="number"
                        min="5"
                        max="120"
                        value={resumeWaitTimeout}
                        onChange={(e) =>
                          setResumeWaitTimeout(parseInt(e.target.value) || 25)
                        }
                        className="mt-1"
                        aria-describedby={
                          errors.resumeWaitTimeout
                            ? "resume-timeout-error"
                            : undefined
                        }
                        aria-invalid={!!errors.resumeWaitTimeout}
                      />
                      {errors.resumeWaitTimeout ? (
                        <p
                          id="resume-timeout-error"
                          className="text-xs text-red-500 mt-1"
                          role="alert"
                        >
                          {errors.resumeWaitTimeout}
                        </p>
                      ) : (
                        <p id="resume-timeout-help" className="text-xs text-gray-400 mt-1">
                          Default: 25 seconds
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="audit-after-submit"
                      checked={auditAfterSubmit}
                      onCheckedChange={(checked) =>
                        setAuditAfterSubmit(checked as boolean)
                      }
                      aria-label="Audit form after submission"
                    />
                    <Label
                      htmlFor="audit-after-submit"
                      className="text-sm cursor-pointer"
                    >
                      Audit Page After Submit
                    </Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="save-logs"
                      checked={saveLogs}
                      onCheckedChange={(checked) => setSaveLogs(checked as boolean)}
                      aria-label="Save execution logs to file"
                    />
                    <Label
                      htmlFor="save-logs"
                      className="text-sm cursor-pointer"
                    >
                      Save Logs
                    </Label>
                  </div>

                  {saveLogs && (
                    <div>
                      <Label htmlFor="logs-dir" className="text-sm font-medium">
                        Logs Directory
                      </Label>
                      <Input
                        id="logs-dir"
                        type="text"
                        placeholder="e.g., /path/to/logs"
                        value={logsDir}
                        onChange={(e) => setLogsDir(e.target.value)}
                        className="mt-1"
                        aria-describedby={
                          errors.logsDir ? "logs-dir-error" : undefined
                        }
                        aria-invalid={!!errors.logsDir}
                      />
                      {errors.logsDir && (
                        <p
                          id="logs-dir-error"
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
                disabled={isApplying}
                className="bg-blue-600 hover:bg-blue-700"
                aria-label={
                  isApplying ? "Application in progress" : "Apply to job"
                }
              >
                {isApplying ? "Applying..." : "Apply"}
              </Button>
            </DialogFooter>
          </>
        )}

        {step === "progress" && (
          <>
            <DialogHeader>
              <DialogTitle>Application in Progress</DialogTitle>
              <DialogDescription>
                Filling and submitting application form. This may take a minute or two.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <Alert>
                <AlertDescription aria-live="polite" aria-atomic="true">
                  {statusMessage || "Processing application..."}
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
                disabled={isApplying}
                aria-label="Cancel application"
              >
                Cancel
              </Button>
              {error && (
                <Button
                  onClick={handleRetry}
                  disabled={isApplying}
                  className="bg-orange-600 hover:bg-orange-700"
                  aria-label="Retry application"
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
              <DialogTitle>Application Complete</DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <Alert>
                <AlertDescription>
                  <div className="space-y-2">
                    <div>
                      <span className="font-medium">Status:</span>{" "}
                      {resultStatus}
                    </div>
                    {confirmationId && (
                      <div>
                        <span className="font-medium">Confirmation ID:</span>{" "}
                        {confirmationId}
                      </div>
                    )}
                    {confirmationText && (
                      <div>
                        <span className="font-medium">Message:</span>{" "}
                        {confirmationText}
                      </div>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleReset}>
                Apply to Another
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
