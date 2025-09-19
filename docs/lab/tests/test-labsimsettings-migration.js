/**
 * Test to verify labSimSettings migration to AppState
 * Run this in browser console after loading the page
 */

function testLabSimSettingsMigration() {
  console.log("Testing labSimSettings migration to AppState...");

  // 1. Check that appState is available and initialized
  if (typeof appState === 'undefined' || !appState._initialized) {
    console.error("❌ AppState not available or not initialized");
    return false;
  }

  // 2. Check that labSimSettings is accessible through appState
  const labSettings = appState.labSimSettings;
  if (!labSettings) {
    console.error("❌ labSimSettings not found in appState");
    return false;
  }

  // 3. Check that labSimSettings has expected properties
  const expectedProperties = ['scale', 'citySize', 'vehicleCount', 'requestRate', 'chartType'];
  for (const prop of expectedProperties) {
    if (!(prop in labSettings)) {
      console.error(`❌ Missing expected property: ${prop}`);
      return false;
    }
  }

  // 4. Test getter/setter functionality
  const originalScale = labSettings.scale;
  console.log(`Original scale: ${originalScale}`);

  // 5. Test setting a value
  appState.labSimSettings.scale = 'town';
  if (appState.labSimSettings.scale !== 'town') {
    console.error("❌ Failed to set labSimSettings.scale");
    return false;
  }

  // 6. Test that the object is the same instance
  const labSettings2 = appState.labSimSettings;
  if (labSettings !== labSettings2) {
    console.error("❌ labSimSettings getter returns different instances");
    return false;
  }

  // 7. Restore original value
  appState.labSimSettings.scale = originalScale;

  // 8. Test that global labSimSettings variable is no longer accessible
  if (typeof labSimSettings !== 'undefined') {
    console.warn("⚠️ Global labSimSettings variable still exists (may be expected during transition)");
  }

  console.log("✅ All labSimSettings migration tests passed!");
  return true;
}

function testLabSimSettingsIntegration() {
  console.log("Testing labSimSettings integration with App class...");

  try {
    // Check that window.app exists
    if (!window.app) {
      console.error("❌ window.app not found");
      return false;
    }

    // Test accessing settings through appState in a way that mimics app.js usage
    const currentScale = appState.labSimSettings.scale;
    const currentChartType = appState.labSimSettings.chartType;

    console.log(`Current scale: ${currentScale}`);
    console.log(`Current chart type: ${currentChartType}`);

    // Test that we can modify settings (simulating what happens in app.js)
    const originalVehicleCount = appState.labSimSettings.vehicleCount;
    appState.labSimSettings.vehicleCount = 10;

    if (appState.labSimSettings.vehicleCount !== 10) {
      console.error("❌ Failed to modify vehicleCount");
      return false;
    }

    // Restore original value
    appState.labSimSettings.vehicleCount = originalVehicleCount;

    console.log("✅ labSimSettings integration tests passed!");
    return true;
  } catch (error) {
    console.error("❌ labSimSettings integration test error:", error);
    return false;
  }
}

// Export test functions for console use
window.testLabSimSettingsMigration = testLabSimSettingsMigration;
window.testLabSimSettingsIntegration = testLabSimSettingsIntegration;

console.log("labSimSettings migration tests loaded. Run testLabSimSettingsMigration() and testLabSimSettingsIntegration() in console.");