# Accessibility Features - Profile & Settings Forms

This document outlines the accessibility features implemented in the ProfileForm and SettingsForm components to ensure WCAG 2.1 AA compliance.

## ProfileForm Component Accessibility Features

### 1. Semantic HTML Structure
- ✅ Form uses semantic `<form>` element with `role="form"` and `aria-label="Edit profile form"`
- ✅ Form fields use `<fieldset>` elements for related field groups
- ✅ Section headings use semantic `<h2>` elements with proper hierarchy
- ✅ Labels use proper `<Label>` components with `htmlFor` associations to inputs
- ✅ Error messages use semantic `<p>` elements with descriptive text

### 2. ARIA Attributes
- ✅ Form fields have `aria-label` describing their purpose
- ✅ Invalid fields have `aria-invalid="true"` attribute
- ✅ Error messages linked via `aria-describedby` to input IDs
- ✅ Error alert region has `role="alert"`, `aria-live="assertive"`, `aria-atomic="true"`
- ✅ Alert messages announced immediately to screen readers
- ✅ Required field indicators clearly marked with "*" and text

### 3. Label Association
- ✅ All text inputs have associated `<Label>` elements with proper `htmlFor`
- ✅ Checkbox inputs have labels positioned with checkbox
- ✅ Textarea fields have descriptive labels
- ✅ Select dropdowns have associated labels
- ✅ Read-only fields clearly marked as disabled

### 4. Error Handling & Validation
- ✅ Form validation runs on submit with clear error messages
- ✅ Error alert appears at top of form with:
  - List of all validation errors
  - Field names and specific error messages
  - Automatic focus movement to error alert
- ✅ Inline error messages under each invalid field
- ✅ Errors cleared when user corrects field
- ✅ Form prevents submission with validation errors

### 5. Focus Management
- ✅ Error alert `errorAlertRef` receives focus when validation fails
- ✅ Error alert has `tabIndex={-1}` for programmatic focus
- ✅ Form buttons receive proper focus styles
- ✅ Tab order follows logical document flow
- ✅ Focus is manageable with keyboard navigation

### 6. Color Contrast
- ✅ Text and background colors meet WCAG AA standards (4.5:1 for normal text)
- ✅ Error text uses `text-destructive` color with sufficient contrast
- ✅ Success/info messages use colors with adequate contrast ratios
- ✅ Disabled fields have visually distinct styling
- ✅ Light and dark mode support maintains contrast

### 7. Keyboard Navigation
- ✅ All interactive elements accessible via Tab key
- ✅ Buttons and links have visible focus indicators
- ✅ Collapsible sections toggle with Enter/Space
- ✅ Select dropdowns work with keyboard arrow keys
- ✅ No keyboard traps exist
- ✅ Tab order: Basic Info → Defaults → Keywords → Experience → Actions

### 8. Form Fields
- ✅ Text inputs (`name`, `email`, `phone`, `location`) fully accessible
- ✅ Required fields marked with `required` attribute and `*` indicator
- ✅ Placeholder text does not replace labels
- ✅ Resume path input with Browse button has proper labeling
- ✅ Browser dropdown has all options keyboard accessible

### 9. Collapsible Sections
- ✅ Collapsible components use proper `<Collapsible>` structure
- ✅ Section triggers have proper button semantics
- ✅ Chevron icons include aria-labels for expand/collapse state
- ✅ Expanded state visible to screen readers
- ✅ Can toggle sections with keyboard (Enter/Space)

### 10. Dynamic Content (Experience Entries)
- ✅ Add button labeled "Add Experience" with icon
- ✅ Trash buttons for removal labeled with aria-label
- ✅ Experience entries numbered (#1, #2, etc.) for clarity
- ✅ Field groups in each entry properly labeled
- ✅ Textarea fields for highlights, tech_stack, metrics
- ✅ Parse functionality handles newline-separated input correctly

### 11. Instructions & Helper Text
- ✅ Helper text provided for multi-line input fields
- ✅ Format guidance: "One role per line", "One technology per line"
- ✅ Placeholder text provides examples: "Frontend Engineer", "React"
- ✅ Default values shown in placeholder or description
- ✅ Default value hints displayed below inputs

### 12. Screen Reader Support
- ✅ Form announces validation errors with `aria-live="assertive"`
- ✅ Error alert content read immediately by screen readers
- ✅ Field descriptions announced via `aria-describedby`
- ✅ Required field indicators announced
- ✅ Section headers properly announced
- ✅ Collapsible state announced (expanded/collapsed)

## SettingsForm Component Accessibility Features

### 1. Semantic HTML Structure
- ✅ Form structure uses semantic `<form>` element
- ✅ Fieldset elements group related settings by category
- ✅ Legend elements provide fieldset descriptions (sr-only for visual users)
- ✅ Section headings use `<h2>` with proper hierarchy
- ✅ Category labels clearly identify setting groups

### 2. ARIA Attributes
- ✅ Settings container has proper role attributes
- ✅ Inputs have `aria-label` describing setting purpose
- ✅ Setting descriptions linked via `aria-describedby`
- ✅ Collapsible sections have proper `aria-expanded` state
- ✅ Category buttons have `aria-expanded` indicating collapsed/expanded state

### 3. Label Association
- ✅ All input fields have associated labels
- ✅ Checkbox inputs have adjacent labels with proper association
- ✅ Select dropdowns have associated labels
- ✅ Text/number/textarea inputs all labeled
- ✅ Password inputs (secrets) have labels
- ✅ Secret field indicator (🔐) included in label

### 4. Input Type Support
- ✅ Text inputs for string settings
- ✅ Number inputs with min/max constraints for numeric settings
- ✅ Checkbox inputs for boolean settings
- ✅ Select dropdowns for enum values
- ✅ Password inputs for secret/API key fields
- ✅ All input types properly labeled and described

### 5. Secret/Password Field Handling
- ✅ API key fields render as `type="password"` by default
- ✅ Show/hide toggle button with `aria-label`
- ✅ Eye icon button clearly labeled "Show value" or "Hide value"
- ✅ Button toggles between Eye and EyeOff icons
- ✅ Secret indicator (🔐) next to field name
- ✅ Sensitivity clearly communicated to users

### 6. Form Validation
- ✅ Numeric fields enforce min/max constraints
- ✅ Select fields only allow valid enum options
- ✅ Range hints displayed (Min: X, Max: Y)
- ✅ Default value hints shown
- ✅ Category information helps users find settings
- ✅ Description text provides context for each setting

### 7. Focus Management
- ✅ Focus remains within form during navigation
- ✅ Collapsible sections maintain focus on collapse/expand
- ✅ Show/hide buttons for secrets are keyboard accessible
- ✅ Tab order follows logical category structure
- ✅ Visible focus indicators on all interactive elements

### 8. Color Contrast
- ✅ Setting names and descriptions have sufficient contrast
- ✅ Input placeholders visible with proper contrast
- ✅ Default value hints readable with good contrast
- ✅ Category headers stand out from content
- ✅ Light and dark theme support

### 9. Keyboard Navigation
- ✅ Tab through all settings in logical order
- ✅ Category sections collapsible with keyboard (Enter/Space)
- ✅ Dropdown options selectable with arrow keys
- ✅ Show/hide toggle buttons accessible with Enter/Space
- ✅ No keyboard traps
- ✅ Fully keyboard navigable without mouse

### 10. Collapsible Categories
- ✅ Each category uses `<Collapsible>` component
- ✅ Chevron icon direction indicates state (down=expanded, up=collapsed)
- ✅ Category header button is keyboard accessible
- ✅ Settings visible/hidden based on expansion state
- ✅ Category count shown in header "(N)"
- ✅ LLM and Application categories expanded by default

### 11. Setting Metadata Display
- ✅ Category label: "LLM & Provider", "Diagnostics", etc.
- ✅ Setting key displayed (e.g., "OPENROUTER_API_KEY")
- ✅ Description text explains setting purpose
- ✅ Default value shown when available
- ✅ Min/max range displayed for numeric settings
- ✅ Required field indicator when applicable

### 12. Screen Reader Support
- ✅ Category sections announced with count
- ✅ Setting descriptions read along with labels
- ✅ Default values announced
- ✅ Range constraints announced (min/max)
- ✅ Secret indicator announced
- ✅ Collapsible state announced
- ✅ Setting type (text, number, checkbox, etc.) clear to users

### 13. Visual Indicators
- ✅ Required fields marked with "*"
- ✅ Secret fields marked with "🔐"
- ✅ Expanded/collapsed chevron direction clear
- ✅ Category count shows number of settings
- ✅ Error states clearly visible
- ✅ Hover states provide visual feedback

## Testing Recommendations

### Automated Testing
1. Run axe-core audit on both forms
   ```bash
   npx axe devtools
   ```
2. Check color contrast ratios
   ```bash
   npx pa11y
   ```
3. Validate HTML semantics

### Manual Testing
1. **Keyboard Navigation**: Use only Tab, Shift+Tab, Enter, Space keys
   - Can reach all inputs
   - Focus visible at all times
   - No keyboard traps
   - Logical tab order

2. **Screen Reader Testing**: Use NVDA (Windows), JAWS, or VoiceOver (Mac)
   - All form fields announced
   - Labels associated properly
   - Error messages announced
   - Help text readable
   - Section structure clear

3. **Color Contrast**: Use WebAIM or WAVE tools
   - All text meets WCAG AA (4.5:1)
   - Form elements clearly visible
   - Error text readable
   - Light and dark modes both accessible

4. **Mobile Accessibility**: Test on iOS VoiceOver and Android TalkBack
   - Form usable on small screens
   - Touch targets adequate (44x44px minimum)
   - Inputs reachable
   - Errors announced

## WCAG 2.1 Level AA Checklist

### Perceivable
- [x] Text alternatives for non-text content
- [x] Sufficient color contrast (4.5:1)
- [x] Text is readable without color alone

### Operable
- [x] All functionality keyboard accessible
- [x] No keyboard traps
- [x] Focus visible and obvious
- [x] Forms labeled properly

### Understandable
- [x] Clear language used
- [x] Instructions provided for complex inputs
- [x] Error messages specific and helpful
- [x] Form labels associated

### Robust
- [x] Valid HTML semantics
- [x] ARIA attributes used correctly
- [x] Compatible with assistive technologies

## Components Used
- **shadcn/ui**: Button, Input, Label, Textarea, Select, Collapsible, Alert
- **Lucide Icons**: AlertCircle, Eye, EyeOff, ChevronDown, ChevronUp, Plus, Trash2
- **React**: Built-in hooks for state and refs
- **TypeScript**: Type-safe form handling

## Browser Support
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari 14+, Chrome Android 90+)

## References
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Color Contrast](https://webaim.org/articles/contrast/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
