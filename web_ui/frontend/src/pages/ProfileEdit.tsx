/**
 * Profile Edit Page
 *
 * Allows users to edit profile configuration with save/cancel and message feedback.
 * Includes unsaved changes warning (optional).
 */

import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import ProfileForm from "@/components/ProfileForm";
import { apiClient } from "@/services/api";
import { Profile, ProfileDefaults, ProfileKeywords, ProfileExperience, ProfilePrompts } from "@/types";

/**
 * ProfileEdit page component
 */
export default function ProfileEdit() {
  const navigate = useNavigate();
  const { profileId } = useParams<{ profileId: string }>();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  // Load profile on mount
  useEffect(() => {
    const loadProfile = async () => {
      if (!profileId) {
        setErrorMessage("Profile ID not found");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await apiClient.get(`/profiles/${profileId}`);
        setProfile(response.data);
        setErrorMessage("");
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load profile";
        setErrorMessage(message);
        console.error("Profile load error:", error);
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, [profileId]);

  /**
   * Handle profile form submission
   */
  const handleSave = async (formData: Profile) => {
    if (!profileId) {
      setErrorMessage("Profile ID not found");
      return;
    }

    try {
      setSaving(true);
      setErrorMessage("");
      setSuccessMessage("");

      const response = await apiClient.put(`/profiles/${profileId}`, formData);
      setProfile(response.data);
      setUnsavedChanges(false);
      setSuccessMessage("Profile saved successfully");

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save profile";
      setErrorMessage(message);
      console.error("Profile save error:", error);
    } finally {
      setSaving(false);
    }
  };

  /**
   * Handle cancel - navigate back
   */
  const handleCancel = () => {
    if (unsavedChanges && !window.confirm("You have unsaved changes. Are you sure you want to leave?")) {
      return;
    }
    navigate("/profiles");
  };

  /**
   * Handle form changes
   */
  const handleFormChange = () => {
    setUnsavedChanges(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancel}
                className="gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
              <h1 className="text-2xl font-bold">Edit Profile</h1>
            </div>
            {unsavedChanges && (
              <div className="text-sm text-amber-600 dark:text-amber-500">
                Unsaved changes
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
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

        {/* Profile Form */}
        {profile && (
          <ProfileForm
            profile={profile}
            onSave={handleSave}
            onCancel={handleCancel}
            onChange={handleFormChange}
            isSaving={saving}
          />
        )}
      </div>
    </div>
  );
}
