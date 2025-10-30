/**
 * Settings Form Component
 *
 * Comprehensive form for editing settings with:
 * - Collapsible sections by category
 * - Support for multiple input types (text, number, checkbox, select, password)
 * - API key masking with show/hide toggle
 * - Form validation with numeric ranges
 * - Real-time change tracking
 */

import { useState, useEffect } from "react";
import { Eye, EyeOff, ChevronDown, ChevronUp } from "lucide-react";
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
import { Setting, SettingCategory, SettingInputType } from "@/types";

interface SettingsFormProps {
  settings: Setting[];
  onSettingsChange: (settings: Setting[]) => void;
}

/**
 * Group settings by category
 */
function groupSettingsByCategory(settings: Setting[]): Record<SettingCategory, Setting[]> {
  const categories: Record<SettingCategory, Setting[]> = {
    server: [],
    discovery: [],
    application: [],
    llm: [],
    diagnostics: [],
    performance: [],
  };

  settings.forEach((setting) => {
    const category = setting.category as SettingCategory;
    if (category in categories) {
      categories[category].push(setting);
    }
  });

  return categories;
}

/**
 * Get display name for category
 */
function getCategoryLabel(category: SettingCategory): string {
  const labels: Record<SettingCategory, string> = {
    server: "Server Configuration",
    discovery: "Discovery & Search",
    application: "Application Behavior",
    llm: "LLM & Provider",
    diagnostics: "Diagnostics & Debugging",
    performance: "Performance & Monitoring",
  };
  return labels[category] || category;
}

/**
 * SettingsForm component
 */
export default function SettingsForm({
  settings: initialSettings,
  onSettingsChange,
}: SettingsFormProps) {
  const [settings, setSettings] = useState<Setting[]>(initialSettings);
  const [visibleSecrets, setVisibleSecrets] = useState<Set<string>>(new Set());
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(["llm", "application"])
  );

  useEffect(() => {
    setSettings(initialSettings);
  }, [initialSettings]);

  /**
   * Toggle section expansion
   */
  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  /**
   * Toggle secret visibility
   */
  const toggleSecretVisibility = (key: string) => {
    const newVisible = new Set(visibleSecrets);
    if (newVisible.has(key)) {
      newVisible.delete(key);
    } else {
      newVisible.add(key);
    }
    setVisibleSecrets(newVisible);
  };

  /**
   * Update setting value
   */
  const updateSetting = (key: string, value: any) => {
    const updated = settings.map((s) =>
      s.key === key ? { ...s, value } : s
    );
    setSettings(updated);
    onSettingsChange(updated);
  };

  /**
   * Render input based on type
   */
  const renderInput = (setting: Setting) => {
    const isSecret = setting.is_secret && !visibleSecrets.has(setting.key);

    switch (setting.input_type) {
      case SettingInputType.TEXT:
        return (
          <div className="relative">
            <Input
              type={isSecret ? "password" : "text"}
              value={setting.value || ""}
              onChange={(e) => updateSetting(setting.key, e.target.value)}
              placeholder={setting.default_value}
              className={setting.is_secret ? "pr-10" : ""}
              aria-label={setting.description}
              aria-describedby={`${setting.key}-desc`}
            />
            {setting.is_secret && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 -translate-y-1/2"
                onClick={() => toggleSecretVisibility(setting.key)}
                aria-label={
                  visibleSecrets.has(setting.key)
                    ? "Hide value"
                    : "Show value"
                }
              >
                {visibleSecrets.has(setting.key) ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </Button>
            )}
          </div>
        );

      case SettingInputType.NUMBER:
        return (
          <Input
            type="number"
            value={setting.value || ""}
            onChange={(e) => updateSetting(setting.key, e.target.value)}
            placeholder={setting.default_value}
            min={setting.min}
            max={setting.max}
            aria-label={setting.description}
            aria-describedby={`${setting.key}-desc`}
          />
        );

      case SettingInputType.BOOLEAN:
        return (
          <Checkbox
            checked={
              setting.value === "true" ||
              setting.value === "1" ||
              setting.value === true
            }
            onCheckedChange={(checked) =>
              updateSetting(setting.key, checked ? "true" : "false")
            }
            id={setting.key}
            aria-label={setting.description}
            aria-describedby={`${setting.key}-desc`}
          />
        );

      case SettingInputType.SELECT:
        return (
          <Select
            value={setting.value || setting.default_value || ""}
            onValueChange={(value) => updateSetting(setting.key, value)}
          >
            <SelectTrigger
              id={setting.key}
              aria-label={setting.description}
              aria-describedby={`${setting.key}-desc`}
            >
              <SelectValue placeholder="Select option..." />
            </SelectTrigger>
            <SelectContent>
              {setting.options?.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      default:
        return (
          <Input
            type="text"
            value={setting.value || ""}
            onChange={(e) => updateSetting(setting.key, e.target.value)}
            placeholder={setting.default_value}
            aria-label={setting.description}
            aria-describedby={`${setting.key}-desc`}
          />
        );
    }
  };

  const groupedSettings = groupSettingsByCategory(settings);

  return (
    <div className="space-y-4">
      {Object.entries(groupedSettings).map(([category, categorySettings]) => {
        if (categorySettings.length === 0) return null;

        const isExpanded = expandedCategories.has(category);

        return (
          <Collapsible
            key={category}
            open={isExpanded}
            onOpenChange={() => toggleCategory(category)}
            className="border rounded-lg bg-card"
          >
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                className="w-full justify-between h-auto p-4 hover:bg-accent"
              >
                <h2 className="text-base font-semibold">
                  {getCategoryLabel(category as SettingCategory)}
                  <span className="text-muted-foreground ml-2 text-sm font-normal">
                    ({categorySettings.length})
                  </span>
                </h2>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </Button>
            </CollapsibleTrigger>

            <Collapsible Content className="px-4 pb-4 border-t pt-4">
              <div className="space-y-4">
                {categorySettings.map((setting) => (
                  <div key={setting.key} className="space-y-2">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        {setting.input_type !== SettingInputType.BOOLEAN ? (
                          <Label
                            htmlFor={setting.key}
                            className={setting.required ? "required" : ""}
                          >
                            {setting.key}
                            {setting.is_secret && (
                              <span className="text-amber-600 dark:text-amber-500 ml-1">
                                🔐
                              </span>
                            )}
                          </Label>
                        ) : (
                          <div className="flex items-center gap-2">
                            {renderInput(setting)}
                            <Label
                              htmlFor={setting.key}
                              className="cursor-pointer font-normal"
                            >
                              {setting.key}
                            </Label>
                          </div>
                        )}

                        <p
                          id={`${setting.key}-desc`}
                          className="text-xs text-muted-foreground mt-1"
                        >
                          {setting.description}
                        </p>

                        {setting.default_value && (
                          <p className="text-xs text-muted-foreground">
                            Default: <code className="bg-muted px-1 rounded">{setting.default_value}</code>
                          </p>
                        )}

                        {(setting.min || setting.max) && (
                          <p className="text-xs text-muted-foreground">
                            {setting.min && `Min: ${setting.min}`}
                            {setting.min && setting.max && ", "}
                            {setting.max && `Max: ${setting.max}`}
                          </p>
                        )}
                      </div>
                    </div>

                    {setting.input_type !== SettingInputType.BOOLEAN && (
                      <div className="w-full">{renderInput(setting)}</div>
                    )}
                  </div>
                ))}
              </div>
            </Collapsible Content>
          </Collapsible>
        );
      })}
    </div>
  );
}
