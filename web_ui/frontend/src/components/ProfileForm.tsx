/**
 * Profile Form Component
 *
 * Comprehensive form for editing profile with:
 * - Basic fields (ID, name, email, phone, location, resume, browser)
 * - Defaults section (contact and URL defaults)
 * - Keywords section (roles, tech stack)
 * - Experience section with add/remove functionality
 * - Full validation and error messaging
 */

import { useState, useEffect, useRef } from "react";
import { Plus, Trash2, ChevronDown, ChevronUp, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Profile, ProfileDefaults, ProfileKeywords, ProfileExperience, ProfilePrompts } from "@/types";

interface ProfileFormProps {
  profile: Profile;
  onSave: (profile: Profile) => void;
  onCancel: () => void;
  onChange?: () => void;
  isSaving?: boolean;
}

/**
 * ProfileForm component
 */
export default function ProfileForm({
  profile: initialProfile,
  onSave,
  onCancel,
  onChange,
  isSaving = false,
}: ProfileFormProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const errorAlertRef = useRef<HTMLDivElement>(null);
  const [profile, setProfile] = useState<Profile>(initialProfile);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [expandedSections, setExpandedSections] = useState({
    defaults: true,
    keywords: true,
    experience: true,
    prompts: false,
  });
  const [focusTrap, setFocusTrap] = useState(false);

  useEffect(() => {
    setProfile(initialProfile);
  }, [initialProfile]);

  /**
   * Focus management for error alerts
   */
  useEffect(() => {
    if (Object.keys(errors).length > 0 && errorAlertRef.current) {
      // Announce errors to screen readers
      errorAlertRef.current.focus();
      errorAlertRef.current.setAttribute("aria-live", "assertive");
    }
  }, [errors]);

  /**
   * Toggle section expansion
   */
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  /**
   * Validate form
   */
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!profile.id?.trim()) {
      newErrors.id = "Profile ID is required";
    }
    if (!profile.name?.trim()) {
      newErrors.name = "Name is required";
    }
    if (!profile.resume_path?.trim()) {
      newErrors.resume_path = "Resume path is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Handle form submission
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm()) {
      onSave(profile);
    }
  };

  /**
   * Update basic fields
   */
  const updateField = (field: keyof Profile, value: any) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
    onChange?.();
    setErrors((prev) => ({ ...prev, [field]: "" }));
  };

  /**
   * Update nested defaults field
   */
  const updateDefaults = (field: keyof ProfileDefaults, value: string) => {
    setProfile((prev) => ({
      ...prev,
      defaults: {
        ...prev.defaults,
        [field]: value,
      },
    }));
    onChange?.();
  };

  /**
   * Update keywords
   */
  const updateKeywords = (field: keyof ProfileKeywords, value: string[]) => {
    setProfile((prev) => ({
      ...prev,
      keywords: {
        ...prev.keywords,
        [field]: value,
      },
    }));
    onChange?.();
  };

  /**
   * Add experience entry
   */
  const addExperience = () => {
    const newExperience: ProfileExperience = {
      company: "",
      role: "",
      dates: "",
      highlights: [],
      tech_stack: [],
      metrics: {},
    };
    setProfile((prev) => ({
      ...prev,
      experience: [...(prev.experience || []), newExperience],
    }));
    onChange?.();
  };

  /**
   * Update experience entry
   */
  const updateExperience = (
    index: number,
    field: keyof ProfileExperience,
    value: any
  ) => {
    setProfile((prev) => {
      const updated = [...(prev.experience || [])];
      updated[index] = { ...updated[index], [field]: value };
      return { ...prev, experience: updated };
    });
    onChange?.();
  };

  /**
   * Remove experience entry
   */
  const removeExperience = (index: number) => {
    setProfile((prev) => ({
      ...prev,
      experience: prev.experience?.filter((_, i) => i !== index) || [],
    }));
    onChange?.();
  };

  /**
   * Update prompts
   */
  const updatePrompts = (field: keyof ProfilePrompts, value: string) => {
    setProfile((prev) => ({
      ...prev,
      prompts: {
        ...prev.prompts,
        [field]: value,
      },
    }));
    onChange?.();
  };

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      className="space-y-6"
      role="form"
      aria-label="Edit profile form"
      noValidate
    >
      {/* Error Alert Region - for screen readers */}
      {Object.keys(errors).length > 0 && (
        <Alert
          ref={errorAlertRef}
          variant="destructive"
          className="mb-6"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
          tabIndex={-1}
        >
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <div className="font-semibold mb-2">
              Form has {Object.keys(errors).length} error(s). Please correct them and try again.
            </div>
            <ul className="list-disc list-inside space-y-1">
              {Object.entries(errors).map(([field, message]) => (
                <li key={field}>
                  <strong>{field}:</strong> {message}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Basic Information Section */}
      <fieldset className="space-y-4 border rounded-lg p-6 bg-card">
        <legend className="text-lg font-semibold sr-only">Basic Information</legend>
        <h2 className="text-lg font-semibold" id="basic-info-heading">
          Basic Information
        </h2>

        {/* Profile ID (read-only) */}
        <div className="space-y-2">
          <Label htmlFor="profile-id">Profile ID</Label>
          <Input
            id="profile-id"
            value={profile.id}
            disabled
            className="bg-muted"
          />
          <p className="text-xs text-muted-foreground">
            Profile ID cannot be changed
          </p>
        </div>

        {/* Name */}
        <div className="space-y-2">
          <Label htmlFor="profile-name" className="required">
            Full Name *
          </Label>
          <Input
            id="profile-name"
            value={profile.name}
            onChange={(e) => updateField("name", e.target.value)}
            placeholder="Your full name"
            aria-invalid={!!errors.name}
            aria-describedby={errors.name ? "profile-name-error" : undefined}
          />
          {errors.name && (
            <p id="profile-name-error" className="text-sm text-destructive">
              {errors.name}
            </p>
          )}
        </div>

        {/* Email */}
        <div className="space-y-2">
          <Label htmlFor="profile-email">Email</Label>
          <Input
            id="profile-email"
            type="email"
            value={profile.email || ""}
            onChange={(e) => updateField("email", e.target.value)}
            placeholder="email@example.com"
          />
        </div>

        {/* Phone */}
        <div className="space-y-2">
          <Label htmlFor="profile-phone">Phone</Label>
          <Input
            id="profile-phone"
            value={profile.phone || ""}
            onChange={(e) => updateField("phone", e.target.value)}
            placeholder="+1-555-0000"
          />
        </div>

        {/* Location */}
        <div className="space-y-2">
          <Label htmlFor="profile-location">Location</Label>
          <Input
            id="profile-location"
            value={profile.location || ""}
            onChange={(e) => updateField("location", e.target.value)}
            placeholder="City, State"
          />
        </div>

        {/* Resume Path */}
        <div className="space-y-2">
          <Label htmlFor="profile-resume" className="required">
            Resume Path *
          </Label>
          <div className="flex gap-2">
            <Input
              id="profile-resume"
              value={profile.resume_path}
              onChange={(e) => updateField("resume_path", e.target.value)}
              placeholder="resumes/resume.pdf"
              aria-invalid={!!errors.resume_path}
              aria-describedby={
                errors.resume_path ? "resume-path-error" : undefined
              }
              className="flex-1"
            />
            <Button variant="outline" size="sm" type="button">
              Browse
            </Button>
          </div>
          {errors.resume_path && (
            <p id="resume-path-error" className="text-sm text-destructive">
              {errors.resume_path}
            </p>
          )}
        </div>

        {/* Preferred Browser */}
        <div className="space-y-2">
          <Label htmlFor="profile-browser">Preferred Browser</Label>
          <Select
            value={profile.preferred_browser || "chromium"}
            onValueChange={(value) =>
              updateField("preferred_browser", value)
            }
          >
            <SelectTrigger id="profile-browser">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="chromium">Chromium</SelectItem>
              <SelectItem value="chrome">Chrome</SelectItem>
              <SelectItem value="msedge">Microsoft Edge</SelectItem>
              <SelectItem value="firefox">Firefox</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* User Data Directory */}
        <div className="space-y-2">
          <Label htmlFor="profile-user-data-dir">User Data Directory</Label>
          <Input
            id="profile-user-data-dir"
            value={profile.user_data_dir || ""}
            onChange={(e) => updateField("user_data_dir", e.target.value)}
            placeholder="Path to browser profile directory"
          />
          <p className="text-xs text-muted-foreground">
            Optional: For persistent browser profiles with cookies/sessions
          </p>
        </div>
      </div>

      {/* Defaults Section */}
      <Collapsible
        open={expandedSections.defaults}
        onOpenChange={() => toggleSection("defaults")}
        className="border rounded-lg bg-card"
      >
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between h-auto p-6 hover:bg-accent"
          >
            <h2 className="text-lg font-semibold">Default Information</h2>
            {expandedSections.defaults ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </CollapsibleTrigger>
        <Collapsible Content className="px-6 pb-6 space-y-4 border-t pt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="defaults-name">Default Name</Label>
              <Input
                id="defaults-name"
                value={profile.defaults?.name || ""}
                onChange={(e) => updateDefaults("name", e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="defaults-email">Default Email</Label>
              <Input
                id="defaults-email"
                type="email"
                value={profile.defaults?.email || ""}
                onChange={(e) => updateDefaults("email", e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="defaults-phone">Default Phone</Label>
              <Input
                id="defaults-phone"
                value={profile.defaults?.phone || ""}
                onChange={(e) => updateDefaults("phone", e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="defaults-location">Default Location</Label>
              <Input
                id="defaults-location"
                value={profile.defaults?.location || ""}
                onChange={(e) => updateDefaults("location", e.target.value)}
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="defaults-portfolio">Portfolio URL</Label>
              <Input
                id="defaults-portfolio"
                type="url"
                value={profile.defaults?.portfolio_url || ""}
                onChange={(e) => updateDefaults("portfolio_url", e.target.value)}
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="defaults-github">GitHub URL</Label>
              <Input
                id="defaults-github"
                type="url"
                value={profile.defaults?.github_url || ""}
                onChange={(e) => updateDefaults("github_url", e.target.value)}
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="defaults-linkedin">LinkedIn URL</Label>
              <Input
                id="defaults-linkedin"
                type="url"
                value={profile.defaults?.linkedin_url || ""}
                onChange={(e) => updateDefaults("linkedin_url", e.target.value)}
              />
            </div>
          </div>
        </Collapsible Content>
      </Collapsible>

      {/* Keywords Section */}
      <Collapsible
        open={expandedSections.keywords}
        onOpenChange={() => toggleSection("keywords")}
        className="border rounded-lg bg-card"
      >
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between h-auto p-6 hover:bg-accent"
          >
            <h2 className="text-lg font-semibold">Keywords & Skills</h2>
            {expandedSections.keywords ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </CollapsibleTrigger>
        <Collapsible Content className="px-6 pb-6 space-y-4 border-t pt-4">
          <div className="space-y-2">
            <Label htmlFor="keywords-roles">Target Roles</Label>
            <Textarea
              id="keywords-roles"
              value={(profile.keywords?.roles || []).join("\n")}
              onChange={(e) =>
                updateKeywords(
                  "roles",
                  e.target.value.split("\n").filter((r) => r.trim())
                )
              }
              placeholder="Frontend Engineer&#10;React Developer&#10;Full Stack Engineer"
              rows={4}
            />
            <p className="text-xs text-muted-foreground">
              One role per line
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="keywords-tech">Tech Stack</Label>
            <Textarea
              id="keywords-tech"
              value={(profile.keywords?.tech_stack || []).join("\n")}
              onChange={(e) =>
                updateKeywords(
                  "tech_stack",
                  e.target.value.split("\n").filter((t) => t.trim())
                )
              }
              placeholder="React&#10;TypeScript&#10;Next.js&#10;Node.js"
              rows={4}
            />
            <p className="text-xs text-muted-foreground">
              One technology per line
            </p>
          </div>
        </Collapsible Content>
      </Collapsible>

      {/* Experience Section */}
      <Collapsible
        open={expandedSections.experience}
        onOpenChange={() => toggleSection("experience")}
        className="border rounded-lg bg-card"
      >
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between h-auto p-6 hover:bg-accent"
          >
            <h2 className="text-lg font-semibold">
              Work Experience
              {profile.experience?.length > 0 && (
                <span className="text-muted-foreground ml-2">
                  ({profile.experience.length})
                </span>
              )}
            </h2>
            {expandedSections.experience ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </CollapsibleTrigger>
        <Collapsible Content className="px-6 pb-6 border-t pt-4">
          <div className="space-y-6">
            {profile.experience?.map((exp, index) => (
              <div
                key={index}
                className="border rounded-lg p-4 bg-muted/30 space-y-4"
              >
                <div className="flex justify-between items-start gap-4">
                  <h3 className="font-semibold text-sm">
                    Experience #{index + 1}
                  </h3>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeExperience(index)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`exp-${index}-company`}>Company</Label>
                    <Input
                      id={`exp-${index}-company`}
                      value={exp.company}
                      onChange={(e) =>
                        updateExperience(index, "company", e.target.value)
                      }
                      placeholder="Company Name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`exp-${index}-role`}>Role</Label>
                    <Input
                      id={`exp-${index}-role`}
                      value={exp.role}
                      onChange={(e) =>
                        updateExperience(index, "role", e.target.value)
                      }
                      placeholder="Job Title"
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor={`exp-${index}-dates`}>Dates</Label>
                    <Input
                      id={`exp-${index}-dates`}
                      value={exp.dates}
                      onChange={(e) =>
                        updateExperience(index, "dates", e.target.value)
                      }
                      placeholder="Jan 2020 – Dec 2023"
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor={`exp-${index}-highlights`}>
                      Key Highlights
                    </Label>
                    <Textarea
                      id={`exp-${index}-highlights`}
                      value={(exp.highlights || []).join("\n")}
                      onChange={(e) =>
                        updateExperience(
                          index,
                          "highlights",
                          e.target.value
                            .split("\n")
                            .filter((h) => h.trim())
                        )
                      }
                      placeholder="Led team of 5 engineers&#10;Improved performance by 40%&#10;Shipped 3 major features"
                      rows={3}
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor={`exp-${index}-tech`}>Tech Stack</Label>
                    <Textarea
                      id={`exp-${index}-tech`}
                      value={(exp.tech_stack || []).join("\n")}
                      onChange={(e) =>
                        updateExperience(
                          index,
                          "tech_stack",
                          e.target.value
                            .split("\n")
                            .filter((t) => t.trim())
                        )
                      }
                      placeholder="React&#10;TypeScript&#10;Node.js"
                      rows={2}
                    />
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor={`exp-${index}-metrics`}>Metrics</Label>
                    <Textarea
                      id={`exp-${index}-metrics`}
                      value={
                        exp.metrics && Object.keys(exp.metrics).length > 0
                          ? Object.entries(exp.metrics)
                              .map(([k, v]) => `${k}: ${v}`)
                              .join("\n")
                          : ""
                      }
                      onChange={(e) => {
                        const metrics: Record<string, string> = {};
                        e.target.value.split("\n").forEach((line) => {
                          const [key, value] = line.split(":").map((s) => s.trim());
                          if (key && value) {
                            metrics[key] = value;
                          }
                        });
                        updateExperience(index, "metrics", metrics);
                      }}
                      placeholder="key_metric: 40%&#10;team_size: 5&#10;impact: 1M users"
                      rows={2}
                    />
                  </div>
                </div>
              </div>
            ))}

            <Button
              type="button"
              variant="outline"
              className="w-full gap-2"
              onClick={addExperience}
            >
              <Plus className="w-4 h-4" />
              Add Experience
            </Button>
          </div>
        </Collapsible Content>
      </Collapsible>

      {/* Prompts Section (Optional) */}
      <Collapsible
        open={expandedSections.prompts}
        onOpenChange={() => toggleSection("prompts")}
        className="border rounded-lg bg-card"
      >
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between h-auto p-6 hover:bg-accent"
          >
            <h2 className="text-lg font-semibold">LLM Prompts (Advanced)</h2>
            {expandedSections.prompts ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </CollapsibleTrigger>
        <Collapsible Content className="px-6 pb-6 space-y-4 border-t pt-4">
          <div className="space-y-2">
            <Label htmlFor="prompts-cover">Cover Letter Guidance</Label>
            <Textarea
              id="prompts-cover"
              value={profile.prompts?.cover_letter || ""}
              onChange={(e) =>
                updatePrompts("cover_letter", e.target.value)
              }
              placeholder="Instructions for LLM when writing cover letters..."
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompts-summary">Resume Summary Guidance</Label>
            <Textarea
              id="prompts-summary"
              value={profile.prompts?.resume_summary || ""}
              onChange={(e) =>
                updatePrompts("resume_summary", e.target.value)
              }
              placeholder="Instructions for LLM when crafting resume summaries..."
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompts-accomplishments">
              Key Accomplishments Guidance
            </Label>
            <Textarea
              id="prompts-accomplishments"
              value={profile.prompts?.key_accomplishments || ""}
              onChange={(e) =>
                updatePrompts("key_accomplishments", e.target.value)
              }
              placeholder="Instructions for LLM when selecting accomplishments..."
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompts-experience">Experience Selection Guidance</Label>
            <Textarea
              id="prompts-experience"
              value={profile.prompts?.experience_selection || ""}
              onChange={(e) =>
                updatePrompts("experience_selection", e.target.value)
              }
              placeholder="Instructions for LLM when matching experiences to job requirements..."
              rows={3}
            />
          </div>
        </Collapsible Content>
      </Collapsible>

      {/* Form Actions */}
      <div className="flex justify-end gap-3 pt-6 border-t">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : "Save Profile"}
        </Button>
      </div>
    </form>
  );
}
