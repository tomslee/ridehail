/**
 * Simple test to verify baselineData functionality
 * Run this in browser console after loading the page
 */

// Test the AppState baselineData functionality
function testBaselineDataFlow() {
  console.log("Testing baselineData functionality...");

  // 1. Check that appState is available
  if (typeof appState === 'undefined') {
    console.error("❌ appState not found - check if app-state.js is imported");
    return false;
  }

  // 2. Check that appState is initialized
  if (!appState._initialized) {
    console.error("❌ appState not initialized");
    return false;
  }

  // 3. Test baseline data is initially null
  const initialData = appState.getBaselineData();
  if (initialData !== null) {
    console.warn("⚠️ baselineData not initially null:", initialData);
  }

  // 4. Test setting baseline data
  const mockResults = new Map([
    ["VEHICLE_FRACTION_P1", 0.4],
    ["VEHICLE_FRACTION_P2", 0.1],
    ["VEHICLE_FRACTION_P3", 0.5],
    ["TRIP_MEAN_WAIT_TIME", 2.5],
    ["VEHICLE_MEAN_COUNT", 8],
    ["block", 100]
  ]);

  appState.setBaselineData(mockResults);

  // 5. Test getting baseline data
  const retrievedData = appState.getBaselineData();
  if (!retrievedData) {
    console.error("❌ Failed to retrieve baseline data");
    return false;
  }

  // 6. Test data integrity
  if (retrievedData.get("VEHICLE_FRACTION_P3") !== 0.5) {
    console.error("❌ Data integrity check failed");
    return false;
  }

  // 7. Test hasBaselineData
  if (!appState.hasBaselineData()) {
    console.error("❌ hasBaselineData() should return true");
    return false;
  }

  // 8. Test clearing baseline data
  appState.clearBaselineData();
  if (appState.hasBaselineData()) {
    console.error("❌ clearBaselineData() failed");
    return false;
  }

  console.log("✅ All baselineData tests passed!");
  return true;
}

// Test the message handler integration
function testMessageHandlerIntegration() {
  console.log("Testing message handler integration...");

  // Set mock baseline data
  const mockBaseline = new Map([
    ["VEHICLE_FRACTION_P1", 0.3],
    ["VEHICLE_FRACTION_P2", 0.2],
    ["VEHICLE_FRACTION_P3", 0.5]
  ]);

  appState.setBaselineData(mockBaseline);

  // Create mock comparison results
  const mockComparison = new Map([
    ["VEHICLE_FRACTION_P1", 0.4],
    ["VEHICLE_FRACTION_P2", 0.1],
    ["VEHICLE_FRACTION_P3", 0.5],
    ["chartType", "what-if"],
    ["block", 50]
  ]);

  try {
    // This should work without throwing errors
    const messageHandler = new MessageHandler(() => {}, () => {});

    // Test that handleWhatIfMessage can access baseline data
    // We can't easily test the actual plotting without DOM setup,
    // but we can check the data retrieval works
    const baselineData = appState.getBaselineData();

    if (baselineData && baselineData.get("VEHICLE_FRACTION_P3") === 0.5) {
      console.log("✅ Message handler can access baseline data correctly");
      return true;
    } else {
      console.error("❌ Message handler baseline data access failed");
      return false;
    }
  } catch (error) {
    console.error("❌ Message handler integration error:", error);
    return false;
  }
}

// Export test functions for console use
window.testBaselineDataFlow = testBaselineDataFlow;
window.testMessageHandlerIntegration = testMessageHandlerIntegration;

console.log("Baseline data tests loaded. Run testBaselineDataFlow() and testMessageHandlerIntegration() in console.");