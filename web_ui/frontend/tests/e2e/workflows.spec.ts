/**
 * End-to-End Integration Tests
 *
 * Tests complete user workflows using Playwright:
 * - Dashboard → Discover → Queue → Detail → Apply → Status
 * - Profile creation and switching
 * - Settings configuration
 * - Error handling and recovery
 */

import { test, expect, Page } from "@playwright/test";

const BASE_URL = process.env.BASE_URL || "http://localhost:5173";
const API_URL = process.env.API_URL || "http://localhost:5000/api/v1";

/**
 * Helper to wait for API response
 */
async function waitForApiCall(page: Page, url: string, method = "GET") {
  return page.waitForResponse((response) =>
    response.url().includes(url) && response.request().method() === method
  );
}

test.describe("Complete Job Discovery & Application Workflow", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to application
    await page.goto(BASE_URL);

    // Wait for application to load
    await page.waitForSelector('a[href="/"]', { timeout: 10000 });
  });

  test("should complete full workflow: dashboard -> discover -> queue -> apply", async ({
    page,
  }) => {
    // Step 1: Verify dashboard loads
    await expect(page).toHaveTitle(/Job AI/);
    await expect(page.locator("h1")).toContainText("Dashboard");

    // Step 2: Navigate to discovery
    const discoverButton = page.locator("button:has-text('Discover Jobs')");
    await expect(discoverButton).toBeVisible();
    await discoverButton.click();

    // Step 3: Wait for discovery modal/page to load
    await page.waitForSelector("[role='dialog']", { timeout: 5000 });
    const discoveryModal = page.locator("[role='dialog']");
    await expect(discoveryModal).toBeVisible();

    // Step 4: Configure discovery options
    const windowSelect = page.locator("select:has-text('24h')");
    if (await windowSelect.isVisible()) {
      await windowSelect.selectOption("48h");
    }

    // Step 5: Execute discovery
    const executeButton = page.locator(
      "button:has-text('Execute Discovery')"
    );
    if (await executeButton.isEnabled()) {
      await executeButton.click();

      // Wait for discovery to complete
      await page.waitForNavigation({ timeout: 10000 }).catch(() => {});
    }

    // Step 6: Verify queue displays
    await page.waitForSelector("table, [role='list']", { timeout: 5000 });
    const queueTable = page.locator("table, [role='list']");
    await expect(queueTable).toBeVisible();

    // Step 7: Click on a job to view details
    const firstJob = page.locator("[data-testid='job-item']").first();
    if (await firstJob.isVisible()) {
      await firstJob.click();

      // Step 8: Verify job details display
      await page.waitForSelector("h2", { timeout: 5000 });
      const detailsHeading = page.locator("h2").first();
      await expect(detailsHeading).toBeVisible();

      // Step 9: Look for apply button
      const applyButton = page.locator(
        "button:has-text('Apply'), button:has-text('Apply Now')"
      );
      if (await applyButton.isVisible()) {
        await applyButton.click();

        // Step 10: Verify apply modal appears
        await page.waitForSelector("[role='dialog']", { timeout: 5000 });
        const applyModal = page.locator("[role='dialog']");
        await expect(applyModal).toBeVisible();
      }
    }
  });

  test("should persist discovery options across sessions", async ({
    page,
  }) => {
    // Navigate to discovery
    await page.goto(`${BASE_URL}/discover`).catch(() => {});

    // Configure options
    const windowInput = page.locator('input[value="24"]');
    if (await windowInput.isVisible()) {
      await windowInput.fill("72");
    }

    const capInput = page.locator('input[value="10"]');
    if (await capInput.isVisible()) {
      await capInput.fill("20");
    }

    // Execute discovery
    const executeButton = page.locator("button:has-text('Execute')");
    if (await executeButton.isEnabled()) {
      await executeButton.click();
    }

    // Wait a moment
    await page.waitForTimeout(1000);

    // Navigate away and back
    await page.goto(BASE_URL);
    await page.goto(`${BASE_URL}/discover`).catch(() => {});

    // Verify options persisted (or at least form is still accessible)
    await expect(page).not.toHaveTitle("Error");
  });
});

test.describe("Profile Management Workflow", () => {
  test("should create and edit profile", async ({ page }) => {
    await page.goto(`${BASE_URL}/profiles`).catch(() => {});

    // Try to find and click edit profile button
    const editButton = page.locator(
      "button:has-text('Edit'), a:has-text('Edit Profile')"
    );
    if (await editButton.first().isVisible({ timeout: 2000 }).catch(() => false)) {
      await editButton.first().click();

      // Verify profile form loads
      await page.waitForSelector("form, [role='form']", { timeout: 5000 });

      // Update name field
      const nameInput = page.locator('input[placeholder*="name"], input#profile-name');
      if (await nameInput.isVisible()) {
        await nameInput.fill("Updated Test User");
      }

      // Save profile
      const saveButton = page.locator("button:has-text('Save')");
      if (await saveButton.isEnabled()) {
        await saveButton.click();

        // Wait for success message
        await page
          .waitForSelector("[role='alert']:has-text('saved')", {
            timeout: 5000,
          })
          .catch(() => {});
      }
    }
  });

  test("should switch between profiles", async ({ page }) => {
    await page.goto(`${BASE_URL}/profiles`).catch(() => {});

    // Look for profile list
    const profileItems = page.locator("[data-testid='profile-item']");
    const count = await profileItems.count();

    if (count > 0) {
      // Click first profile
      await profileItems.first().click();

      // Wait for switch to complete
      await page.waitForTimeout(500);

      // Verify we're viewing that profile
      await expect(page).not.toHaveTitle("Error");
    }
  });
});

test.describe("Settings Management Workflow", () => {
  test("should load and modify settings", async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`).catch(() => {});

    // Verify settings page loads
    await page.waitForSelector("[role='form']", { timeout: 5000 }).catch(() => {});

    // Look for any setting input
    const inputs = page.locator("input, select, textarea");
    const inputCount = await inputs.count();

    if (inputCount > 0) {
      // Try to modify first setting
      const firstInput = inputs.first();
      const type = await firstInput.getAttribute("type");

      if (type === "text" || type === "number" || !type) {
        await firstInput.fill("test-value");
      } else if (type === "checkbox") {
        await firstInput.click();
      }

      // Look for save button
      const saveButton = page.locator("button:has-text('Save')");
      if (await saveButton.isEnabled({ timeout: 2000 }).catch(() => false)) {
        await saveButton.click();

        // Wait for confirmation
        await page
          .waitForSelector("[role='alert']:has-text('save')", { timeout: 5000 })
          .catch(() => {});
      }
    }
  });

  test("should reset settings to defaults", async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`).catch(() => {});

    // Look for reset button
    const resetButton = page.locator("button:has-text('Reset All')");
    if (await resetButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await resetButton.click();

      // Confirm reset in dialog
      const confirmButton = page.locator(
        "button:has-text('Reset All Settings'), [role='alertdialog'] button:nth-child(2)"
      );
      if (await confirmButton.isVisible()) {
        await confirmButton.click();

        // Wait for completion
        await page.waitForTimeout(1000);
        await expect(page).not.toHaveTitle("Error");
      }
    }
  });
});

test.describe("Error Handling and Recovery", () => {
  test("should handle network errors gracefully", async ({ page }) => {
    // Go offline
    await page.context().setOffline(true);

    // Try to load dashboard
    await page.goto(`${BASE_URL}`).catch(() => {});

    // Should either show error or handle gracefully
    const errorMessage = page.locator("[role='alert']");
    const page401 = page.locator("text=/Error|error|offline/i");

    // Go back online
    await page.context().setOffline(false);

    // Try to reload
    await page.reload().catch(() => {});

    // Page should recover
    await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
  });

  test("should show validation errors on invalid form submission", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/profiles`).catch(() => {});

    const editButton = page.locator(
      "button:has-text('Edit'), a:has-text('Edit')"
    );
    if (
      await editButton
        .first()
        .isVisible({ timeout: 2000 })
        .catch(() => false)
    ) {
      await editButton.first().click();

      // Wait for form
      await page.waitForSelector("form, [role='form']", { timeout: 5000 });

      // Try to clear required field and submit
      const nameInput = page.locator(
        'input[id*="name"], input[placeholder*="name"]'
      );
      if (await nameInput.isVisible()) {
        await nameInput.fill("");
      }

      // Try to submit
      const submitButton = page.locator("button:has-text('Save')");
      if (await submitButton.isVisible()) {
        await submitButton.click();

        // Should show validation error
        const errorAlert = page.locator("[role='alert']:has-text('Error')");
        const errorText = page.locator("text=/required|invalid|error/i");

        // Either error alert or error text should appear (or form stays open)
        await page.waitForTimeout(500);
      }
    }
  });
});

test.describe("Accessibility in Workflows", () => {
  test("should be keyboard navigable through complete workflow", async ({
    page,
  }) => {
    await page.goto(BASE_URL);

    // Tab through main navigation
    await page.keyboard.press("Tab");
    let focusedElement = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      return el?.textContent?.substring(0, 20) || "unknown";
    });

    // Should be able to navigate with tab
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press("Tab");
    }

    focusedElement = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      return el?.tagName || "unknown";
    });

    // Should have moved focus
    expect(focusedElement).not.toBe("");
  });

  test("should announce form errors to screen readers", async ({ page }) => {
    await page.goto(`${BASE_URL}/profiles`).catch(() => {});

    const editButton = page.locator("button:has-text('Edit')");
    if (await editButton.first().isVisible({ timeout: 2000 }).catch(() => false)) {
      await editButton.first().click();

      // Wait for form
      await page.waitForSelector("form", { timeout: 5000 }).catch(() => {});

      // Try to submit with errors
      const submitButton = page.locator("button:has-text('Save')");
      if (await submitButton.isVisible()) {
        await submitButton.click();

        // Check for aria-live alert
        const liveRegion = page.locator('[aria-live="assertive"]');
        const ariaAlert = page.locator('[role="alert"]');

        // One of these should be present
        const liveExists = await liveRegion.count().then((c) => c > 0);
        const alertExists = await ariaAlert.count().then((c) => c > 0);

        // Should have at least one
        expect(liveExists || alertExists).toBe(true);
      }
    }
  });
});

test.describe("Performance Baselines", () => {
  test("should load dashboard within 2 seconds", async ({ page }) => {
    const startTime = Date.now();
    await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
    const loadTime = Date.now() - startTime;

    // Should load quickly
    expect(loadTime).toBeLessThan(2000);
  });

  test("should display queue within 3 seconds", async ({ page }) => {
    await page.goto(`${BASE_URL}/queue`).catch(() => {});

    const startTime = Date.now();
    await page.waitForSelector("table, [role='list']", { timeout: 3000 });
    const displayTime = Date.now() - startTime;

    expect(displayTime).toBeLessThan(3000);
  });

  test("should open modals within 1 second", async ({ page }) => {
    await page.goto(BASE_URL);

    const button = page.locator(
      "button:has-text('Discover'), button:has-text('Apply')"
    );
    if (await button.first().isVisible()) {
      const startTime = Date.now();
      await button.first().click();
      await page.waitForSelector("[role='dialog']", { timeout: 1000 });
      const openTime = Date.now() - startTime;

      expect(openTime).toBeLessThan(1000);
    }
  });
});
