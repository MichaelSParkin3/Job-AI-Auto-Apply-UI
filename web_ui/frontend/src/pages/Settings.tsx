/**
 * Settings Page
 *
 * Displays and manages application settings with:
 * - Settings form (SettingsForm component)
 * - Save and Revert buttons
 * - Modified indicator
 * - Reset All button with confirmation
 * - Organized by category
 */

import { useState, useEffect } from "react";
import { RotateCcw, Save, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import SettingsForm from "@/components/SettingsForm";
import { apiClient } from "@/services/api";
import { Setting } from "@/types";

/**
 * Settings page component
 */
export default function SettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [initialSettings, setInitialSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [modified, setModified] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  /**
   * Load all settings from API
   */
  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get("/settings");
      setSettings(response.data.settings);
      setInitialSettings(response.data.settings);
      setModified(false);
      setErrorMessage("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load settings";
      setErrorMessage(message);
      console.error("Settings load error:", error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle settings change
   */
  const handleSettingsChange = (updatedSettings: Setting[]) => {
    setSettings(updatedSettings);

    // Check if any settings have changed from initial
    const hasChanges = updatedSettings.some(
      (setting, index) =>
        setting.value !== initialSettings[index]?.value
    );
    setModified(hasChanges);
  };

  /**
   * Handle save - update modified settings
   */
  const handleSave = async () => {
    try {
      setSaving(true);
      setErrorMessage("");
      setSuccessMessage("");

      // Build update payload with only changed settings
      const updates: Record<string, string> = {};
      settings.forEach((setting, index) => {
        if (setting.value !== initialSettings[index]?.value && setting.value) {
          updates[setting.key] = setting.value;
        }
      });

      if (Object.keys(updates).length === 0) {
        setSuccessMessage("No changes to save");
        setTimeout(() => setSuccessMessage(""), 3000);
        return;
      }

      await apiClient.put("/settings", updates);
      setInitialSettings(settings);
      setModified(false);
      setSuccessMessage(
        `${Object.keys(updates).length} setting(s) saved successfully`
      );

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save settings";
      setErrorMessage(message);
      console.error("Settings save error:", error);
    } finally {
      setSaving(false);
    }
  };

  /**
   * Handle revert - reload initial settings
   */
  const handleRevert = () => {
    setSettings(initialSettings.map((s) => ({ ...s })));
    setModified(false);
    setErrorMessage("");
    setSuccessMessage("");
  };

  /**
   * Handle reset all - confirm and reset
   */
  const handleResetAll = async () => {
    try {
      setSaving(true);
      setErrorMessage("");
      setSuccessMessage("");

      await apiClient.post("/settings/reset");

      // Reload settings
      await loadSettings();
      setSuccessMessage("All settings reset to defaults");
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to reset settings";
      setErrorMessage(message);
      console.error("Settings reset error:", error);
    } finally {
      setSaving(false);
      setShowResetConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">Settings</h1>
            {modified && (
              <div className="flex items-center gap-2 text-amber-600 dark:text-amber-500">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-medium">Unsaved changes</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Messages */}
        {errorMessage && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        )}

        {successMessage && (
          <Alert className="mb-6 bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800">
            <AlertDescription className="text-green-800 dark:text-green-200">
              {successMessage}
            </AlertDescription>
          </Alert>
        )}

        {/* Settings Form */}
        {settings.length > 0 && (
          <div className="space-y-6">
            <SettingsForm
              settings={settings}
              onSettingsChange={handleSettingsChange}
            />

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 justify-between pt-6 border-t">
              <Button
                variant="outline"
                onClick={() => setShowResetConfirm(true)}
                className="text-destructive hover:text-destructive"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset All to Defaults
              </Button>

              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={handleRevert}
                  disabled={!modified || saving}
                >
                  Revert Changes
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={!modified || saving}
                >
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? "Saving..." : "Save Settings"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Reset Confirmation Dialog */}
      <AlertDialog open={showResetConfirm} onOpenChange={setShowResetConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset All Settings?</AlertDialogTitle>
            <AlertDialogDescription>
              This will reset all application settings to their default values.
              This action cannot be undone. Are you sure?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialog Footer>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleResetAll}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Reset All Settings
            </AlertDialogAction>
          </AlertDialog Footer>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
